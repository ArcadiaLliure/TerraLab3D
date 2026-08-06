"""Serveis de domini per a elevacions i DEM."""
from typing import Protocol
from .models import ElevationGrid

class ElevationGridModel(Protocol):
    """Normalitza un grid i conserva metadades científiques explícites."""
    def normalize(self, grid: ElevationGrid) -> ElevationGrid: ...
