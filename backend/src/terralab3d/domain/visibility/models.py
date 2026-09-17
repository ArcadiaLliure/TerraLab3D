"""Renderer-neutral models for apparent trajectories and local visibility."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from terralab3d.domain.geometry import CartesianDirection


class ObservableFamily(StrEnum):
    SOLAR_SYSTEM = "solar_system"
    SATELLITE = "satellite"
    STAR = "star"
    DEEP_SKY = "deep_sky"
    COORDINATE = "coordinate"
    CONSTELLATION = "constellation"


class TrajectoryResolution(StrEnum):
    AUTOMATIC = "automatic"
    DETAILED = "detailed"


class TrajectoryVisibilityState(StrEnum):
    VISIBLE = "visible"
    TERRAIN_OCCLUDED = "terrain_occluded"
    BELOW_ASTRONOMICAL_HORIZON = "below_astronomical_horizon"
    INSUFFICIENT_DATA = "insufficient_data"


class HorizonProvenance(StrEnum):
    REAL = "real"
    FALLBACK_ASTRONOMICAL = "fallback_astronomical"
    INSUFFICIENT = "insufficient"


class TrajectoryEventKind(StrEnum):
    RISE = "rise"
    SET = "set"
    TANGENT = "tangent"


class VisibilityIntervalClassification(StrEnum):
    VISIBLE_THROUGHOUT = "visible_throughout"
    NEVER_VISIBLE = "never_visible"
    MIXED = "mixed"
    INSUFFICIENT_DATA = "insufficient_data"


@dataclass(frozen=True, slots=True)
class ObservableObject:
    """Identity and scientific inputs for one observable object.

    Solar-system bodies and satellites use ``body_id``. Fixed ICRS targets,
    including constellation centres from Pas 23, use right ascension and
    declination.
    """

    object_id: str
    family: ObservableFamily
    display_name: str
    body_id: str | None = None
    right_ascension_deg: float | None = None
    declination_deg: float | None = None
    frame: str = "ICRS"

    @property
    def has_apparent_position(self) -> bool:
        if self.family in (ObservableFamily.SOLAR_SYSTEM, ObservableFamily.SATELLITE):
            return bool(self.body_id)
        return self.right_ascension_deg is not None and self.declination_deg is not None


@dataclass(frozen=True, slots=True)
class ApparentPosition:
    instant_utc: datetime
    direction_enu: CartesianDirection
    azimuth_deg: float
    altitude_deg: float
    valid: bool
    quality: str


@dataclass(frozen=True, slots=True)
class HorizonReading:
    elevation_deg: float
    provenance: HorizonProvenance


@dataclass(frozen=True, slots=True)
class TrajectorySample:
    instant_utc: datetime
    offset_seconds: float
    apparent: ApparentPosition
    horizon_elevation_deg: float
    horizon_provenance: HorizonProvenance
    visibility: TrajectoryVisibilityState
    margin_deg: float


@dataclass(frozen=True, slots=True)
class TrajectorySegment:
    start_index: int
    end_index: int
    visibility: TrajectoryVisibilityState
    horizon_provenance: HorizonProvenance


@dataclass(frozen=True, slots=True)
class TrajectoryEvent:
    kind: TrajectoryEventKind
    instant_utc: datetime
    direction_enu: CartesianDirection
    azimuth_deg: float
    altitude_deg: float
    horizon_elevation_deg: float
    horizon_provenance: HorizonProvenance


@dataclass(frozen=True, slots=True)
class VisibleTrajectory:
    observable: ObservableObject
    observer_latitude_deg: float
    observer_longitude_deg: float
    observer_elevation_m: float
    start_utc: datetime
    end_utc: datetime
    samples: tuple[TrajectorySample, ...]
    segments: tuple[TrajectorySegment, ...]
    events: tuple[TrajectoryEvent, ...]
    interval_classification: VisibilityIntervalClassification
    astronomically_circumpolar: bool
    generation: int
    observer_generation: int
    kernel_generation: str
    horizon_version: int
    horizon_quality: str
    resolution: TrajectoryResolution
    temporal_tolerance_seconds: float
    angular_tolerance_deg: float
    compute_ms: float
