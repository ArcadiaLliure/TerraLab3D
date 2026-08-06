"""Contractes de càlcul científic pur per a objectes de cel profund."""

from typing import Protocol
from terralab3d.domain.deep_sky.models import DeepSkyObject

class DeepSkyVisibilityCalculator(Protocol):
    """Defineix els càlculs purs de objectes de cel profund sense I/O ni renderitzat."""
    def visible(self, item: DeepSkyObject, limiting_magnitude: float, minimum_surface_brightness: float) -> bool: ...
    def apparent_extent_deg(self, item: DeepSkyObject) -> tuple[float, float]: ...
