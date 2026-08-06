"""Contractes de càlcul científic pur per a geometria de terreny 3D."""

from typing import Protocol
from terralab3d.domain.terrain.models import TerrainMeshResource, TerrainTileRequest

class TerrainMeshCalculator(Protocol):
    """Defineix els càlculs purs de geometria de terreny 3D sense I/O ni renderitzat."""
    def build_mesh(self, request: TerrainTileRequest, elevation_buffer_key: str, version: int) -> TerrainMeshResource: ...
    def select_lod(self, distance_m: float, screen_error_px: float) -> int: ...
