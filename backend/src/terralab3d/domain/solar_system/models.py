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
    DWARF_PLANET = "dwarf_planet"
    NATURAL_SATELLITE = "natural_satellite"


class EphemerisQuality(str, Enum):
    PRECISE = "precise"
    FALLBACK = "fallback"


class LunarOrientationQuality(str, Enum):
    PRECISE = "precise"
    UNAVAILABLE = "unavailable"
    OUT_OF_RANGE = "out_of_range"


class PhysicalModelQuality(str, Enum):
    HIGH_PRECISION = "HIGH_PRECISION"
    IAU_MODEL = "IAU_MODEL"
    MEASURED = "MEASURED"
    ESTIMATED = "ESTIMATED"
    VISUAL_REFERENCE = "VISUAL_REFERENCE"
    UNAVAILABLE = "UNAVAILABLE"
    OUT_OF_RANGE = "OUT_OF_RANGE"


class CoverageStatus(str, Enum):
    IN_RANGE = "IN_RANGE"
    OUT_OF_RANGE = "OUT_OF_RANGE"
    NO_KERNEL = "NO_KERNEL"
    AMBIGUOUS_KERNEL = "AMBIGUOUS_KERNEL"
    ERROR = "ERROR"


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
class BodyOrientationState:
    """Body-fixed orientation with a separate equatorial/ring-plane basis.

    Both quaternions use renderer-neutral ``(x, y, z, w)`` and map body axes
    to canonical right-handed East/North/Up. The equatorial quaternion carries
    pole/equator orientation without prime-meridian spin.
    """

    frame: str
    source: str
    quality: PhysicalModelQuality
    body_to_enu_quaternion: tuple[float, float, float, float] | None
    equatorial_to_enu_quaternion: tuple[float, float, float, float] | None
    body_to_sun_direction_enu: tuple[float, float, float] | None
    north_pole_icrf: tuple[float, float, float] | None
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
            "equatorialToENUQuaternion": (
                list(self.equatorial_to_enu_quaternion)
                if self.equatorial_to_enu_quaternion is not None
                else None
            ),
            "bodyToSunDirectionENU": (
                list(self.body_to_sun_direction_enu)
                if self.body_to_sun_direction_enu is not None
                else None
            ),
            "northPoleICRF": (
                list(self.north_pole_icrf) if self.north_pole_icrf is not None else None
            ),
            "computeMs": self.compute_ms,
            "detail": self.detail,
        }


@dataclass(frozen=True, slots=True)
class RingPlaneDiagnostics:
    opening_geocentric_deg: float
    opening_topocentric_deg: float
    sun_elevation_deg: float

    def to_dict(self) -> dict[str, float]:
        return {
            "ringOpeningGeocentricDeg": self.opening_geocentric_deg,
            "ringOpeningTopocentricDeg": self.opening_topocentric_deg,
            "sunElevationAboveRingDeg": self.sun_elevation_deg,
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
    apparent_magnitude: float | None
    source: str
    quality: EphemerisQuality
    display_name: str | None = None
    bright_limb_position_angle_deg: float | None = None
    orientation: LunarOrientationState | BodyOrientationState | None = None
    naif_id: int | None = None
    parent_naif_id: int | None = None
    parent_body_id: str | None = None
    position_icrf_km: tuple[float, float, float] | None = None
    velocity_icrf_km_s: tuple[float, float, float] | None = None
    radii_km: tuple[float, float, float] | None = None
    mean_radius_km: float | None = None
    body_to_sun_direction_enu: tuple[float, float, float] | None = None
    ephemeris_kernel_id: str | None = None
    coverage_status: CoverageStatus = CoverageStatus.IN_RANGE
    orientation_quality: PhysicalModelQuality = PhysicalModelQuality.UNAVAILABLE
    shape_quality: PhysicalModelQuality = PhysicalModelQuality.UNAVAILABLE
    texture_quality: PhysicalModelQuality = PhysicalModelQuality.UNAVAILABLE
    geometric_elevation_deg: float | None = None
    horizon_elevation_deg: float = 0.0
    horizon_visible: bool = True
    refraction_applied: bool = False
    ring_diagnostics: RingPlaneDiagnostics | None = None

    def to_dict(self) -> dict[str, Any]:
        payload = {
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
        if self.display_name is not None:
            payload["displayName"] = self.display_name
        if self.naif_id is not None:
            payload.update(
                {
                    "naifId": self.naif_id,
                    "parentNaifId": self.parent_naif_id,
                    "parentBodyId": self.parent_body_id,
                    "positionICRFKm": (
                        list(self.position_icrf_km) if self.position_icrf_km else None
                    ),
                    "velocityICRFKmS": (
                        list(self.velocity_icrf_km_s) if self.velocity_icrf_km_s else None
                    ),
                    "radiiKm": list(self.radii_km) if self.radii_km else None,
                    "meanRadiusKm": self.mean_radius_km,
                    "bodyToSunDirectionENU": (
                        list(self.body_to_sun_direction_enu)
                        if self.body_to_sun_direction_enu is not None
                        else None
                    ),
                    "ephemerisKernelId": self.ephemeris_kernel_id,
                    "coverageStatus": self.coverage_status.value,
                    "orientationQuality": self.orientation_quality.value,
                    "shapeQuality": self.shape_quality.value,
                    "textureQuality": self.texture_quality.value,
                    "geometricElevationDeg": (
                        self.geometric_elevation_deg
                        if self.geometric_elevation_deg is not None
                        else self.horizontal.altitude_deg
                    ),
                    "horizonElevationDeg": self.horizon_elevation_deg,
                    "horizonVisible": self.horizon_visible,
                    "refractionApplied": self.refraction_applied,
                    "ringDiagnostics": (
                        self.ring_diagnostics.to_dict()
                        if self.ring_diagnostics is not None
                        else None
                    ),
                }
            )
        return payload


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
    satellites: tuple[ApparentBodyState, ...] = ()
    catalog_count: int = 0
    satellite_ephemeris_count: int = 0
    satellite_visible_count: int = 0
    kernel_generation: str | None = None
    kernel_status: str = "unavailable"
    icrf_to_enu_quaternion: tuple[float, float, float, float] | None = None
    detail: str | None = None

    def with_generation(self, generation: int, observer_generation: int) -> "SolarSystemSnapshot":
        return replace(
            self,
            generation=generation,
            observer_generation=observer_generation,
        )

    def to_dict(self) -> dict[str, Any]:
        timestamp = self.timestamp_utc.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
        payload = {
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
        if self.kernel_generation is not None or self.catalog_count:
            payload.update(
                {
                    "satellites": [satellite.to_dict() for satellite in self.satellites],
                    "catalogCount": self.catalog_count,
                    "satelliteEphemerisCount": self.satellite_ephemeris_count,
                    "satelliteVisibleCount": self.satellite_visible_count,
                    "kernelGeneration": self.kernel_generation,
                    "kernelStatus": self.kernel_status,
                    "icrfToENUQuaternion": (
                        list(self.icrf_to_enu_quaternion)
                        if self.icrf_to_enu_quaternion is not None
                        else None
                    ),
                }
            )
        return payload


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
    provider: str = "skyfield"
    aberration_policy: str = "apparent"
    reference_frame: str = "J2000/ICRF"
    kernel_generation: str | None = None
    kernel_manifest_path: str | None = None
    satellite_catalog_path: str | None = None
