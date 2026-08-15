"""Typed, renderer-neutral elevation and DEM contracts."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Callable

import numpy as np
from numpy.typing import NDArray

from terralab3d.domain.observer.models import GeoLocation


class ElevationStatus(StrEnum):
    REAL = "real"
    NODATA = "nodata"
    UNAVAILABLE = "unavailable"
    CANCELLED = "cancelled"
    ERROR = "error"


@dataclass(frozen=True, slots=True)
class ElevationSourceMetadata:
    source_id: str
    fingerprint: str
    native_crs: str
    resolution_m: float | None
    bounds: tuple[float, float, float, float] | None
    nodata: float | None
    format: str
    source_ids: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class ElevationSample:
    location: GeoLocation
    elevation_m: float | None
    source_id: str | None
    status: ElevationStatus

    @property
    def available(self) -> bool:
        return self.status is ElevationStatus.REAL and self.elevation_m is not None


@dataclass(frozen=True, slots=True)
class ElevationBatchRequest:
    """Point batch. Arrays may have any shape but must align."""

    latitude_deg: NDArray[np.float64]
    longitude_deg: NDArray[np.float64]
    input_crs: str = "EPSG:4326"
    cancellation_check: Callable[[], bool] | None = None

    def __post_init__(self) -> None:
        latitude = np.asarray(self.latitude_deg, dtype=np.float64)
        longitude = np.asarray(self.longitude_deg, dtype=np.float64)
        if latitude.shape != longitude.shape:
            raise ValueError("Latitude and longitude batches must have the same shape")
        object.__setattr__(self, "latitude_deg", latitude)
        object.__setattr__(self, "longitude_deg", longitude)


@dataclass(frozen=True, slots=True)
class ElevationBatch:
    values_m: NDArray[np.float32]
    valid_mask: NDArray[np.bool_]
    source_indices: NDArray[np.int16] | None = None
    status: ElevationStatus = ElevationStatus.REAL

    def __post_init__(self) -> None:
        values = np.asarray(self.values_m, dtype=np.float32)
        valid = np.asarray(self.valid_mask, dtype=np.bool_)
        if values.shape != valid.shape:
            raise ValueError("Elevation values and valid mask must have the same shape")
        indices = self.source_indices
        if indices is None:
            indices = np.full(values.shape, -1, dtype=np.int16)
        else:
            indices = np.asarray(indices, dtype=np.int16)
            if indices.shape != values.shape:
                raise ValueError("Elevation source indices must match the values shape")
        object.__setattr__(self, "values_m", values)
        object.__setattr__(self, "valid_mask", valid)
        object.__setattr__(self, "source_indices", indices)


@dataclass(frozen=True, slots=True)
class ElevationGrid:
    """Observer-relative DEM samples for terrain preparation, never a fallback mesh."""

    width: int
    height: int
    spacing_m: float
    crs: str
    elevation_buffer_key: str
    values_m: NDArray[np.float32]
    valid_mask: NDArray[np.bool_]
    source_indices: NDArray[np.int16]
