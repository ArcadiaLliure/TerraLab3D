"""Models de domini tipats per a la capacitat terreny."""


from dataclasses import dataclass
from enum import Enum
from terralab3d.domain.identifiers import ResourceId, TerrainTileId

class SurfaceMode(str, Enum):
    BASE = "base"
    ORTHOPHOTO = "orthophoto"
    CATEGORICAL = "categorical"

@dataclass(frozen=True, slots=True)
class TerrainTileRequest:
    tile_id: TerrainTileId
    center_latitude_deg: float
    center_longitude_deg: float
    radius_m: float
    target_resolution_m: float

@dataclass(frozen=True, slots=True)
class TerrainMeshResource:
    resource_id: ResourceId
    version: int
    tile_id: TerrainTileId
    vertex_buffer_key: str
    index_buffer_key: str
    normal_buffer_key: str
    bounds_key: str

@dataclass(frozen=True, slots=True)
class TerrainMaterialResource:
    resource_id: ResourceId
    version: int
    mode: SurfaceMode
    texture_key: str | None
    category_buffer_key: str | None


@dataclass(frozen=True, slots=True)
class TerrainChunkIdentity:
    """Lightweight terrain chunk reference for surface coordination.

    This DTO allows the surface subsystem to reference a specific terrain
    chunk without importing Three.js or the full mesh builder.
    """
    content_key: str
    version: int
    vertex_count: int
    center_east_m: float
    center_north_m: float
    bounds_west_deg: float | None = None
    bounds_south_deg: float | None = None
    bounds_east_deg: float | None = None
    bounds_north_deg: float | None = None
