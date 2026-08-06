"""Contractes de càlcul científic pur per a superfícies, ortofoto i cobertura categòrica."""

from typing import Protocol
from terralab3d.domain.surface.models import SurfaceMaterialDescriptor, SurfaceSampleGrid

class SurfaceSamplingCalculator(Protocol):
    """Defineix els càlculs purs de superfícies, ortofoto i cobertura categòrica sense I/O ni renderitzat."""
    def resample(self, grid: SurfaceSampleGrid, target_width: int, target_height: int) -> SurfaceSampleGrid: ...
    def material(self, grid: SurfaceSampleGrid, style_key: str, version: int) -> SurfaceMaterialDescriptor: ...
