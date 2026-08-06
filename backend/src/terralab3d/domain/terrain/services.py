"""Contractes de servei purs per a la capacitat terreny."""
from typing import Protocol, Sequence
from terralab3d.domain.elevation.models import ElevationGrid
from terralab3d.domain.surface.models import SurfaceSampleGrid
from .models import TerrainMaterialResource, TerrainMeshResource, TerrainTileRequest

class TerrainGeometryModel(Protocol):
    """Crea descriptors de malla des de grids d’elevació subministrats."""
    def build_mesh(self, request: TerrainTileRequest, elevation_grid: ElevationGrid, *, version: int) -> TerrainMeshResource: ...

class TerrainMaterialModel(Protocol):
    """Descriu recursos de material de superfície sense renderitzar-los."""
    def build_material(self, *, mode: str, sampled_surface: SurfaceSampleGrid, version: int) -> TerrainMaterialResource: ...

class TerrainTileSelectionModel(Protocol):
    """Selecciona tiles retinguts a partir d’entrades de visibilitat gruixuda."""
    def select(self, available: Sequence[TerrainTileRequest], *, camera_latitude_deg: float, camera_longitude_deg: float, visibility_radius_m: float) -> Sequence[TerrainTileRequest]: ...
