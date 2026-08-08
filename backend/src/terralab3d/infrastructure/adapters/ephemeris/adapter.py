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
    moon_apparent_magnitude,
    sun_apparent_magnitude,
)
from terralab3d.domain.solar_system.models import (
    ApparentBodyState,
    BodyKind,
    EphemerisMetadata,
    EphemerisQuality,
    ScientificObserver,
    SolarSystemSnapshot,
)
from terralab3d.infrastructure.app_paths import resolve_data_root

log = logging.getLogger("terralab3d.ephemeris")

EPHEMERIS_PATH_ENV = "TERRALAB3D_EPHEMERIS_PATH"
KERNEL_NAME = "de421.bsp"
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
        self._range_jd: tuple[float, float] | None = None
        self._unavailable_detail: str | None = None
        self._metadata = EphemerisMetadata(None, None, None, None, None, None)
        self.open()

    @property
    def metadata(self) -> EphemerisMetadata:
        return self._metadata

    def open(self) -> None:
        if self._ephemeris is not None:
            return
        try:
            from skyfield.api import load, load_file, wgs84
            from skyfield.magnitudelib import planetary_magnitude

            kernel_path = self._resolve_kernel_path()
            if kernel_path is None:
                raise FileNotFoundError(
                    f"{KERNEL_NAME} not found in {EPHEMERIS_PATH_ENV}, the TerraLab data library, or skyfield-data"
                )
            self._timescale = load.timescale(builtin=True)
            self._ephemeris = load_file(str(kernel_path))
            self._wgs84 = wgs84
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
        self._planetary_magnitude = None

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
