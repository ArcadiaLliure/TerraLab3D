"""Serveis de domini per a superfícies."""
from typing import Protocol
from .models import SurfaceMaterialDescriptor, SurfaceSampleGrid

class SurfaceMaterialModel(Protocol):
    """Converteix mostres i estil en un descriptor de material neutral."""
    def describe(self, grid: SurfaceSampleGrid, *, style_key: str, version: int) -> SurfaceMaterialDescriptor: ...
