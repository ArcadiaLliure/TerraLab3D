"""Contractes de domini per a la cobertura categòrica (Land Cover)."""

from dataclasses import dataclass

@dataclass(frozen=True, slots=True)
class LandCoverTileRequest:
    min_x: float
    min_y: float
    max_x: float
    max_y: float
    resolution: float
    crs: str
    source_mode: str
    source_id: str | None

@dataclass(frozen=True, slots=True)
class LandCoverProvenance:
    source_id: str
    version: int

@dataclass(frozen=True, slots=True)
class LandCoverLegendEntry:
    class_id: int
    name: str
    color_rgba: tuple[int, int, int, int]

@dataclass(frozen=True, slots=True)
class LandCoverLegend:
    legend_id: str
    entries: tuple[LandCoverLegendEntry, ...]

@dataclass(frozen=True, slots=True)
class LandCoverTile:
    resource_id: str
    provenance: LandCoverProvenance
    legend_id: str
    min_x: float
    min_y: float
    max_x: float
    max_y: float
    width: int
    height: int
    resolution: float
    crs: str
    valid_pixels: int
    class_buffer: bytes  # IDs uint16 little-endian, con clase 0 reservada para nodata/sin cobertura
