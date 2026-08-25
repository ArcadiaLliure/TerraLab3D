"""Boundary for exact categorical raster analysis and indexed materialization."""

from __future__ import annotations

from pathlib import Path
from typing import Callable, Mapping, Protocol

from terralab3d.domain.raster.models import RasterDatasetSelection
from terralab3d.domain.surface.categorical import (
    CategoricalEncoding,
    CategoricalRasterAnalysis,
)
from terralab3d.domain.surface.tlst import SourceValue


class CategoricalRasterPort(Protocol):
    def analyse(
        self,
        selection: RasterDatasetSelection,
        *,
        encoding: CategoricalEncoding,
        band_indices: tuple[int, ...],
        progress_callback: Callable[[float], None] | None = None,
    ) -> CategoricalRasterAnalysis: ...

    def materialize_indexed(
        self,
        selection: RasterDatasetSelection,
        destination: Path,
        *,
        encoding: CategoricalEncoding,
        band_indices: tuple[int, ...],
        code_by_source_value: Mapping[SourceValue, int],
        progress_callback: Callable[[float], None] | None = None,
    ) -> Path: ...
