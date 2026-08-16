"""Models de domini tipats per a cobertura categòrica i estils de superfície.

Separació de responsabilitats:
  - LandCoverSourceDescriptor: metadades d'una font de cobertura
  - LandCoverLegend / LandCoverLegendEntry: llegenda semàntica
  - LandCoverSamplingRequest: petició de mostreig per a un chunk
  - LandCoverSampleGrid: resultat del mostreig
  - CategoricalSurfaceResource: recurs versionat publicable al frontend
  - SurfaceStyle: estil visual aplicable (BASE / CATEGORICAL_ORIGINAL)

Cap d'aquests tipus importa rasterio, pyproj, Three.js ni fa I/O.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Sequence

import numpy as np

from terralab3d.domain.identifiers import ResourceId


# ─── Enums ────────────────────────────────────────────────────────────

class SurfaceSampleKind(str, Enum):
    """Physical representation of the sample data."""
    RGB = "rgb"
    CATEGORICAL = "categorical"


class SurfaceStyle(str, Enum):
    """Visual style applied to terrain surface."""
    BASE = "base"
    CATEGORICAL_ORIGINAL = "categorical_original"


from enum import Enum, IntEnum

class LandCoverProvenance(IntEnum):
    """How a particular sample was obtained."""
    EXACT = 0
    MODAL_LOD = 1
    SOURCE_FALLBACK = 2
    NODATA = 3


class LandCoverSourceType(str, Enum):
    """Semantic type of a land-cover raster source."""
    CATEGORICAL_NATIVE = "categorical_native"
    CATEGORICAL_RGB = "categorical_rgb"


# ─── Legend ───────────────────────────────────────────────────────────

@dataclass(frozen=True, slots=True)
class LandCoverLegendEntry:
    """One entry in a categorical legend."""
    class_id: int
    name: str
    rgba: tuple[int, int, int, int]
    is_nodata: bool = False
    is_transparent: bool = False


@dataclass(frozen=True, slots=True)
class LandCoverLegend:
    """Complete legend for a categorical source."""
    legend_id: str
    source_id: str
    entries: tuple[LandCoverLegendEntry, ...]

    def entry_by_class(self, class_id: int) -> LandCoverLegendEntry | None:
        for entry in self.entries:
            if entry.class_id == class_id:
                return entry
        return None

    def rgba_by_class(self, class_id: int) -> tuple[int, int, int, int] | None:
        entry = self.entry_by_class(class_id)
        return entry.rgba if entry is not None else None


# ─── Source descriptor ────────────────────────────────────────────────

@dataclass(frozen=True, slots=True)
class LandCoverSourceDescriptor:
    """Metadata for a single land-cover source.

    No I/O here — the adapter populates these from config / raster headers.
    """
    id: str
    name: str
    source_type: LandCoverSourceType
    crs: str | None
    resolution_m: float
    bounds: tuple[float, float, float, float] | None  # west, south, east, north
    coverage: tuple[float, float, float, float] | None  # west, south, east, north
    priority: int
    legend_id: str | None
    fingerprint: str
    provenance: str = ""
    attribution: str = ""
    enabled: bool = True


# ─── Sampling request ─────────────────────────────────────────────────

@dataclass(frozen=True, slots=True)
class LandCoverSamplingRequest:
    """Request to sample land-cover classes for terrain vertices."""
    terrain_content_key: str
    terrain_version: int
    latitude_deg: np.ndarray
    longitude_deg: np.ndarray
    generation: int
    lod_tier: int = 0
    selected_source_id: str | None = None  # None = automatic
    cancellation_check: object = None  # Callable[[], bool] | None


# ─── Sample grid result ───────────────────────────────────────────────

@dataclass(frozen=True, slots=True)
class LandCoverSampleGrid:
    """Result of sampling land-cover classes over terrain vertices.

    All arrays have the same length as the input coordinates.
    """
    class_ids: np.ndarray         # uint16: raw class id from the source
    palette_indices: np.ndarray   # uint16: index into the shared palette
    source_slots: np.ndarray      # int16: ordinal of the source that resolved this sample
    valid: np.ndarray             # bool: whether this sample has a resolved category
    provenance: np.ndarray        # uint8: LandCoverProvenance ordinal per sample
    resolved_fraction: float
    fallback_fraction: float
    source_descriptors: tuple[LandCoverSourceDescriptor, ...]
    legend: LandCoverLegend | None
    colors_rgba: np.ndarray | None = None      # uint8: 2D array [N, 4] of RGBA colors for each vertex

    @property
    def sample_count(self) -> int:
        return int(self.class_ids.shape[0])


# ─── Categorical surface resource ─────────────────────────────────────

@dataclass(frozen=True, slots=True)
class CategoricalSurfaceResource:
    """Versionat resource descriptor for a categorical surface overlay.

    Published to the frontend alongside binary buffers.
    """
    resource_id: ResourceId
    version: int
    generation: int
    terrain_content_key: str
    compatible_terrain_version: int
    sample_count: int
    resolved_fraction: float
    fallback_fraction: float
    legend: LandCoverLegend | None
    source_descriptors: tuple[LandCoverSourceDescriptor, ...]
    sampling_metadata: dict[str, object] = field(default_factory=dict)


# ─── Palette entry ────────────────────────────────────────────────────

@dataclass(frozen=True, slots=True)
class SurfacePaletteEntry:
    """One entry in the compact GPU palette shared with the frontend."""
    palette_index: int
    class_id: int
    source_slot: int
    r: int
    g: int
    b: int
    a: int


# ─── Legacy compatibility ─────────────────────────────────────────────
# These DTOs from the original skeleton are preserved for compatibility but
# their role is now served by the richer types above.

@dataclass(frozen=True, slots=True)
class SurfaceSampleGrid:
    kind: SurfaceSampleKind
    width: int
    height: int
    value_buffer_key: str
    legend_id: str | None


@dataclass(frozen=True, slots=True)
class SurfaceMaterialDescriptor:
    resource_id: ResourceId
    version: int
    style_key: str
    texture_resource_id: ResourceId | None
