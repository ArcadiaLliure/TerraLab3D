"""Renderer-neutral contracts for eclipses, occultations and apparent paths.

Angles exposed by this package are degrees, distances are kilometres and every
instant is an aware UTC ``datetime``.  Directions use J2000/ICRF internally;
the established TerraLab3D wire convention remains East/Up/North at the bridge.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime, timezone
from enum import Enum
from typing import Any

Vector3 = tuple[float, float, float]
Quaternion = tuple[float, float, float, float]


class EclipseKind(str, Enum):
    SOLAR = "solar"
    LUNAR = "lunar"
    OCCULTATION = "occultation"


class GeometryQuality(str, Enum):
    SCIENTIFIC = "scientific"
    FALLBACK = "fallback"
    UNAVAILABLE = "unavailable"


class SolarEclipseClassification(str, Enum):
    NONE = "none"
    PARTIAL = "partial"
    ANNULAR = "annular"
    TOTAL = "total"


class LunarEclipseClassification(str, Enum):
    NONE = "none"
    PENUMBRAL = "penumbral"
    PARTIAL = "partial"
    TOTAL = "total"


class OccultationClassification(str, Enum):
    NONE = "none"
    PARTIAL = "partial"
    TOTAL = "total"
    TRANSIT = "transit"


class SolarAppearancePhase(str, Enum):
    PARTIAL = "partial"
    BAILY_INGRESS = "baily_ingress"
    DIAMOND_INGRESS = "diamond_ingress"
    TOTALITY = "totality"
    DIAMOND_EGRESS = "diamond_egress"
    BAILY_EGRESS = "baily_egress"


@dataclass(frozen=True, slots=True)
class ApparentEventBody:
    body_id: str
    naif_id: int
    direction_icrf: Vector3
    direction_enu: Vector3
    distance_km: float
    angular_radius_deg: float
    altitude_deg: float
    physical_radius_km: float
    body_to_icrf_quaternion: Quaternion | None = None
    north_pole_position_angle_deg: float | None = None


@dataclass(frozen=True, slots=True)
class AstronomicalEventEphemeris:
    timestamp_utc: datetime
    observer_latitude_deg: float
    observer_longitude_deg: float
    observer_elevation_m: float
    kernel_generation: str
    source: str
    quality: GeometryQuality
    bodies: tuple[ApparentEventBody, ...]
    earth_to_sun_icrf_km: Vector3 | None = None
    earth_to_moon_icrf_km: Vector3 | None = None
    observer_position_icrf_km: Vector3 | None = None

    def body(self, body_id: str) -> ApparentEventBody | None:
        return next((body for body in self.bodies if body.body_id == body_id), None)


@dataclass(frozen=True, slots=True)
class DiscOverlap:
    overlap_area_square_deg: float
    foreground_area_fraction: float
    background_area_fraction: float


@dataclass(frozen=True, slots=True)
class SolarEclipseState:
    classification: SolarEclipseClassification
    sun_angular_radius_deg: float
    moon_angular_radius_deg: float
    moon_to_sun_radius_ratio: float
    center_separation_deg: float
    moon_position_angle_deg: float
    eclipse_magnitude: float
    obscuration: float
    solar_disc_transmission: float
    source_altitude_deg: float
    locally_visible: bool
    separation_rate_deg_s: float | None
    geometry_quality: GeometryQuality

    def to_dict(self) -> dict[str, Any]:
        return {
            "classification": self.classification.value,
            "sunAngularRadius": self.sun_angular_radius_deg,
            "moonAngularRadius": self.moon_angular_radius_deg,
            "moonToSunRadiusRatio": self.moon_to_sun_radius_ratio,
            "centerSeparation": self.center_separation_deg,
            "moonPositionAngleDeg": self.moon_position_angle_deg,
            "eclipseMagnitude": self.eclipse_magnitude,
            "obscuration": self.obscuration,
            "solarDiscTransmission": self.solar_disc_transmission,
            "sourceAltitudeDeg": self.source_altitude_deg,
            "locallyVisible": self.locally_visible,
            "separationRateDegS": self.separation_rate_deg_s,
            "geometryQuality": self.geometry_quality.value,
        }


@dataclass(frozen=True, slots=True)
class LunarEclipseState:
    classification: LunarEclipseClassification
    penumbra_radius_km: float
    umbra_radius_km: float
    moon_radius_km: float
    shadow_axis_offset_km: float
    penumbral_magnitude: float
    umbral_magnitude: float
    penumbra_radius_moon_radii: float
    umbra_radius_moon_radii: float
    shadow_offset_moon_radii: float
    shadow_offset_position_angle_deg: float
    mean_lunar_light_transmission: float
    source_altitude_deg: float
    locally_visible: bool
    atmosphere_enlargement_factor: float
    geometry_quality: GeometryQuality

    def to_dict(self) -> dict[str, Any]:
        return {
            "classification": self.classification.value,
            "penumbraRadiusKm": self.penumbra_radius_km,
            "umbraRadiusKm": self.umbra_radius_km,
            "moonRadiusKm": self.moon_radius_km,
            "shadowAxisOffsetKm": self.shadow_axis_offset_km,
            "penumbralMagnitude": self.penumbral_magnitude,
            "umbralMagnitude": self.umbral_magnitude,
            "penumbraRadiusMoonRadii": self.penumbra_radius_moon_radii,
            "umbraRadiusMoonRadii": self.umbra_radius_moon_radii,
            "shadowOffsetMoonRadii": self.shadow_offset_moon_radii,
            "shadowOffsetPositionAngleDeg": self.shadow_offset_position_angle_deg,
            "meanLunarLightTransmission": self.mean_lunar_light_transmission,
            "sourceAltitudeDeg": self.source_altitude_deg,
            "locallyVisible": self.locally_visible,
            "atmosphereEnlargementFactor": self.atmosphere_enlargement_factor,
            "geometryQuality": self.geometry_quality.value,
        }


@dataclass(frozen=True, slots=True)
class OccultationState:
    foreground: str
    background: str
    classification: OccultationClassification
    separation_deg: float
    foreground_radius_deg: float
    background_radius_deg: float
    foreground_distance_km: float
    background_distance_km: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "foreground": self.foreground,
            "background": self.background,
            "classification": self.classification.value,
            "separationDeg": self.separation_deg,
            "foregroundRadiusDeg": self.foreground_radius_deg,
            "backgroundRadiusDeg": self.background_radius_deg,
            "foregroundDistanceKm": self.foreground_distance_km,
            "backgroundDistanceKm": self.background_distance_km,
        }


@dataclass(frozen=True, slots=True)
class AngularSeparationMeasurement:
    body_a: str
    body_b: str
    timestamp_utc: datetime
    separation_deg: float
    limb_separation_deg: float
    quality: GeometryQuality

    def to_dict(self) -> dict[str, Any]:
        return {
            "bodyA": self.body_a,
            "bodyB": self.body_b,
            "timestampUtc": _utc_iso(self.timestamp_utc),
            "separationDeg": self.separation_deg,
            "limbSeparationDeg": self.limb_separation_deg,
            "quality": self.quality.value,
        }


@dataclass(frozen=True, slots=True)
class ApparentPairResult:
    request_id: str
    measurement: AngularSeparationMeasurement
    occultation: OccultationState
    kernel_generation: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "requestId": self.request_id,
            **self.measurement.to_dict(),
            "occultation": self.occultation.to_dict(),
            "kernelGeneration": self.kernel_generation,
        }


@dataclass(frozen=True, slots=True)
class EclipseContact:
    name: str
    instant_utc: datetime
    locally_visible: bool
    source_altitude_deg: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "instantUtc": _utc_iso(self.instant_utc),
            "locallyVisible": self.locally_visible,
            "sourceAltitudeDeg": self.source_altitude_deg,
        }


@dataclass(frozen=True, slots=True)
class AstronomicalEventSearchResult:
    request_id: str
    event_type: EclipseKind
    classification: str
    interval_start_utc: datetime
    interval_end_utc: datetime
    greatest_utc: datetime | None
    contacts: tuple[EclipseContact, ...]
    event_exists: bool
    locally_visible: bool
    maximum_magnitude: float
    maximum_obscuration: float | None
    observer_generation: int
    kernel_generation: str
    quality: GeometryQuality
    ephemeris_query_count: int
    duration_ms: float
    temporal_tolerance_seconds: float
    angular_tolerance_deg: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "requestId": self.request_id,
            "eventType": self.event_type.value,
            "classification": self.classification,
            "intervalStartUtc": _utc_iso(self.interval_start_utc),
            "intervalEndUtc": _utc_iso(self.interval_end_utc),
            "greatestUtc": _utc_iso(self.greatest_utc) if self.greatest_utc else None,
            "contacts": [contact.to_dict() for contact in self.contacts],
            "eventExists": self.event_exists,
            "locallyVisible": self.locally_visible,
            "maximumMagnitude": self.maximum_magnitude,
            "maximumObscuration": self.maximum_obscuration,
            "observerGeneration": self.observer_generation,
            "kernelGeneration": self.kernel_generation,
            "quality": self.quality.value,
            "ephemerisQueryCount": self.ephemeris_query_count,
            "durationMs": self.duration_ms,
            "temporalToleranceSeconds": self.temporal_tolerance_seconds,
            "angularToleranceDeg": self.angular_tolerance_deg,
        }


@dataclass(frozen=True, slots=True)
class LunarLimbSample:
    position_angle_deg: float
    elevation_km: float
    angular_radius_deg: float


@dataclass(frozen=True, slots=True)
class LunarLimbProfile:
    samples: tuple[LunarLimbSample, ...]
    dataset_id: str
    asset_sha256: str | None
    quality: str


@dataclass(frozen=True, slots=True)
class BailyBead:
    lunar_position_angle_deg: float
    angular_width_deg: float
    exposed_photosphere_area_square_deg: float
    brightness: float

    def to_dict(self) -> dict[str, float]:
        return {
            "lunarPositionAngle": self.lunar_position_angle_deg,
            "angularWidth": self.angular_width_deg,
            "exposedPhotosphereArea": self.exposed_photosphere_area_square_deg,
            "brightness": self.brightness,
        }


@dataclass(frozen=True, slots=True)
class CoronaStructure:
    kind: str
    position_angle_deg: float
    angular_width_deg: float
    radial_extent_solar_radii: float
    brightness: float

    def to_dict(self) -> dict[str, float | str]:
        return {
            "kind": self.kind,
            "positionAngleDeg": self.position_angle_deg,
            "angularWidthDeg": self.angular_width_deg,
            "radialExtentSolarRadii": self.radial_extent_solar_radii,
            "brightness": self.brightness,
        }


@dataclass(frozen=True, slots=True)
class SolarCoronaState:
    mode: str
    quality: str
    solar_north_position_angle_deg: float
    visibility: float
    structures: tuple[CoronaStructure, ...]
    asset_timestamp_utc: str | None = None
    asset_sha256: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "mode": self.mode,
            "quality": self.quality,
            "solarNorthPositionAngleDeg": self.solar_north_position_angle_deg,
            "visibility": self.visibility,
            "structures": [item.to_dict() for item in self.structures],
            "assetTimestampUtc": self.asset_timestamp_utc,
            "assetSha256": self.asset_sha256,
        }


@dataclass(frozen=True, slots=True)
class TerrainCorrectedLimbState:
    dataset_id: str
    asset_sha256: str | None
    radius_scale_samples: tuple[float, ...]
    maximum_radius_scale: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "datasetId": self.dataset_id,
            "assetSha256": self.asset_sha256,
            "sampleCount": len(self.radius_scale_samples),
            "radiusScaleSamples": [
                round(value, 8) for value in self.radius_scale_samples
            ],
            "maximumRadiusScale": self.maximum_radius_scale,
        }


@dataclass(frozen=True, slots=True)
class EclipseSceneAppearance:
    quality: str
    strength: float
    saturation: float
    color_temperature_shift: float
    contrast: float
    midtone_exposure: float
    direct_to_diffuse_ratio: float

    def to_dict(self) -> dict[str, float | str]:
        return {
            "quality": self.quality,
            "strength": self.strength,
            "saturation": self.saturation,
            "colorTemperatureShift": self.color_temperature_shift,
            "contrast": self.contrast,
            "midtoneExposure": self.midtone_exposure,
            "directToDiffuseRatio": self.direct_to_diffuse_ratio,
        }


@dataclass(frozen=True, slots=True)
class SolarTotalityAppearance:
    phase: SolarAppearancePhase
    limb_quality: str
    beads: tuple[BailyBead, ...]
    dominant_photosphere_region_count: int
    exposed_photosphere_area_square_deg: float
    corona: SolarCoronaState
    chromosphere_visibility: float
    prominence_quality: str
    terrain_corrected_limb: TerrainCorrectedLimbState | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "phase": self.phase.value,
            "limbQuality": self.limb_quality,
            "beads": [bead.to_dict() for bead in self.beads],
            "dominantPhotosphereRegionCount": self.dominant_photosphere_region_count,
            "exposedPhotosphereArea": self.exposed_photosphere_area_square_deg,
            "corona": self.corona.to_dict(),
            "chromosphereVisibility": self.chromosphere_visibility,
            "prominenceQuality": self.prominence_quality,
            "terrainCorrectedLimb": (
                self.terrain_corrected_limb.to_dict()
                if self.terrain_corrected_limb is not None
                else None
            ),
        }


@dataclass(frozen=True, slots=True)
class AstronomicalEventSnapshot:
    generation: int
    timestamp_utc: datetime
    observer_generation: int
    source_solar_system_generation: int
    kernel_generation: str
    solar: SolarEclipseState
    lunar: LunarEclipseState
    sky_eclipse_dimming_factor: float
    scene_appearance: EclipseSceneAppearance
    totality_appearance: SolarTotalityAppearance
    compute_ms: float

    def with_generations(
        self,
        generation: int,
        observer_generation: int,
        source_solar_system_generation: int,
    ) -> "AstronomicalEventSnapshot":
        return replace(
            self,
            generation=generation,
            observer_generation=observer_generation,
            source_solar_system_generation=source_solar_system_generation,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "generation": self.generation,
            "timestampUtc": _utc_iso(self.timestamp_utc),
            "observerGeneration": self.observer_generation,
            "sourceSolarSystemGeneration": self.source_solar_system_generation,
            "kernelGeneration": self.kernel_generation,
            "solar": self.solar.to_dict(),
            "lunar": self.lunar.to_dict(),
            "skyEclipseDimmingFactor": self.sky_eclipse_dimming_factor,
            "sceneAppearance": self.scene_appearance.to_dict(),
            "totalityAppearance": self.totality_appearance.to_dict(),
            "geometryQuality": self.solar.geometry_quality.value,
            "limbQuality": self.totality_appearance.limb_quality,
            "coronaQuality": self.totality_appearance.corona.quality,
            "appearanceQuality": self.scene_appearance.quality,
            "computeMs": self.compute_ms,
        }


@dataclass(frozen=True, slots=True)
class ApparentTrajectory:
    body_id: str
    observer_latitude_deg: float
    observer_longitude_deg: float
    observer_elevation_m: float
    start_utc: datetime
    end_utc: datetime
    directions_enu: tuple[Vector3, ...]
    time_offsets_seconds: tuple[float, ...]
    validity: tuple[bool, ...]
    generation: int
    observer_generation: int
    kernel_generation: str
    quality: GeometryQuality


def _utc_iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
