"""Skyfield/DE421 adapter with an explicit local-only kernel policy."""

from __future__ import annotations

import hashlib
import logging
import math
import os
import time
from dataclasses import replace
from datetime import datetime, timezone
from importlib.metadata import version
from pathlib import Path
from typing import Any

from terralab3d.domain.geometry import EquatorialCoordinate, HorizontalCoordinate
from terralab3d.domain.identifiers import CelestialBodyId
from terralab3d.domain.sky_background.solar_direction import sun_direction_enu
from terralab3d.domain.solar_system.calculations import (
    AU_KM,
    analytical_sun_state,
    angular_radius_deg,
    bright_limb_position_angle_deg,
    ecef_to_enu_rotation,
    matrix3_apply,
    matrix3_multiply,
    matrix3_transpose,
    moon_apparent_magnitude,
    north_pole_position_angle_deg,
    normalize_vector,
    rotation_matrix_to_quaternion,
    signed_longitude_deg,
    sun_apparent_magnitude,
)
from terralab3d.domain.solar_system.models import (
    ApparentBodyState,
    BodyKind,
    EphemerisMetadata,
    EphemerisQuality,
    LunarOrientationQuality,
    LunarOrientationState,
    ScientificObserver,
    SolarSystemSnapshot,
)
from terralab3d.infrastructure.app_paths import resolve_data_root

log = logging.getLogger("terralab3d.ephemeris")

EPHEMERIS_PATH_ENV = "TERRALAB3D_EPHEMERIS_PATH"
LUNAR_ORIENTATION_DIR_ENV = "TERRALAB3D_LUNAR_ORIENTATION_DIR"
KERNEL_NAME = "de421.bsp"
LUNAR_FRAME_NAME = "MOON_ME_DE421"
LUNAR_FRAME_KERNEL_NAME = "moon_080317.tf"
LUNAR_ORIENTATION_KERNEL_NAME = "moon_pa_de421_1900-2050.bpc"
LUNAR_ORIENTATION_RANGE_START = datetime(1900, 1, 1, tzinfo=timezone.utc)
LUNAR_ORIENTATION_RANGE_END = datetime(2051, 1, 1, tzinfo=timezone.utc)
BODY_SPECS = (
    ("mercury", "mercury", 2_439.7),
    ("venus", "venus", 6_051.8),
    ("mars", "mars", 3_389.5),
    ("jupiter", "jupiter barycenter", 69_911.0),
    ("saturn", "saturn barycenter", 58_232.0),
    ("uranus", "uranus barycenter", 25_362.0),
    ("neptune", "neptune barycenter", 24_622.0),
)


class SkyfieldEphemerisAdapter:
    """Loads one local DE421 kernel and never asks Skyfield to download data."""

    def __init__(self, kernel_path: Path | None = None) -> None:
        self._requested_kernel_path = kernel_path
        self._ephemeris: Any | None = None
        self._timescale: Any | None = None
        self._wgs84: Any | None = None
        self._planetary_magnitude: Any | None = None
        self._itrs: Any | None = None
        self._planetary_constants: Any | None = None
        self._lunar_orientation_frame: Any | None = None
        self._lunar_orientation_binary_file: Any | None = None
        self._range_jd: tuple[float, float] | None = None
        self._unavailable_detail: str | None = None
        self._orientation_unavailable_detail: str | None = None
        self._lunar_orientation_kernel_load_count = 0
        self._metadata = EphemerisMetadata(None, None, None, None, None, None)
        self.open()

    @property
    def metadata(self) -> EphemerisMetadata:
        return self._metadata

    @property
    def lunar_orientation_kernel_load_count(self) -> int:
        return self._lunar_orientation_kernel_load_count

    def open(self) -> None:
        if self._ephemeris is not None:
            return
        try:
            from skyfield.api import load, load_file, wgs84
            from skyfield.framelib import itrs
            from skyfield.magnitudelib import planetary_magnitude

            kernel_path = self._resolve_kernel_path()
            if kernel_path is None:
                raise FileNotFoundError(
                    f"{KERNEL_NAME} not found in {EPHEMERIS_PATH_ENV}, the TerraLab data library, or skyfield-data"
                )
            self._timescale = load.timescale(builtin=True)
            self._ephemeris = load_file(str(kernel_path))
            self._wgs84 = wgs84
            self._itrs = itrs
            self._planetary_magnitude = planetary_magnitude

            segment = self._ephemeris.segments[0].spk_segment
            self._range_jd = (float(segment.start_jd), float(segment.end_jd))
            digest = _sha256(kernel_path)
            self._metadata = EphemerisMetadata(
                kernel_name=KERNEL_NAME,
                kernel_path=str(kernel_path),
                kernel_sha256=digest,
                range_start_utc="1899-07-28",
                range_end_utc="2053-10-08",
                skyfield_version=version("skyfield"),
            )
            self._unavailable_detail = None
            self._open_lunar_orientation()
            log.info(
                "DE421 loaded once: %s sha256=%s range=%s..%s",
                kernel_path,
                digest,
                self._metadata.range_start_utc,
                self._metadata.range_end_utc,
            )
        except (ImportError, OSError, ValueError) as exc:
            self._unavailable_detail = str(exc)
            self._ephemeris = None
            self._timescale = None
            log.warning("DE421 unavailable; using the analytical Sun fallback: %s", exc)

    def snapshot(
        self,
        utc: datetime,
        observer: ScientificObserver,
    ) -> SolarSystemSnapshot:
        instant = _as_utc(utc)
        started = time.perf_counter()
        if self._ephemeris is None or self._timescale is None or self._wgs84 is None:
            return self._fallback_snapshot(instant, observer, started, self._unavailable_detail)

        try:
            time_point = self._timescale.from_datetime(instant)
            jd_tdb = float(time_point.tdb)
            if self._range_jd is None or not self._range_jd[0] <= jd_tdb <= self._range_jd[1]:
                detail = (
                    f"UTC {instant.isoformat()} lies outside DE421 range "
                    f"{self._metadata.range_start_utc}..{self._metadata.range_end_utc}"
                )
                return self._fallback_snapshot(instant, observer, started, detail)
            return self._skyfield_snapshot(instant, observer, time_point, started)
        except (KeyError, ValueError, ArithmeticError) as exc:
            log.warning("DE421 computation failed; using analytical Sun fallback: %s", exc)
            return self._fallback_snapshot(instant, observer, started, str(exc))

    def close(self) -> None:
        if self._ephemeris is not None:
            self._ephemeris.close()
        self._ephemeris = None
        self._timescale = None
        self._wgs84 = None
        self._itrs = None
        self._planetary_magnitude = None
        self._planetary_constants = None
        self._lunar_orientation_frame = None
        if self._lunar_orientation_binary_file is not None:
            self._lunar_orientation_binary_file.close()
        self._lunar_orientation_binary_file = None

    def _resolve_kernel_path(self) -> Path | None:
        if self._requested_kernel_path is not None:
            requested = self._requested_kernel_path.expanduser().resolve(strict=False)
            return requested if requested.is_file() else None

        configured = os.getenv(EPHEMERIS_PATH_ENV, "").strip()
        if configured:
            requested = Path(configured).expanduser().resolve(strict=False)
            if not requested.is_file():
                raise FileNotFoundError(f"Configured ephemeris does not exist: {requested}")
            return requested

        managed = resolve_data_root() / "data" / "sky" / "solar-system" / KERNEL_NAME
        if managed.is_file():
            return managed.resolve()

        try:
            from skyfield_data import get_skyfield_data_path

            packaged = Path(get_skyfield_data_path()) / KERNEL_NAME
            return packaged.resolve() if packaged.is_file() else None
        except ImportError:
            return None

    def _open_lunar_orientation(self) -> None:
        if self._lunar_orientation_frame is not None:
            return
        try:
            from skyfield.api import PlanetaryConstants

            frame_path, orientation_path = self._resolve_lunar_orientation_paths()
            constants = PlanetaryConstants()
            constants.read_text(frame_path.open("rb"))
            binary_file = orientation_path.open("rb")
            try:
                constants.read_binary(binary_file)
                frame = constants.build_frame_named(LUNAR_FRAME_NAME)
            except Exception:
                binary_file.close()
                raise

            self._planetary_constants = constants
            self._lunar_orientation_binary_file = binary_file
            self._lunar_orientation_frame = frame
            self._lunar_orientation_kernel_load_count += 1
            self._orientation_unavailable_detail = None
            self._metadata = replace(
                self._metadata,
                lunar_orientation_frame=LUNAR_FRAME_NAME,
                lunar_frame_kernel_sha256=_sha256(frame_path),
                lunar_orientation_kernel_sha256=_sha256(orientation_path),
                lunar_orientation_range_start_utc="1900-01-01",
                lunar_orientation_range_end_utc="2050-12-31",
            )
            log.info(
                "Lunar orientation loaded once: frame=%s kernels=%s,%s",
                LUNAR_FRAME_NAME,
                frame_path,
                orientation_path,
            )
        except Exception as exc:
            # Infrastructure boundary: a malformed optional orientation layer
            # must not take down the authoritative Step 8 position/phase path.
            self._orientation_unavailable_detail = str(exc)
            self._planetary_constants = None
            self._lunar_orientation_frame = None
            log.warning("Lunar orientation unavailable; retaining the Step 8 Moon: %s", exc)

    def _resolve_lunar_orientation_paths(self) -> tuple[Path, Path]:
        configured = os.getenv(LUNAR_ORIENTATION_DIR_ENV, "").strip()
        orientation_dir = (
            Path(configured).expanduser().resolve(strict=False)
            if configured
            else resolve_data_root() / "data" / "sky" / "moon" / "orientation"
        )
        frame_path = orientation_dir / LUNAR_FRAME_KERNEL_NAME
        orientation_path = orientation_dir / LUNAR_ORIENTATION_KERNEL_NAME
        missing = [str(path) for path in (frame_path, orientation_path) if not path.is_file()]
        if missing:
            raise FileNotFoundError("Missing local lunar orientation kernel(s): " + ", ".join(missing))
        return frame_path.resolve(), orientation_path.resolve()

    def _skyfield_snapshot(
        self,
        instant: datetime,
        observer: ScientificObserver,
        time_point: Any,
        started: float,
    ) -> SolarSystemSnapshot:
        earth = self._ephemeris["earth"]
        sun = self._ephemeris["sun"]
        moon = self._ephemeris["moon"]
        location = self._wgs84.latlon(
            latitude_degrees=observer.latitude_deg,
            longitude_degrees=observer.longitude_deg,
            elevation_m=observer.elevation_m,
        )
        observer_at = (earth + location).at(time_point)

        sun_state = self._body_state(
            "sun", BodyKind.SUN, sun, 695_700.0, observer_at, sun, time_point
        )
        moon_state = self._body_state(
            "moon", BodyKind.MOON, moon, 1_737.4, observer_at, sun, time_point
        )
        moon_state = replace(
            moon_state,
            bright_limb_position_angle_deg=bright_limb_position_angle_deg(
                moon_state.equatorial.right_ascension_deg,
                moon_state.equatorial.declination_deg,
                sun_state.equatorial.right_ascension_deg,
                sun_state.equatorial.declination_deg,
            ),
        )
        moon_state = replace(
            moon_state,
            orientation=self._lunar_orientation(
                instant,
                observer,
                time_point,
                earth,
                location,
                moon,
                sun,
                moon_state.bright_limb_position_angle_deg,
            ),
        )
        planets = tuple(
            self._body_state(
                body_id,
                BodyKind.PLANET,
                self._ephemeris[kernel_key],
                radius_km,
                observer_at,
                sun,
                time_point,
            )
            for body_id, kernel_key, radius_km in BODY_SPECS
        )
        return SolarSystemSnapshot(
            generation=0,
            timestamp_utc=instant,
            observer_generation=0,
            source="DE421",
            quality=EphemerisQuality.PRECISE,
            sun=sun_state,
            moon=moon_state,
            planets=planets,
            compute_ms=(time.perf_counter() - started) * 1000.0,
            scientific_observer=observer,
        )

    def _lunar_orientation(
        self,
        instant: datetime,
        observer: ScientificObserver,
        time_point: Any,
        earth: Any,
        location: Any,
        moon: Any,
        sun: Any,
        bright_limb_position_angle: float | None,
    ) -> LunarOrientationState:
        started = time.perf_counter()
        if self._lunar_orientation_frame is None or self._itrs is None:
            return self._unavailable_lunar_orientation(
                LunarOrientationQuality.UNAVAILABLE,
                started,
                self._orientation_unavailable_detail,
                bright_limb_position_angle,
            )
        if not LUNAR_ORIENTATION_RANGE_START <= instant < LUNAR_ORIENTATION_RANGE_END:
            return self._unavailable_lunar_orientation(
                LunarOrientationQuality.OUT_OF_RANGE,
                started,
                (
                    f"UTC {instant.isoformat()} lies outside lunar orientation range "
                    "1900-01-01..2050-12-31"
                ),
                bright_limb_position_angle,
            )

        try:
            body_to_icrf = matrix3_transpose(_matrix3(self._lunar_orientation_frame.rotation_at(time_point)))
            icrf_to_itrs = _matrix3(self._itrs.rotation_at(time_point))
            itrs_to_enu = ecef_to_enu_rotation(observer.latitude_deg, observer.longitude_deg)
            body_to_enu = matrix3_multiply(
                itrs_to_enu,
                matrix3_multiply(icrf_to_itrs, body_to_icrf),
            )

            sub_earth_lat, sub_earth_lon, _ = (earth - moon).at(time_point).frame_latlon(
                self._lunar_orientation_frame
            )
            observer_position = earth + location
            sub_observer_lat, sub_observer_lon, _ = (
                observer_position - moon
            ).at(time_point).frame_latlon(self._lunar_orientation_frame)

            moon_to_sun_icrf = normalize_vector(
                _vector3((sun - moon).at(time_point).position.km)
            )
            moon_to_sun_enu_axes = normalize_vector(
                matrix3_apply(itrs_to_enu, matrix3_apply(icrf_to_itrs, moon_to_sun_icrf))
            )
            moon_to_sun_eun = (
                moon_to_sun_enu_axes[0],
                moon_to_sun_enu_axes[2],
                moon_to_sun_enu_axes[1],
            )
            observer_to_moon_icrf = normalize_vector(
                _vector3((moon - observer_position).at(time_point).position.km)
            )
            lunar_north_icrf = normalize_vector(matrix3_apply(body_to_icrf, (0.0, 0.0, 1.0)))
            celestial_north_icrf = normalize_vector(
                matrix3_apply(matrix3_transpose(_matrix3(time_point.M)), (0.0, 0.0, 1.0))
            )

            sub_earth_longitude = signed_longitude_deg(float(sub_earth_lon.degrees))
            sub_earth_latitude = float(sub_earth_lat.degrees)
            return LunarOrientationState(
                frame=LUNAR_FRAME_NAME,
                source="JPL DE421 + NAIF lunar PCK",
                quality=LunarOrientationQuality.PRECISE,
                body_to_enu_quaternion=rotation_matrix_to_quaternion(body_to_enu),
                libration_longitude_deg=sub_earth_longitude,
                libration_latitude_deg=sub_earth_latitude,
                sub_earth_longitude_deg=sub_earth_longitude,
                sub_earth_latitude_deg=sub_earth_latitude,
                sub_observer_longitude_deg=signed_longitude_deg(float(sub_observer_lon.degrees)),
                sub_observer_latitude_deg=float(sub_observer_lat.degrees),
                north_pole_position_angle_deg=north_pole_position_angle_deg(
                    observer_to_moon_icrf,
                    lunar_north_icrf,
                    celestial_north_icrf,
                ),
                bright_limb_position_angle_deg=bright_limb_position_angle,
                moon_to_sun_direction_enu=moon_to_sun_eun,
                compute_ms=(time.perf_counter() - started) * 1000.0,
            )
        except Exception as exc:
            # Keep the Step 8 Moon alive if Skyfield rejects only orientation.
            log.warning("Lunar orientation calculation failed: %s", exc)
            return self._unavailable_lunar_orientation(
                LunarOrientationQuality.UNAVAILABLE,
                started,
                str(exc),
                bright_limb_position_angle,
            )

    @staticmethod
    def _unavailable_lunar_orientation(
        quality: LunarOrientationQuality,
        started: float,
        detail: str | None,
        bright_limb_position_angle: float | None,
    ) -> LunarOrientationState:
        return LunarOrientationState(
            frame=LUNAR_FRAME_NAME,
            source="NAIF lunar orientation kernels",
            quality=quality,
            body_to_enu_quaternion=None,
            libration_longitude_deg=None,
            libration_latitude_deg=None,
            sub_earth_longitude_deg=None,
            sub_earth_latitude_deg=None,
            sub_observer_longitude_deg=None,
            sub_observer_latitude_deg=None,
            north_pole_position_angle_deg=None,
            bright_limb_position_angle_deg=bright_limb_position_angle,
            moon_to_sun_direction_enu=None,
            compute_ms=(time.perf_counter() - started) * 1000.0,
            detail=detail,
        )

    def _body_state(
        self,
        body_id: str,
        kind: BodyKind,
        target: Any,
        physical_radius_km: float,
        observer_at: Any,
        sun: Any,
        time_point: Any,
    ) -> ApparentBodyState:
        astrometric = observer_at.observe(target)
        apparent = astrometric.apparent()
        ra, dec, _ = apparent.radec(epoch="date")
        altitude, azimuth, distance = apparent.altaz()
        distance_km = float(distance.km)

        if kind is BodyKind.SUN:
            phase_angle = 0.0
            illumination = 1.0
            magnitude = sun_apparent_magnitude(distance_km / AU_KM)
        else:
            phase_angle = float(astrometric.phase_angle(sun).degrees)
            illumination = float(astrometric.fraction_illuminated(sun))
            if kind is BodyKind.MOON:
                moon_vector = target.at(time_point).position.au
                sun_vector = sun.at(time_point).position.au
                sun_distance_au = math.sqrt(
                    sum(float(sun_vector[index] - moon_vector[index]) ** 2 for index in range(3))
                )
                magnitude = moon_apparent_magnitude(
                    distance_km / AU_KM,
                    sun_distance_au,
                    phase_angle,
                )
            else:
                magnitude = float(self._planetary_magnitude(astrometric))

        altitude_deg = float(altitude.degrees)
        azimuth_deg = float(azimuth.degrees) % 360.0
        return ApparentBodyState(
            body_id=CelestialBodyId(body_id),
            kind=kind,
            equatorial=EquatorialCoordinate(float(ra.hours) * 15.0, float(dec.degrees)),
            horizontal=HorizontalCoordinate(altitude_deg, azimuth_deg),
            direction_enu=sun_direction_enu(altitude_deg, azimuth_deg),
            distance_km=distance_km,
            angular_radius_deg=angular_radius_deg(physical_radius_km, distance_km),
            illumination_fraction=max(0.0, min(1.0, illumination)),
            phase_angle_deg=max(0.0, min(180.0, phase_angle)),
            apparent_magnitude=magnitude,
            source="DE421",
            quality=EphemerisQuality.PRECISE,
        )

    @staticmethod
    def _fallback_snapshot(
        instant: datetime,
        observer: ScientificObserver,
        started: float,
        detail: str | None,
    ) -> SolarSystemSnapshot:
        return SolarSystemSnapshot(
            generation=0,
            timestamp_utc=instant,
            observer_generation=0,
            source="fallback",
            quality=EphemerisQuality.FALLBACK,
            sun=analytical_sun_state(instant, observer),
            moon=None,
            planets=(),
            compute_ms=(time.perf_counter() - started) * 1000.0,
            detail=detail,
        )


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        raise ValueError("Ephemeris instants must be timezone-aware")
    return value.astimezone(timezone.utc)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _matrix3(value: Any) -> tuple[
    tuple[float, float, float],
    tuple[float, float, float],
    tuple[float, float, float],
]:
    return tuple(
        tuple(float(value[row][column]) for column in range(3))
        for row in range(3)
    )  # type: ignore[return-value]


def _vector3(value: Any) -> tuple[float, float, float]:
    return float(value[0]), float(value[1]), float(value[2])
