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


@dataclass(frozen=True, slots=True)
class ScientificObserver:
    """Observer inputs that affect ephemerides; camera motion is excluded."""

    latitude_deg: float
    longitude_deg: float
    elevation_m: float


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
