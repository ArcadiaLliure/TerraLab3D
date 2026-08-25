"""Exact categorical analysis over the universal raster port.

RGB/RGBA inputs are never interpolated semantically. They are converted to a
rebuildable indexed GeoTIFF only after the user confirms a versioned scheme.
The source file and source values remain the audit authority.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import replace
from math import ceil
from pathlib import Path
from typing import Callable, Mapping

import numpy as np
import rasterio
from affine import Affine

from terralab3d.application.ports.raster import RasterReaderPort
from terralab3d.domain.raster.models import (
    RasterDatasetError,
    RasterDatasetSelection,
    RasterWindowRequest,
)
from terralab3d.domain.surface.categorical import (
    CategoricalEncoding,
    CategoricalRasterAnalysis,
    CategoricalValueCount,
    rgba_source_value,
    source_value_rgba,
)
from terralab3d.domain.surface.tlst import SourceValue


_WINDOW_SIZE = 1024
_MAX_CATEGORY_COUNT = 65_536


class RasterioCategoricalRasterAdapter:
    def __init__(self, reader: RasterReaderPort) -> None:
        self._reader = reader

    def analyse(
        self,
        selection: RasterDatasetSelection,
        *,
        encoding: CategoricalEncoding,
        band_indices: tuple[int, ...],
        progress_callback: Callable[[float], None] | None = None,
    ) -> CategoricalRasterAnalysis:
        descriptor = self._validate_bands(selection, encoding, band_indices)
        counts: Counter[SourceValue] = Counter()
        valid_pixels = 0
        invalid_pixels = 0

        total_windows = ceil(descriptor.width / _WINDOW_SIZE) * ceil(descriptor.height / _WINDOW_SIZE)
        for index, (row, column, width, height) in enumerate(_windows(descriptor.width, descriptor.height)):
            if progress_callback is not None:
                progress_callback(index / max(1, total_windows))
            values, valid = self._read_values(
                selection, encoding, band_indices, column, row, width, height,
            )
            count = int(np.count_nonzero(valid))
            valid_pixels += count
            invalid_pixels += int(valid.size - count)
            if not np.any(valid):
                continue
            unique, unique_counts = np.unique(values[valid], return_counts=True)
            for value, occurrences in zip(unique.tolist(), unique_counts.tolist(), strict=True):
                counts[self._source_value(value, encoding)] += int(occurrences)
            if len(counts) > _MAX_CATEGORY_COUNT:
                raise RasterDatasetError(
                    "The raster exposes more than 65536 exact values and cannot be "
                    "represented as a categorical legend"
                )

        palette = descriptor.bands[band_indices[0] - 1].color_map
        analysed = tuple(
            CategoricalValueCount(
                source_value=value,
                pixel_count=counts[value],
                color_rgba=self._value_color(value, encoding, palette),
            )
            for value in sorted(counts, key=_source_value_sort_key)
        )
        source_dtypes = ",".join(descriptor.bands[index - 1].dtype for index in band_indices)
        return CategoricalRasterAnalysis(
            encoding=encoding,
            band_indices=band_indices,
            source_dtype=source_dtypes,
            values=analysed,
            valid_pixels=valid_pixels,
            invalid_pixels=invalid_pixels,
        )

    def materialize_indexed(
        self,
        selection: RasterDatasetSelection,
        destination: Path,
        *,
        encoding: CategoricalEncoding,
        band_indices: tuple[int, ...],
        code_by_source_value: Mapping[SourceValue, int],
        progress_callback: Callable[[float], None] | None = None,
    ) -> Path:
        descriptor = self._validate_bands(selection, encoding, band_indices)
        if descriptor.crs is None:
            raise RasterDatasetError(
                "Categorical import requires a CRS or an explicit CRS override"
            )
        codes = tuple(code_by_source_value.values())
        if len(codes) != len(set(codes)) or any(code < 0 or code > 0xFFFF for code in codes):
            raise RasterDatasetError("Execution codes must be unique uint16 values")

        destination = destination.resolve(strict=False)
        destination.parent.mkdir(parents=True, exist_ok=True)
        temporary = destination.with_suffix(destination.suffix + ".tmp")
        profile = {
            "driver": "GTiff",
            "width": descriptor.width,
            "height": descriptor.height,
            "count": 1,
            "dtype": "uint16",
            "crs": descriptor.crs,
            "transform": Affine(*descriptor.transform),
            "compress": "deflate",
            "predictor": 2,
            "tiled": descriptor.width >= 16 and descriptor.height >= 16,
        }
        try:
            total_windows = ceil(descriptor.width / _WINDOW_SIZE) * ceil(descriptor.height / _WINDOW_SIZE)
            with rasterio.open(temporary, "w", **profile) as target:
                target.update_tags(
                    TERRALAB_DERIVED="categorical-index-v1",
                    TERRALAB_SOURCE_DTYPE=",".join(
                        descriptor.bands[index - 1].dtype for index in band_indices
                    ),
                    TERRALAB_ENCODING=encoding.value,
                )
                for index, (row, column, width, height) in enumerate(_windows(
                    descriptor.width, descriptor.height,
                )):
                    if progress_callback is not None:
                        progress_callback(index / max(1, total_windows))
                    values, valid = self._read_values(
                        selection, encoding, band_indices, column, row, width, height,
                    )
                    indexed = np.zeros((height, width), dtype=np.uint16)
                    for raw_value in np.unique(values[valid]).tolist():
                        source_value = self._source_value(raw_value, encoding)
                        code = code_by_source_value.get(source_value)
                        if code is None:
                            raise RasterDatasetError(
                                "Confirmed scheme has no mapping for source value "
                                f"{source_value!r}"
                            )
                        indexed[valid & (values == raw_value)] = np.uint16(code)
                    window = rasterio.windows.Window(column, row, width, height)
                    target.write(indexed, 1, window=window)
                    target.write_mask(valid.astype(np.uint8) * 255, window=window)
            temporary.replace(destination)
        except Exception:
            temporary.unlink(missing_ok=True)
            raise
        return destination

    def _validate_bands(
        self,
        selection: RasterDatasetSelection,
        encoding: CategoricalEncoding,
        band_indices: tuple[int, ...],
    ):
        expected = {
            CategoricalEncoding.INTEGER: 1,
            CategoricalEncoding.PALETTE: 1,
            CategoricalEncoding.RGB: 3,
            CategoricalEncoding.RGBA: 4,
        }[encoding]
        if len(band_indices) != expected or len(set(band_indices)) != expected:
            raise RasterDatasetError(
                f"{encoding.value} requires {expected} explicit, distinct band indices"
            )
        descriptor = None
        for index in band_indices:
            descriptor = self._reader.validate_selection(replace(selection, band_index=index))
            dtype = np.dtype(descriptor.bands[index - 1].dtype)
            if dtype.kind not in {"u", "i"}:
                raise RasterDatasetError("Categorical bands must use an integral source dtype")
            if encoding in {CategoricalEncoding.RGB, CategoricalEncoding.RGBA} and dtype.itemsize != 1:
                raise RasterDatasetError("RGB/RGBA categorical channels must be lossless bytes")
        assert descriptor is not None
        if encoding is CategoricalEncoding.PALETTE and not descriptor.bands[band_indices[0] - 1].color_map:
            raise RasterDatasetError("Palette encoding requires an embedded colour table")
        return descriptor

    def _read_values(
        self,
        selection: RasterDatasetSelection,
        encoding: CategoricalEncoding,
        band_indices: tuple[int, ...],
        column: int,
        row: int,
        width: int,
        height: int,
    ) -> tuple[np.ndarray, np.ndarray]:
        bands = []
        valid = np.ones((height, width), dtype=np.bool_)
        for index in band_indices:
            window = self._reader.read_window(RasterWindowRequest(
                selection=replace(selection, band_index=index),
                column_offset=column,
                row_offset=row,
                width=width,
                height=height,
            ))
            bands.append(np.asarray(window.values))
            valid &= window.valid_mask
        if encoding in {CategoricalEncoding.INTEGER, CategoricalEncoding.PALETTE}:
            values = bands[0]
            eligible = values[valid]
            if eligible.size and (
                not np.all(np.isfinite(eligible))
                or not np.all(eligible == np.floor(eligible))
            ):
                raise RasterDatasetError("Categorical source values must be finite integers")
            return values.astype(np.int64, copy=False), valid
        stacked = np.stack(bands, axis=-1).astype(np.uint32, copy=False)
        packed = stacked[..., 0] << 24
        packed |= stacked[..., 1] << 16
        packed |= stacked[..., 2] << 8
        packed |= stacked[..., 3] if encoding is CategoricalEncoding.RGBA else 255
        return packed, valid

    @staticmethod
    def _source_value(value: object, encoding: CategoricalEncoding) -> SourceValue:
        integer = int(value)
        if encoding in {CategoricalEncoding.INTEGER, CategoricalEncoding.PALETTE}:
            return integer
        channels = (
            (integer >> 24) & 0xFF,
            (integer >> 16) & 0xFF,
            (integer >> 8) & 0xFF,
            integer & 0xFF,
        )
        return rgba_source_value(
            channels[:3] if encoding is CategoricalEncoding.RGB else channels,
        )

    @staticmethod
    def _value_color(
        value: SourceValue,
        encoding: CategoricalEncoding,
        palette: Mapping[int, tuple[int, int, int, int]],
    ) -> tuple[int, int, int, int] | None:
        if encoding is CategoricalEncoding.PALETTE and isinstance(value, int):
            return palette.get(value)
        if encoding in {CategoricalEncoding.RGB, CategoricalEncoding.RGBA} and isinstance(value, str):
            return source_value_rgba(value)
        return None


def _windows(width: int, height: int):
    for row in range(0, height, _WINDOW_SIZE):
        window_height = min(_WINDOW_SIZE, height - row)
        for column in range(0, width, _WINDOW_SIZE):
            yield row, column, min(_WINDOW_SIZE, width - column), window_height


def _source_value_sort_key(value: SourceValue) -> tuple[int, int | str]:
    return (0, value) if isinstance(value, int) else (1, value)
