"""Solar direction and twilight helpers with scientific ENU semantics."""

from __future__ import annotations

import math
from enum import Enum


class TwilightPhase(str, Enum):
    DAY = "day"
    CIVIL = "civil"
    NAUTICAL = "nautical"
    ASTRONOMICAL = "astronomical"
    NIGHT = "night"


def twilight_phase(sun_altitude_deg: float) -> TwilightPhase:
    if sun_altitude_deg >= 0.0:
        return TwilightPhase.DAY
    if sun_altitude_deg >= -6.0:
        return TwilightPhase.CIVIL
    if sun_altitude_deg >= -12.0:
        return TwilightPhase.NAUTICAL
    if sun_altitude_deg >= -18.0:
        return TwilightPhase.ASTRONOMICAL
    return TwilightPhase.NIGHT


def twilight_factor(sun_altitude_deg: float) -> float:
    """Continuous night factor: zero by day, one below astronomical twilight."""

    if sun_altitude_deg >= 0.0:
        return 0.0
    if sun_altitude_deg <= -18.0:
        return 1.0
    fraction = -sun_altitude_deg / 18.0
    return fraction * fraction * (3.0 - 2.0 * fraction)


def sun_direction_enu(altitude_deg: float, azimuth_deg: float) -> tuple[float, float, float]:
    """Convert north-clockwise Alt/Az to unit ENU ordered as East, Up, North."""

    altitude = math.radians(altitude_deg)
    azimuth = math.radians(azimuth_deg)
    cos_altitude = math.cos(altitude)
    east = cos_altitude * math.sin(azimuth)
    up = math.sin(altitude)
    north = cos_altitude * math.cos(azimuth)
    length = math.sqrt(east * east + up * up + north * north)
    return (east / length, up / length, north / length)
