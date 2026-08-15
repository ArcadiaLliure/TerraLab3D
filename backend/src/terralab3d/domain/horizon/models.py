"""Scientific models for the versioned 360-degree terrain horizon."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

import numpy as np
from numpy.typing import NDArray

from terralab3d.domain.identifiers import ResourceId

EARTH_RADIUS_M = 6_371_000.0
OBSERVER_EYE_HEIGHT_M = 1.7
HORIZON_KERNEL_VERSION = "horizon-numpy-aeqd-v2"


class HorizonQuality(StrEnum):
    REAL = "REAL"
    PARTIAL_DEM = "PARTIAL_DEM"
    FLAT_FALLBACK = "FLAT_FALLBACK"
    UNAVAILABLE = "UNAVAILABLE"
    ERROR = "ERROR"


class HorizonRangeMode(StrEnum):
    AUTO = "auto"
    MANUAL = "manual"


@dataclass(frozen=True, slots=True)
class HorizonProfileSettings:
    range_mode: HorizonRangeMode = HorizonRangeMode.MANUAL
    visible_radius_km: float = 150.0
    angular_step_deg: float = 0.25
    atmospheric_refraction_enabled: bool = True
    effective_earth_radius_factor: float = 7.0 / 6.0
    max_samples_per_ray: int = 4096
    memory_budget_bytes: int = 256 * 1024 * 1024

    def validated(self) -> "HorizonProfileSettings":
        mode = HorizonRangeMode(self.range_mode)
        radius = float(self.visible_radius_km)
        step = float(self.angular_step_deg)
        factor = float(self.effective_earth_radius_factor)
        samples = int(self.max_samples_per_ray)
        budget = int(self.memory_budget_bytes)
        if not 1.0 <= radius <= 530.0:
            raise ValueError("Visible radius must be between 1 and 530 km")
        if not 0.005 <= step <= 5.0:
            raise ValueError("Angular step must be between 0.005 and 5 degrees")
        if factor < 1.0:
            raise ValueError("Effective Earth radius factor must be at least 1")
        if samples < 16:
            raise ValueError("max_samples_per_ray must be at least 16")
        if budget < 1_048_576:
            raise ValueError("memory_budget_bytes must be at least 1 MiB")
        return HorizonProfileSettings(
            range_mode=mode,
            visible_radius_km=radius,
            angular_step_deg=step,
            atmospheric_refraction_enabled=bool(self.atmospheric_refraction_enabled),
            effective_earth_radius_factor=factor,
            max_samples_per_ray=samples,
            memory_budget_bytes=budget,
        )


@dataclass(frozen=True, slots=True)
class HorizonRequest:
    request_id: str
    generation: int
    observer_generation: int
    settings_generation: int
    latitude_deg: float
    longitude_deg: float
    terrain_elevation_m: float | None
    height_offset_m: float
    settings: HorizonProfileSettings
    force_recalculate: bool = False
    # A flight camera may need an updated scientific horizon while retaining
    # the already resident world mesh.  Rebuilding a 530 km mesh per flight
    # stop would be both visually wrong (different local origin) and wasteful.
    build_terrain_mesh: bool = True

    @property
    def observer_eye_elevation_m(self) -> float | None:
        if self.terrain_elevation_m is None:
            return None
        return self.terrain_elevation_m + self.height_offset_m + OBSERVER_EYE_HEIGHT_M


@dataclass(frozen=True, slots=True)
class HorizonReduction:
    horizon_elevation_deg: NDArray[np.float32]
    occluder_distance_m: NDArray[np.float32]
    occluder_height_m: NDArray[np.float32]
    valid_mask: NDArray[np.bool_]


@dataclass(frozen=True, slots=True)
class HorizonProfile:
    resource_id: ResourceId
    version: int
    content_key: str
    source_ids: tuple[str, ...]
    source_fingerprint: str
    observer_generation: int
    latitude_deg: float
    longitude_deg: float
    terrain_elevation_m: float | None
    eye_elevation_m: float | None
    visible_radius_m: float
    azimuth_start_deg: float
    angular_step_deg: float
    horizon_elevation_deg: NDArray[np.float32]
    occluder_distance_m: NDArray[np.float32]
    occluder_height_m: NDArray[np.float32]
    valid_mask: NDArray[np.uint8]
    quality: HorizonQuality
    resolved_fraction: float
    kernel_version: str = HORIZON_KERNEL_VERSION

    @property
    def sample_count(self) -> int:
        return int(self.horizon_elevation_deg.size)

    @property
    def binary_byte_length(self) -> int:
        return self.sample_count * (3 * np.dtype(np.float32).itemsize + np.dtype(np.uint8).itemsize)

    def elevation_at_azimuth(self, azimuth_deg: float) -> float:
        if self.sample_count == 0:
            return 0.0
        position = ((float(azimuth_deg) - self.azimuth_start_deg) % 360.0) / self.angular_step_deg
        left_floor = np.floor(position)
        left = int(left_floor) % self.sample_count
        right = (left + 1) % self.sample_count
        fraction = position - left_floor
        left_value = float(self.horizon_elevation_deg[left]) if self.valid_mask[left] else 0.0
        right_value = float(self.horizon_elevation_deg[right]) if self.valid_mask[right] else 0.0
        return left_value + (right_value - left_value) * fraction

    def is_occluded(self, azimuth_deg: float, altitude_deg: float) -> bool:
        return float(altitude_deg) < self.elevation_at_azimuth(azimuth_deg)
