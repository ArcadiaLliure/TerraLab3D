"""Pure astronomical helpers shared by ephemeris adapters and tests."""

from __future__ import annotations

import math
from datetime import datetime, timezone

from terralab3d.domain.geometry import EquatorialCoordinate, HorizontalCoordinate
from terralab3d.domain.identifiers import CelestialBodyId
from terralab3d.domain.sky_background.solar_direction import sun_direction_enu

from .models import ApparentBodyState, BodyKind, EphemerisQuality, ScientificObserver

AU_KM = 149_597_870.7
SUN_RADIUS_KM = 695_700.0


def angular_radius_deg(physical_radius_km: float, distance_km: float) -> float:
    if physical_radius_km <= 0.0 or distance_km <= physical_radius_km:
        raise ValueError("Physical radius and distance do not define a visible sphere")
    return math.degrees(math.asin(physical_radius_km / distance_km))


def illuminated_fraction(phase_angle_deg: float) -> float:
    phase = math.radians(max(0.0, min(180.0, phase_angle_deg)))
    return (1.0 + math.cos(phase)) * 0.5


def bright_limb_position_angle_deg(
    moon_ra_deg: float,
    moon_dec_deg: float,
    sun_ra_deg: float,
    sun_dec_deg: float,
) -> float:
    """Position angle eastward from celestial north, in [0, 360)."""

    moon_ra = math.radians(moon_ra_deg)
    moon_dec = math.radians(moon_dec_deg)
    sun_ra = math.radians(sun_ra_deg)
    sun_dec = math.radians(sun_dec_deg)
    delta_ra = sun_ra - moon_ra
    y = math.cos(sun_dec) * math.sin(delta_ra)
    x = (
        math.sin(sun_dec) * math.cos(moon_dec)
        - math.cos(sun_dec) * math.sin(moon_dec) * math.cos(delta_ra)
    )
    return math.degrees(math.atan2(y, x)) % 360.0


def sun_apparent_magnitude(distance_au: float) -> float:
    return -26.74 + 5.0 * math.log10(max(distance_au, 1e-12))


def moon_apparent_magnitude(
    observer_distance_au: float,
    sun_distance_au: float,
    phase_angle_deg: float,
) -> float:
    """Meeus-style visual magnitude for an unresolved lunar disc."""

    phase = abs(phase_angle_deg)
    return (
        0.23
        + 5.0 * math.log10(max(observer_distance_au * sun_distance_au, 1e-12))
        + 0.026 * phase
        + 4.0e-9 * phase**4
    )


def analytical_sun_state(
    utc: datetime,
    observer: ScientificObserver,
) -> ApparentBodyState:
    """Validated no-refraction solar fallback based on standard Meeus terms."""

    instant = _as_utc(utc)
    jd = _julian_day(instant)
    centuries = (jd - 2_451_545.0) / 36_525.0

    mean_longitude = (280.46646 + 36_000.76983 * centuries + 0.0003032 * centuries**2) % 360.0
    mean_anomaly = math.radians(
        (357.52911 + 35_999.05029 * centuries - 0.0001537 * centuries**2) % 360.0
    )
    eccentricity = 0.016708634 - 0.000042037 * centuries - 0.0000001267 * centuries**2
    equation_of_center = (
        (1.914602 - 0.004817 * centuries - 0.000014 * centuries**2) * math.sin(mean_anomaly)
        + (0.019993 - 0.000101 * centuries) * math.sin(2.0 * mean_anomaly)
        + 0.000289 * math.sin(3.0 * mean_anomaly)
    )
    true_longitude = mean_longitude + equation_of_center
    true_anomaly = mean_anomaly + math.radians(equation_of_center)
    omega = math.radians(125.04 - 1934.136 * centuries)
    apparent_longitude = math.radians(true_longitude - 0.00569 - 0.00478 * math.sin(omega))
    mean_obliquity = 23.0 + 26.0 / 60.0 + (
        21.448 - 46.815 * centuries - 0.00059 * centuries**2 + 0.001813 * centuries**3
    ) / 3600.0
    obliquity = math.radians(mean_obliquity + 0.00256 * math.cos(omega))

    ra_deg = math.degrees(math.atan2(math.cos(obliquity) * math.sin(apparent_longitude), math.cos(apparent_longitude))) % 360.0
    dec_deg = math.degrees(math.asin(math.sin(obliquity) * math.sin(apparent_longitude)))
    distance_au = (1.000001018 * (1.0 - eccentricity**2)) / (
        1.0 + eccentricity * math.cos(true_anomaly)
    )

    lst_deg = _local_sidereal_deg(jd, observer.longitude_deg)
    hour_angle = math.radians((lst_deg - ra_deg) % 360.0)
    latitude = math.radians(observer.latitude_deg)
    declination = math.radians(dec_deg)
    sin_altitude = (
        math.sin(latitude) * math.sin(declination)
        + math.cos(latitude) * math.cos(declination) * math.cos(hour_angle)
    )
    altitude = math.asin(max(-1.0, min(1.0, sin_altitude)))
    east = -math.cos(declination) * math.sin(hour_angle)
    north = (
        math.sin(declination) * math.cos(latitude)
        - math.cos(declination) * math.sin(latitude) * math.cos(hour_angle)
    )
    azimuth_deg = math.degrees(math.atan2(east, north)) % 360.0
    altitude_deg = math.degrees(altitude)
    distance_km = distance_au * AU_KM

    return ApparentBodyState(
        body_id=CelestialBodyId("sun"),
        kind=BodyKind.SUN,
        equatorial=EquatorialCoordinate(ra_deg, dec_deg),
        horizontal=HorizontalCoordinate(altitude_deg, azimuth_deg),
        direction_enu=sun_direction_enu(altitude_deg, azimuth_deg),
        distance_km=distance_km,
        angular_radius_deg=angular_radius_deg(SUN_RADIUS_KM, distance_km),
        illumination_fraction=1.0,
        phase_angle_deg=0.0,
        apparent_magnitude=sun_apparent_magnitude(distance_au),
        source="analytical-solar-fallback",
        quality=EphemerisQuality.FALLBACK,
    )


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        raise ValueError("Ephemeris instants must be timezone-aware UTC datetimes")
    return value.astimezone(timezone.utc)


def _julian_day(utc: datetime) -> float:
    return utc.timestamp() / 86_400.0 + 2_440_587.5


def _local_sidereal_deg(julian_day: float, longitude_deg: float) -> float:
    centuries = (julian_day - 2_451_545.0) / 36_525.0
    gmst = (
        280.46061837
        + 360.98564736629 * (julian_day - 2_451_545.0)
        + 0.000387933 * centuries**2
        - centuries**3 / 38_710_000.0
    )
    return (gmst + longitude_deg) % 360.0
