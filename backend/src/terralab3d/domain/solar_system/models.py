"""Renderer-neutral scientific state for the apparent Solar System sky."""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from terralab3d.domain.geometry import EquatorialCoordinate, HorizontalCoordinate
from terralab3d.domain.identifiers import CelestialBodyId


class BodyKind(str, Enum):
    SUN = "sun"
    MOON = "moon"
    PLANET = "planet"


class EphemerisQuality(str, Enum):
    PRECISE = "precise"
    FALLBACK = "fallback"


class LunarOrientationQuality(str, Enum):
    PRECISE = "precise"
    UNAVAILABLE = "unavailable"
    OUT_OF_RANGE = "out_of_range"


@dataclass(frozen=True, slots=True)
class ScientificObserver:
    """Observer inputs that affect ephemerides; camera motion is excluded."""

    latitude_deg: float
    longitude_deg: float
    elevation_m: float


@dataclass(frozen=True, slots=True)
class LunarOrientationState:
    """Complete body-fixed Moon orientation expressed in the observer ENU frame.

    ``body_to_enu_quaternion`` uses the renderer-neutral ``(x, y, z, w)``
    convention and maps lunar body axes into right-handed East/North/Up.
    Direction tuples retain TerraLab3D's established East/Up/North wire order.
    Longitudes are east-positive in ``[-180, 180)``.
    """

    frame: str
    source: str
    quality: LunarOrientationQuality
    body_to_enu_quaternion: tuple[float, float, float, float] | None
    libration_longitude_deg: float | None
    libration_latitude_deg: float | None
    sub_earth_longitude_deg: float | None
    sub_earth_latitude_deg: float | None
    sub_observer_longitude_deg: float | None
    sub_observer_latitude_deg: float | None
    north_pole_position_angle_deg: float | None
    bright_limb_position_angle_deg: float | None
    moon_to_sun_direction_enu: tuple[float, float, float] | None
    compute_ms: float
    detail: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "frame": self.frame,
            "source": self.source,
            "quality": self.quality.value,
            "bodyToENUQuaternion": (
                list(self.body_to_enu_quaternion)
                if self.body_to_enu_quaternion is not None
                else None
            ),
            "librationLongitudeDeg": self.libration_longitude_deg,
            "librationLatitudeDeg": self.libration_latitude_deg,
            "subEarthLongitudeDeg": self.sub_earth_longitude_deg,
            "subEarthLatitudeDeg": self.sub_earth_latitude_deg,
            "subObserverLongitudeDeg": self.sub_observer_longitude_deg,
            "subObserverLatitudeDeg": self.sub_observer_latitude_deg,
            "northPolePositionAngleDeg": self.north_pole_position_angle_deg,
            "brightLimbPositionAngleDeg": self.bright_limb_position_angle_deg,
            "moonToSunDirectionENU": (
                list(self.moon_to_sun_direction_enu)
                if self.moon_to_sun_direction_enu is not None
                else None
            ),
            "computeMs": self.compute_ms,
            "detail": self.detail,
        }


@dataclass(frozen=True, slots=True)
class ApparentBodyState:
    body_id: CelestialBodyId
    kind: BodyKind
    equatorial: EquatorialCoordinate
    horizontal: HorizontalCoordinate
    direction_enu: tuple[float, float, float]
    distance_km: float
    angular_radius_deg: float
    illumination_fraction: float
    phase_angle_deg: float
    apparent_magnitude: float
    source: str
    quality: EphemerisQuality
    bright_limb_position_angle_deg: float | None = None
    orientation: LunarOrientationState | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": str(self.body_id),
            "type": self.kind.value,
            "rightAscensionDeg": self.equatorial.right_ascension_deg,
            "declinationDeg": self.equatorial.declination_deg,
            "altitudeDeg": self.horizontal.altitude_deg,
            "azimuthDeg": self.horizontal.azimuth_deg,
            "directionENU": list(self.direction_enu),
            "distanceKm": self.distance_km,
            "angularRadiusDeg": self.angular_radius_deg,
            "angularDiameterDeg": self.angular_radius_deg * 2.0,
            "illuminationFraction": self.illumination_fraction,
            "phaseAngleDeg": self.phase_angle_deg,
            "apparentMagnitude": self.apparent_magnitude,
            "brightLimbPositionAngleDeg": self.bright_limb_position_angle_deg,
            "orientation": self.orientation.to_dict() if self.orientation is not None else None,
            "source": self.source,
            "quality": self.quality.value,
        }


@dataclass(frozen=True, slots=True)
class SolarSystemSnapshot:
    generation: int
    timestamp_utc: datetime
    observer_generation: int
    source: str
    quality: EphemerisQuality
    sun: ApparentBodyState
    moon: ApparentBodyState | None
    planets: tuple[ApparentBodyState, ...]
    compute_ms: float
    detail: str | None = None

    def with_generation(self, generation: int, observer_generation: int) -> "SolarSystemSnapshot":
        return replace(
            self,
            generation=generation,
            observer_generation=observer_generation,
        )

    def to_dict(self) -> dict[str, Any]:
        timestamp = self.timestamp_utc.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
        return {
            "generation": self.generation,
            "timestampUtc": timestamp,
            "observerGeneration": self.observer_generation,
            "source": self.source,
            "quality": self.quality.value,
            "detail": self.detail,
            "computeMs": self.compute_ms,
            "sun": self.sun.to_dict(),
            "moon": self.moon.to_dict() if self.moon is not None else None,
            "planets": [planet.to_dict() for planet in self.planets],
        }


@dataclass(frozen=True, slots=True)
class EphemerisMetadata:
    kernel_name: str | None
    kernel_path: str | None
    kernel_sha256: str | None
    range_start_utc: str | None
    range_end_utc: str | None
    skyfield_version: str | None
    lunar_orientation_frame: str | None = None
    lunar_frame_kernel_sha256: str | None = None
    lunar_orientation_kernel_sha256: str | None = None
    lunar_orientation_range_start_utc: str | None = None
    lunar_orientation_range_end_utc: str | None = None
