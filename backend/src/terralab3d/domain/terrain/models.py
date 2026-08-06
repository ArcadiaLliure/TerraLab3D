"""Models de domini tipats per a la capacitat terreny."""


from dataclasses import dataclass
from enum import Enum
from terralab3d.domain.identifiers import ResourceId, TerrainTileId

class SurfaceMode(str, Enum):
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
