"""Unified SPICE authority for Step 8.6 positions, frames and body constants."""

from __future__ import annotations

import logging
import math
import time
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from terralab3d.domain.geometry import EquatorialCoordinate, HorizontalCoordinate
from terralab3d.domain.identifiers import CelestialBodyId
from terralab3d.domain.solar_system.calculations import (
    AU_KM,
    bright_limb_position_angle_deg,
    ecef_to_enu_rotation,
    illuminated_fraction,
    matrix3_apply,
    matrix3_multiply,
    matrix3_transpose,
    moon_apparent_magnitude,
    normalize_vector,
    north_pole_position_angle_deg,
    planet_apparent_magnitude,
    rotation_matrix_to_quaternion,
    signed_longitude_deg,
    sun_apparent_magnitude,
)
from terralab3d.domain.solar_system.catalog import (
    OrbitGeometry,
    SatelliteCatalogSnapshot,
    SolarSystemBodyDefinition,
)
from terralab3d.domain.solar_system.models import (
    ApparentBodyState,
    BodyKind,
    BodyOrientationState,
    CoverageStatus,
    EphemerisMetadata,
    EphemerisQuality,
    LunarOrientationQuality,
    LunarOrientationState,
    PhysicalModelQuality,
    RingPlaneDiagnostics,
    ScientificObserver,
    SolarSystemSnapshot,
)

from .kernel_manager import KernelManifestError, SpiceKernelManager

log = logging.getLogger("terralab3d.spice.ephemeris")

Matrix3 = tuple[
    tuple[float, float, float],
    tuple[float, float, float],
    tuple[float, float, float],
]
Vector3 = tuple[float, float, float]

PLANETS = (
    ("mercury", 199, BodyKind.PLANET),
    ("venus", 299, BodyKind.PLANET),
    ("mars", 499, BodyKind.PLANET),
    ("jupiter", 599, BodyKind.PLANET),
    ("saturn", 699, BodyKind.PLANET),
    ("uranus", 799, BodyKind.PLANET),
    ("neptune", 899, BodyKind.PLANET),
    ("pluto", 999, BodyKind.DWARF_PLANET),
)

BODY_FIXED_FRAMES = {
    199: "IAU_MERCURY",
    299: "IAU_VENUS",
    301: "MOON_ME_DE421",
    499: "IAU_MARS",
    599: "IAU_JUPITER",
    699: "IAU_SATURN",
    799: "IAU_URANUS",
    899: "IAU_NEPTUNE",
    999: "IAU_PLUTO",
}

BODY_DISPLAY_NAMES = {
    10: "Sun",
    199: "Mercury",
    299: "Venus",
    301: "Moon",
    499: "Mars",
    599: "Jupiter",
    699: "Saturn",
    799: "Uranus",
    899: "Neptune",
    999: "Pluto",
}


class SpiceEphemerisError(RuntimeError):
    code = "SPICE_EPHEMERIS_ERROR"

    def __init__(self, message: str, *, context: dict[str, Any], cause: Exception) -> None:
        super().__init__(message)
        self.context = context
        self.__cause__ = cause


class SpiceEphemerisAdapter:
    """One coherent DE440/NAIF state for planets and natural satellites."""

    def __init__(
        self,
        kernel_manifest_path: Path,
        satellite_catalog: SatelliteCatalogSnapshot,
    ) -> None:
        self._manager = SpiceKernelManager(kernel_manifest_path)
        self._catalog = satellite_catalog
        self._active_satellite_systems: frozenset[str] = frozenset()
        self._closed = False
        self._earth_frame_fallback = False
        self._orientation_cache: dict[tuple[int, int, int, int], BodyOrientationState] = {}
        self._orbit_generation = 0
        self.query_count = 0
        self.orientation_query_count = 0
        self.last_query_duration_ms = 0.0
        self.last_orientation_duration_ms = 0.0
        self._manager.open()
        self._metadata = EphemerisMetadata(
            kernel_name="DE440 + planetary satellite SPK",
            kernel_path=None,
            kernel_sha256=None,
            range_start_utc=None,
            range_end_utc=None,
            skyfield_version=None,
            lunar_orientation_frame="MOON_ME_DE421",
            provider="spiceypy",
            aberration_policy=self._manager.aberration_policy,
            reference_frame="J2000/ICRF",
            kernel_generation=self._manager.generation,
            kernel_manifest_path=str(kernel_manifest_path.resolve()),
        )

    @property
    def metadata(self) -> EphemerisMetadata:
        return self._metadata

    @property
    def lunar_orientation_kernel_load_count(self) -> int:
        return 1 if any(item.file_name.endswith(".bpc") for item in self._manager.kernels) else 0

    @property
    def satellite_catalog(self) -> SatelliteCatalogSnapshot:
        return self._catalog

    @property
    def active_satellite_systems(self) -> frozenset[str]:
        return self._active_satellite_systems

    def set_satellite_systems(self, systems: Iterable[str]) -> None:
        allowed = frozenset(self._catalog.by_parent)
        requested = frozenset(str(item).lower() for item in systems)
        unknown = requested - allowed
        if unknown:
            raise ValueError(f"Unknown satellite system(s): {', '.join(sorted(unknown))}")
        self._active_satellite_systems = requested
        log.info(
            "MGP: [SpiceEphemerisAdapter.py] [set_satellite_systems] [Actius=%s]",
            ",".join(sorted(requested)) or "none",
        )

    def utc_to_et(self, utc: datetime) -> float:
        instant = _as_utc(utc)
        spice = _spice()
        with self._manager.lock:
            return float(spice.str2et(instant.strftime("%Y-%m-%dT%H:%M:%S.%f")))

    def snapshot(self, utc: datetime, observer: ScientificObserver) -> SolarSystemSnapshot:
        if self._closed:
            raise SpiceEphemerisError(
                "SPICE adapter is closed", context={"operation": "snapshot"}, cause=RuntimeError()
            )
        instant = _as_utc(utc)
        started = time.perf_counter()
        spice = _spice()
        unavailable: list[str] = []
        with self._manager.lock:
            try:
                et = float(spice.str2et(instant.strftime("%Y-%m-%dT%H:%M:%S.%f")))
                earth_frame = self._earth_fixed_frame(spice, et)
                observer_position = self._observer_position(spice, observer)
                icrf_to_enu = self._icrf_to_enu(spice, et, observer, earth_frame)

                sun = self._body_state(
                    spice, "sun", 10, BodyKind.SUN, None, et, instant,
                    observer, observer_position, earth_frame, icrf_to_enu,
                )
                moon: ApparentBodyState | None
                try:
                    moon = self._body_state(
                        spice, "moon", 301, BodyKind.MOON, 399, et, instant,
                        observer, observer_position, earth_frame, icrf_to_enu,
                    )
                    bright_limb = bright_limb_position_angle_deg(
                        moon.equatorial.right_ascension_deg,
                        moon.equatorial.declination_deg,
                        sun.equatorial.right_ascension_deg,
                        sun.equatorial.declination_deg,
                    )
                    moon = replace(
                        moon,
                        bright_limb_position_angle_deg=bright_limb,
                        orientation=self._lunar_orientation(
                            spice, et, observer_position, earth_frame, icrf_to_enu,
                            moon, bright_limb,
                        ),
                    )
                except Exception as exc:
                    moon = None
                    unavailable.append(f"moon:{_spice_error_name(exc)}")

                planets = []
                for body_id, naif_id, kind in PLANETS:
                    try:
                        planets.append(
                            self._body_state(
                                spice, body_id, naif_id, kind, None, et, instant,
                                observer, observer_position, earth_frame, icrf_to_enu,
                            )
                        )
                    except Exception as exc:
                        unavailable.append(f"{body_id}:{_spice_error_name(exc)}")

                satellite_states = []
                selected = self._catalog.for_parents(self._active_satellite_systems)
                for definition in selected:
                    if definition.naif_id == 301:
                        continue
                    coverage = definition.coverage_at(et)
                    if coverage is not CoverageStatus.IN_RANGE or definition.naif_id is None:
                        unavailable.append(f"{definition.name}:{coverage.value}")
                        continue
                    try:
                        satellite_states.append(
                            self._body_state(
                                spice,
                                definition.body_id,
                                definition.naif_id,
                                BodyKind.NATURAL_SATELLITE,
                                definition.parent_naif_id,
                                et,
                                instant,
                                observer,
                                observer_position,
                                earth_frame,
                                icrf_to_enu,
                                definition,
                            )
                        )
                    except Exception as exc:
                        unavailable.append(f"{definition.name}:{_spice_error_name(exc)}")

                self.query_count += 1
                self.last_query_duration_ms = (time.perf_counter() - started) * 1000.0
                visible_count = sum(item.horizon_visible for item in satellite_states)
                detail_parts = []
                if self._earth_frame_fallback:
                    detail_parts.append("ITRF93 out of range; explicit IAU_EARTH fallback")
                if unavailable:
                    detail_parts.append(
                        f"unavailable={len(unavailable)} [{', '.join(unavailable[:8])}]"
                    )
                return SolarSystemSnapshot(
                    generation=0,
                    timestamp_utc=instant,
                    observer_generation=0,
                    source="SPICE/DE440",
                    quality=EphemerisQuality.PRECISE,
                    sun=sun,
                    moon=moon,
                    planets=tuple(planets),
                    satellites=tuple(satellite_states),
                    catalog_count=self._catalog.total_count,
                    satellite_ephemeris_count=self._catalog.with_spk_count,
                    satellite_visible_count=visible_count,
                    kernel_generation=self._manager.generation,
                    kernel_status="ready" if not self._earth_frame_fallback else "degraded-earth-frame",
                    icrf_to_enu_quaternion=rotation_matrix_to_quaternion(icrf_to_enu),
                    compute_ms=self.last_query_duration_ms,
                    detail="; ".join(detail_parts) or None,
                )
            except Exception as exc:
                raise SpiceEphemerisError(
                    f"Cannot calculate coherent SPICE snapshot at {instant.isoformat()}",
                    context={
                        "operation": "snapshot",
                        "instantUtc": instant.isoformat(),
                        "kernelGeneration": self._manager.generation,
                    },
                    cause=exc,
                ) from exc

    def sample_orbit(
        self,
        definition: SolarSystemBodyDefinition,
        start_et: float,
        end_et: float,
        sample_count: int,
    ) -> OrbitGeometry:
        if definition.naif_id is None or not definition.has_spk:
            raise ValueError(f"{definition.name} has no SPK")
        if sample_count < 2 or sample_count > 8192 or end_et <= start_et:
            raise ValueError("Orbit sampling requires 2..8192 samples and a positive interval")
        if definition.coverage_at(start_et) is not CoverageStatus.IN_RANGE:
            raise ValueError(f"Orbit start is outside coverage for {definition.name}")
        if definition.coverage_at(end_et) is not CoverageStatus.IN_RANGE:
            raise ValueError(f"Orbit end is outside coverage for {definition.name}")
        spice = _spice()
        started = time.perf_counter()
        with self._manager.lock:
            positions = []
            for index in range(sample_count):
                fraction = index / (sample_count - 1)
                et = start_et + (end_et - start_et) * fraction
                state, _ = spice.spkezr(
                    str(definition.naif_id),
                    et,
                    "J2000",
                    "NONE",
                    str(definition.parent_naif_id),
                )
                positions.append(_vector3(state[:3]))
            self._orbit_generation += 1
            elapsed = (time.perf_counter() - started) * 1000.0
            log.info(
                "MGP: [OrbitSampler.py] [sample] "
                "[Òrbita mostrejada body=%s samples=%d duration_ms=%.1f]",
                definition.name,
                sample_count,
                elapsed,
            )
            return OrbitGeometry(
                body_id=definition.body_id,
                parent_body_id=definition.parent_body_id,
                start_et=start_et,
                end_et=end_et,
                sample_count=sample_count,
                frame="J2000 planetocentric",
                kernel_generation=self._manager.generation,
                orbit_generation=self._orbit_generation,
                positions_parent_fixed_km=tuple(positions),
            )

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        self._orientation_cache.clear()
        self._manager.close()

    def _body_state(
        self,
        spice: Any,
        body_id: str,
        naif_id: int,
        kind: BodyKind,
        parent_naif_id: int | None,
        et: float,
        instant: datetime,
        observer: ScientificObserver,
        observer_position: Vector3,
        earth_frame: str,
        icrf_to_enu: Matrix3,
        definition: SolarSystemBodyDefinition | None = None,
    ) -> ApparentBodyState:
        topocentric_state, _ = spice.spkcpo(
            str(naif_id),
            et,
            "J2000",
            "OBSERVER",
            self._manager.aberration_policy,
            observer_position,
            "EARTH",
            earth_frame,
        )
        observer_to_body = _vector3(topocentric_state[:3])
        distance_km = _norm(observer_to_body)
        direction_icrf = normalize_vector(observer_to_body)
        direction_enu_axes = normalize_vector(matrix3_apply(icrf_to_enu, direction_icrf))
        direction_wire = _enu_to_wire(direction_enu_axes)
        altitude_deg = math.degrees(math.asin(_clamp(direction_enu_axes[2], -1.0, 1.0)))
        azimuth_deg = math.degrees(math.atan2(direction_enu_axes[0], direction_enu_axes[1])) % 360.0
        _, right_ascension_rad, declination_rad = spice.recrad(observer_to_body)

        absolute_state, _ = spice.spkezr(str(naif_id), et, "J2000", "NONE", "0")
        body_to_sun_state, _ = spice.spkezr(
            "10", et, "J2000", self._manager.aberration_policy, str(naif_id)
        ) if naif_id != 10 else ([-value for value in topocentric_state], 0.0)
        body_to_sun_icrf = normalize_vector(_vector3(body_to_sun_state[:3]))
        body_to_sun_enu_axes = normalize_vector(matrix3_apply(icrf_to_enu, body_to_sun_icrf))
        body_to_sun_wire = _enu_to_wire(body_to_sun_enu_axes)
        body_to_observer = normalize_vector(tuple(-value for value in observer_to_body))
        phase_angle_deg = (
            0.0
            if naif_id == 10
            else math.degrees(math.acos(_clamp(_dot(body_to_observer, body_to_sun_icrf), -1.0, 1.0)))
        )

        radii = definition.radii_km if definition is not None else self._pck_radii(spice, naif_id)
        mean_radius = definition.mean_radius_km if definition is not None else _mean_radius(radii)
        angular_radius = (
            math.degrees(math.atan2(mean_radius, distance_km)) if mean_radius is not None else 0.0
        )
        frame = definition.body_fixed_frame if definition is not None else BODY_FIXED_FRAMES.get(naif_id)
        orientation = None
        orientation_quality = PhysicalModelQuality.UNAVAILABLE
        if kind not in {BodyKind.SUN, BodyKind.MOON} and frame is not None:
            orientation = self._body_orientation(
                spice, naif_id, frame, et, icrf_to_enu, body_to_sun_wire
            )
            orientation_quality = orientation.quality

        ring_diagnostics = None
        if naif_id == 699 and isinstance(orientation, BodyOrientationState):
            ring_diagnostics = self._ring_diagnostics(
                spice, naif_id, et, orientation.north_pole_icrf, body_to_observer,
                body_to_sun_icrf,
            )
        magnitude = self._magnitude(
            spice,
            naif_id,
            kind,
            et,
            instant,
            distance_km,
            phase_angle_deg,
            ring_diagnostics,
        )
        shape_quality = (
            definition.shape_quality
            if definition is not None
            else PhysicalModelQuality.IAU_MODEL if radii is not None else PhysicalModelQuality.UNAVAILABLE
        )
        coverage = definition.coverage_at(et) if definition is not None else CoverageStatus.IN_RANGE
        return ApparentBodyState(
            body_id=CelestialBodyId(body_id),
            kind=kind,
            equatorial=EquatorialCoordinate(
                math.degrees(right_ascension_rad) % 360.0,
                math.degrees(declination_rad),
            ),
            horizontal=HorizontalCoordinate(altitude_deg, azimuth_deg),
            direction_enu=direction_wire,
            distance_km=distance_km,
            angular_radius_deg=angular_radius,
            illumination_fraction=illuminated_fraction(phase_angle_deg),
            phase_angle_deg=phase_angle_deg,
            apparent_magnitude=magnitude,
            source="SPICE/DE440",
            quality=EphemerisQuality.PRECISE,
            display_name=definition.name if definition is not None else BODY_DISPLAY_NAMES.get(naif_id),
            orientation=orientation,
            naif_id=naif_id,
            parent_naif_id=parent_naif_id,
            parent_body_id=definition.parent_body_id if definition is not None else None,
            position_icrf_km=_vector3(absolute_state[:3]),
            velocity_icrf_km_s=_vector3(absolute_state[3:]),
            radii_km=radii,
            mean_radius_km=mean_radius,
            body_to_sun_direction_enu=body_to_sun_wire,
            ephemeris_kernel_id=self._manager.active_kernel_id(naif_id, et),
            coverage_status=coverage,
            orientation_quality=orientation_quality,
            shape_quality=shape_quality,
            texture_quality=(
                definition.texture_quality if definition is not None
                else PhysicalModelQuality.VISUAL_REFERENCE if naif_id in {199, 299, 499, 599, 699, 799, 899} else PhysicalModelQuality.UNAVAILABLE
            ),
            geometric_elevation_deg=altitude_deg,
            horizon_elevation_deg=0.0,
            horizon_visible=altitude_deg + angular_radius > 0.0,
            refraction_applied=False,
            ring_diagnostics=ring_diagnostics,
        )

    def _body_orientation(
        self,
        spice: Any,
        naif_id: int,
        frame: str,
        et: float,
        icrf_to_enu: Matrix3,
        body_to_sun_wire: Vector3,
    ) -> BodyOrientationState:
        # Pole orientation evolves slowly; the one-second bucket preserves W
        # for textured surfaces while preventing duplicate work per batch.
        key = (naif_id, round(et), hash(icrf_to_enu), hash(frame))
        cached = self._orientation_cache.get(key)
        if cached is not None:
            return cached
        started = time.perf_counter()
        try:
            body_to_icrf = _matrix3(spice.pxform(frame, "J2000", et))
            body_to_enu = matrix3_multiply(icrf_to_enu, body_to_icrf)
            pole_icrf = normalize_vector(matrix3_apply(body_to_icrf, (0.0, 0.0, 1.0)))
            equatorial_to_icrf = _equatorial_basis(pole_icrf)
            equatorial_to_enu = matrix3_multiply(icrf_to_enu, equatorial_to_icrf)
            value = BodyOrientationState(
                frame=frame,
                source="NAIF PCK pck00011",
                quality=PhysicalModelQuality.IAU_MODEL,
                body_to_enu_quaternion=rotation_matrix_to_quaternion(body_to_enu),
                equatorial_to_enu_quaternion=rotation_matrix_to_quaternion(equatorial_to_enu),
                body_to_sun_direction_enu=body_to_sun_wire,
                north_pole_icrf=pole_icrf,
                compute_ms=(time.perf_counter() - started) * 1000.0,
            )
        except Exception as exc:
            value = BodyOrientationState(
                frame=frame,
                source="NAIF PCK pck00011",
                quality=PhysicalModelQuality.UNAVAILABLE,
                body_to_enu_quaternion=None,
                equatorial_to_enu_quaternion=None,
                body_to_sun_direction_enu=body_to_sun_wire,
                north_pole_icrf=None,
                compute_ms=(time.perf_counter() - started) * 1000.0,
                detail=str(exc),
            )
        self.orientation_query_count += 1
        self.last_orientation_duration_ms = value.compute_ms
        if len(self._orientation_cache) > 4096:
            self._orientation_cache.clear()
        self._orientation_cache[key] = value
        return value

    def _lunar_orientation(
        self,
        spice: Any,
        et: float,
        observer_position: Vector3,
        earth_frame: str,
        icrf_to_enu: Matrix3,
        moon: ApparentBodyState,
        bright_limb: float,
    ) -> LunarOrientationState:
        started = time.perf_counter()
        frame = "MOON_ME_DE421"
        try:
            body_to_icrf = _matrix3(spice.pxform(frame, "J2000", et))
            body_to_enu = matrix3_multiply(icrf_to_enu, body_to_icrf)
            earth_state, _ = spice.spkezr(
                "399", et, "J2000", self._manager.aberration_policy, "301"
            )
            sun_state, _ = spice.spkezr(
                "10", et, "J2000", self._manager.aberration_policy, "301"
            )
            # The exact topocentric direction is the inverse of observer→Moon.
            moon_to_observer = normalize_vector(
                tuple(-value for value in _wire_to_canonical_icrf(moon.direction_enu, icrf_to_enu))
            )
            icrf_to_body = matrix3_transpose(body_to_icrf)
            sub_earth_lon, sub_earth_lat = _lon_lat(matrix3_apply(icrf_to_body, _vector3(earth_state[:3])))
            sub_observer_lon, sub_observer_lat = _lon_lat(matrix3_apply(icrf_to_body, moon_to_observer))
            pole_icrf = normalize_vector(matrix3_apply(body_to_icrf, (0.0, 0.0, 1.0)))
            sun_wire = _enu_to_wire(
                normalize_vector(matrix3_apply(icrf_to_enu, _vector3(sun_state[:3])))
            )
            return LunarOrientationState(
                frame=frame,
                source="DE440 + MOON_ME_DE421",
                quality=LunarOrientationQuality.PRECISE,
                body_to_enu_quaternion=rotation_matrix_to_quaternion(body_to_enu),
                libration_longitude_deg=sub_earth_lon,
                libration_latitude_deg=sub_earth_lat,
                sub_earth_longitude_deg=sub_earth_lon,
                sub_earth_latitude_deg=sub_earth_lat,
                sub_observer_longitude_deg=sub_observer_lon,
                sub_observer_latitude_deg=sub_observer_lat,
                north_pole_position_angle_deg=north_pole_position_angle_deg(
                    normalize_vector(_wire_to_canonical_icrf(moon.direction_enu, icrf_to_enu)),
                    pole_icrf,
                ),
                bright_limb_position_angle_deg=bright_limb,
                moon_to_sun_direction_enu=sun_wire,
                compute_ms=(time.perf_counter() - started) * 1000.0,
            )
        except Exception as exc:
            return LunarOrientationState(
                frame=frame,
                source="MOON_ME_DE421",
                quality=LunarOrientationQuality.UNAVAILABLE,
                body_to_enu_quaternion=None,
                libration_longitude_deg=None,
                libration_latitude_deg=None,
                sub_earth_longitude_deg=None,
                sub_earth_latitude_deg=None,
                sub_observer_longitude_deg=None,
                sub_observer_latitude_deg=None,
                north_pole_position_angle_deg=None,
                bright_limb_position_angle_deg=bright_limb,
                moon_to_sun_direction_enu=moon.body_to_sun_direction_enu,
                compute_ms=(time.perf_counter() - started) * 1000.0,
                detail=str(exc),
            )

    @staticmethod
    def _ring_diagnostics(
        spice: Any,
        naif_id: int,
        et: float,
        pole_icrf: Vector3 | None,
        body_to_observer: Vector3,
        body_to_sun: Vector3,
    ) -> RingPlaneDiagnostics | None:
        if pole_icrf is None:
            return None
        earth_state, _ = spice.spkezr("399", et, "J2000", "LT+S", str(naif_id))
        body_to_earth = normalize_vector(_vector3(earth_state[:3]))
        return RingPlaneDiagnostics(
            opening_geocentric_deg=math.degrees(math.asin(_clamp(_dot(pole_icrf, body_to_earth), -1.0, 1.0))),
            opening_topocentric_deg=math.degrees(math.asin(_clamp(_dot(pole_icrf, body_to_observer), -1.0, 1.0))),
            sun_elevation_deg=math.degrees(math.asin(_clamp(_dot(pole_icrf, body_to_sun), -1.0, 1.0))),
        )

    @staticmethod
    def _magnitude(
        spice: Any,
        naif_id: int,
        kind: BodyKind,
        et: float,
        instant: datetime,
        observer_distance_km: float,
        phase_angle_deg: float,
        rings: RingPlaneDiagnostics | None,
    ) -> float | None:
        if kind is BodyKind.SUN:
            return sun_apparent_magnitude(observer_distance_km / AU_KM)
        sun_state, _ = spice.spkezr("10", et, "J2000", "NONE", str(naif_id))
        sun_distance_au = _norm(_vector3(sun_state[:3])) / AU_KM
        if kind is BodyKind.MOON:
            return moon_apparent_magnitude(
                observer_distance_km / AU_KM, sun_distance_au, phase_angle_deg
            )
        year_start = datetime(instant.year, 1, 1, tzinfo=timezone.utc)
        next_year = datetime(instant.year + 1, 1, 1, tzinfo=timezone.utc)
        decimal_year = instant.year + (instant - year_start) / (next_year - year_start)
        return planet_apparent_magnitude(
            naif_id,
            sun_distance_au,
            observer_distance_km / AU_KM,
            phase_angle_deg,
            ring_opening_sun_deg=rings.sun_elevation_deg if rings else 0.0,
            ring_opening_observer_deg=rings.opening_topocentric_deg if rings else 0.0,
            decimal_year=decimal_year,
        )

    @staticmethod
    def _pck_radii(spice: Any, naif_id: int) -> tuple[float, float, float] | None:
        try:
            _, radii = spice.bodvcd(naif_id, "RADII", 3)
            return _vector3(radii)
        except Exception:
            return None

    def _earth_fixed_frame(self, spice: Any, et: float) -> str:
        try:
            spice.pxform("J2000", "ITRF93", et)
            self._earth_frame_fallback = False
            return "ITRF93"
        except Exception:
            spice.pxform("J2000", "IAU_EARTH", et)
            self._earth_frame_fallback = True
            return "IAU_EARTH"

    @staticmethod
    def _observer_position(spice: Any, observer: ScientificObserver) -> Vector3:
        _, radii = spice.bodvcd(399, "RADII", 3)
        flattening = (float(radii[0]) - float(radii[2])) / float(radii[0])
        return _vector3(
            spice.georec(
                math.radians(observer.longitude_deg),
                math.radians(observer.latitude_deg),
                observer.elevation_m / 1000.0,
                float(radii[0]),
                flattening,
            )
        )

    @staticmethod
    def _icrf_to_enu(
        spice: Any,
        et: float,
        observer: ScientificObserver,
        earth_frame: str,
    ) -> Matrix3:
        icrf_to_earth = _matrix3(spice.pxform("J2000", earth_frame, et))
        earth_to_enu = ecef_to_enu_rotation(observer.latitude_deg, observer.longitude_deg)
        return matrix3_multiply(earth_to_enu, icrf_to_earth)


def _spice() -> Any:
    try:
        import spiceypy as spice
    except ImportError as exc:
        raise KernelManifestError("spiceypy is not installed") from exc
    return spice


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        raise ValueError("Ephemeris instants must be timezone-aware")
    return value.astimezone(timezone.utc)


def _matrix3(value: Any) -> Matrix3:
    return tuple(
        tuple(float(value[row][column]) for column in range(3)) for row in range(3)
    )  # type: ignore[return-value]


def _vector3(value: Any) -> Vector3:
    return float(value[0]), float(value[1]), float(value[2])


def _norm(value: Vector3) -> float:
    return math.sqrt(_dot(value, value))


def _dot(first: Vector3, second: Vector3) -> float:
    return sum(a * b for a, b in zip(first, second, strict=True))


def _cross(first: Vector3, second: Vector3) -> Vector3:
    return (
        first[1] * second[2] - first[2] * second[1],
        first[2] * second[0] - first[0] * second[2],
        first[0] * second[1] - first[1] * second[0],
    )


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def _enu_to_wire(canonical: Vector3) -> Vector3:
    east, north, up = canonical
    return east, up, north


def _wire_to_canonical_icrf(wire: Vector3, icrf_to_enu: Matrix3) -> Vector3:
    east, up, north = wire
    enu = (east, north, up)
    return normalize_vector(matrix3_apply(matrix3_transpose(icrf_to_enu), enu))


def _mean_radius(radii: Vector3 | None) -> float | None:
    return (radii[0] * radii[1] * radii[2]) ** (1.0 / 3.0) if radii else None


def _equatorial_basis(pole: Vector3) -> Matrix3:
    reference = (0.0, 0.0, 1.0)
    if abs(_dot(reference, pole)) > 0.98:
        reference = (1.0, 0.0, 0.0)
    x_axis = normalize_vector(_cross(reference, pole))
    y_axis = normalize_vector(_cross(pole, x_axis))
    return (
        (x_axis[0], y_axis[0], pole[0]),
        (x_axis[1], y_axis[1], pole[1]),
        (x_axis[2], y_axis[2], pole[2]),
    )


def _lon_lat(vector: Vector3) -> tuple[float, float]:
    unit = normalize_vector(vector)
    return (
        signed_longitude_deg(math.degrees(math.atan2(unit[1], unit[0]))),
        math.degrees(math.asin(_clamp(unit[2], -1.0, 1.0))),
    )


def _spice_error_name(exc: Exception) -> str:
    return getattr(exc, "short", None) or type(exc).__name__
