"""Infrastructure boundary for universal raster metadata and window reads."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping, Protocol

from terralab3d.domain.raster.models import (
    RasterDatasetDescriptor,
    RasterDatasetSelection,
    RasterWindow,
    RasterWindowRequest,
)


class RasterReaderPort(Protocol):
    def drivers(self) -> Mapping[str, str]: ...
    def inspect(
        self,
        uri: str,
        *,
        subdataset: str | None = None,
    ) -> RasterDatasetDescriptor: ...
    def read_window(self, request: RasterWindowRequest) -> RasterWindow: ...
    def validate_selection(self, selection: RasterDatasetSelection) -> RasterDatasetDescriptor: ...
    def release(self, selection: RasterDatasetSelection) -> None: ...
    def close(self) -> None: ...


class TextRasterMaterializerPort(Protocol):
    def materialize(self, source_path: Path | str, cache_dir: Path | str, options: Any) -> Path: ...
