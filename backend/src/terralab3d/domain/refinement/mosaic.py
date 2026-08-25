"""Contracts for deterministic TLST refinement mosaics."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import IntEnum
from pathlib import Path
from types import MappingProxyType
from typing import Mapping

from .errors import RefinementValidationError
from .installations import GeometryRecord
from .licensing import LicenseMetadata


class SourcePriority(IntEnum):
    LOCAL_OFFICIAL = 0
    THEMATIC_REFINEMENT = 1
    EUROPEAN_HIGH_RESOLUTION = 2
    GENERAL_LAND_COVER = 3


@dataclass(frozen=True, slots=True)
class RasterRefinementSource:
    source_id: str
    product: str
    version: str
    path: Path
    band: int
    translations: Mapping[int, str]
    priority: SourcePriority
    license: LicenseMetadata
    asset_checksum: str
    confidence: int = 100
    qualifier_key: str | None = None
    invalid_values: tuple[int, ...] = ()

    def __post_init__(self) -> None:
        if not self.source_id.strip() or not self.product.strip() or not self.version.strip():
            raise RefinementValidationError("Raster refinement source metadata is incomplete")
        if self.band <= 0 or not self.translations:
            raise RefinementValidationError("Raster source requires a band and translations")
        if not 0 <= self.confidence <= 100:
            raise RefinementValidationError("Source confidence must be between 0 and 100")
        object.__setattr__(self, "translations", MappingProxyType(dict(self.translations)))


@dataclass(frozen=True, slots=True)
class MosaicUpdateResult:
    mosaic_path: Path
    source_path: Path
    quality_path: Path
    conflict_path: Path
    manifest_path: Path
    verified_geometry: GeometryRecord
    updated_windows: tuple[tuple[int, int, int, int], ...]
    conflict_pixels: int
    qualifier_paths: Mapping[str, Path] = field(default_factory=dict)
