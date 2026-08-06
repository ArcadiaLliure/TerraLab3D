"""Contractes de càlcul científic pur per a elevacions i DEM."""

from typing import Protocol
from terralab3d.domain.elevation.models import ElevationGrid

class ElevationAnalysisCalculator(Protocol):
    """Defineix els càlculs purs de elevacions i DEM sense I/O ni renderitzat."""
    def interpolate(self, grid: ElevationGrid, x: float, y: float) -> float | None: ...
    def surface_normal(self, grid: ElevationGrid, x: int, y: int) -> tuple[float, float, float]: ...
