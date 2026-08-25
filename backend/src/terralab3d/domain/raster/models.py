"""Pure raster descriptions shared by imports, elevation and future layers."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping

import numpy as np
from numpy.typing import NDArray


TransformTuple = tuple[float, float, float, float, float, float]
BoundsTuple = tuple[float, float, float, float]


class RasterDatasetError(RuntimeError):
    pass


class RasterSelectionRequired(RasterDatasetError):
    pass


@dataclass(frozen=True, slots=True)
class RasterBandDescriptor:
    index: int
    dtype: str
    description: str | None
    nodata: float | int | None
    scale: float
    offset: float
    unit: str | None
    mask_flags: tuple[str, ...]
    overviews: tuple[int, ...]
    block_shape: tuple[int, int] | None
    metadata: Mapping[str, str] = field(default_factory=dict)
    color_interpretation: str | None = None
    color_map: Mapping[int, tuple[int, int, int, int]] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.index < 1:
            raise ValueError("Raster band indices start at one")
        if not np.isfinite(self.scale) or not np.isfinite(self.offset):
            raise ValueError("Raster scale and offset must be finite")


@dataclass(frozen=True, slots=True)
class RasterDatasetDescriptor:
    uri: str
    driver: str
    width: int
    height: int
    crs: str | None
    transform: TransformTuple
    bounds: BoundsTuple
    resolution: tuple[float, float]
    bands: tuple[RasterBandDescriptor, ...]
    subdatasets: tuple[str, ...]
    metadata: Mapping[str, str] = field(default_factory=dict)
    original_metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.width < 0 or self.height < 0:
            raise ValueError("Raster dimensions cannot be negative")
        if self.width and self.height and not self.bands:
            raise ValueError("A raster dataset with pixels must expose at least one band")

    @property
    def source_dtype(self) -> str | None:
        dtypes = {band.dtype for band in self.bands}
        return next(iter(dtypes)) if len(dtypes) == 1 else None

    @property
    def requires_subdataset_selection(self) -> bool:
        return bool(self.subdatasets) and not self.bands

    @property
    def requires_band_selection(self) -> bool:
        return len(self.bands) != 1


@dataclass(frozen=True, slots=True)
class RasterMetadataOverride:
    """User-provided metadata kept separate from the immutable source metadata."""

    crs: str | None = None
    transform: TransformTuple | None = None
    bounds: BoundsTuple | None = None
    nodata: float | int | None = None
    nodata_is_set: bool = False
    provenance: str = "user"

    def __post_init__(self) -> None:
        if not self.provenance.strip():
            raise ValueError("Raster override provenance is required")
        if self.transform is not None and len(self.transform) != 6:
            raise ValueError("Raster transform overrides require six coefficients")
        if self.transform is not None and self.bounds is not None:
            raise ValueError("Use either a transform override or a bounds override, not both")
        if self.bounds is not None:
            west, south, east, north = self.bounds
            if not all(np.isfinite(value) for value in self.bounds) or east <= west or north <= south:
                raise ValueError("Raster bounds overrides must be finite and ordered")


@dataclass(frozen=True, slots=True)
class TextRasterOptions:
    layout: str | None = None
    delimiter: str | None = None
    has_header: bool | None = None
    crs: str | None = None
    transform: TransformTuple | None = None
    nodata: float | int | None = None


@dataclass(frozen=True, slots=True)
class RasterDatasetSelection:
    uri: str
    band_index: int | None = None
    subdataset: str | None = None
    overrides: RasterMetadataOverride | None = None

    @property
    def selected_uri(self) -> str:
        return self.subdataset or self.uri


@dataclass(frozen=True, slots=True)
class RasterWindowRequest:
    selection: RasterDatasetSelection
    column_offset: int
    row_offset: int
    width: int
    height: int
    output_width: int | None = None
    output_height: int | None = None

    def __post_init__(self) -> None:
        if min(self.column_offset, self.row_offset) < 0:
            raise ValueError("Raster window offsets cannot be negative")
        if self.width < 1 or self.height < 1:
            raise ValueError("Raster window dimensions must be positive")
        if self.output_width is not None and self.output_width < 1:
            raise ValueError("Raster output width must be positive")
        if self.output_height is not None and self.output_height < 1:
            raise ValueError("Raster output height must be positive")


@dataclass(frozen=True, slots=True)
class RasterWindow:
    values: NDArray[np.generic]
    valid_mask: NDArray[np.bool_]
    source_dtype: str
    transform: TransformTuple

    def __post_init__(self) -> None:
        values = np.asarray(self.values)
        valid = np.asarray(self.valid_mask, dtype=np.bool_)
        if values.ndim != 2 or values.shape != valid.shape:
            raise ValueError("Raster values and validity must be aligned 2D arrays")
        object.__setattr__(self, "values", values)
        object.__setattr__(self, "valid_mask", valid)
