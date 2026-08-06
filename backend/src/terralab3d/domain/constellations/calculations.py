"""Contractes de càlcul científic pur per a constel·lacions editables."""

from typing import Protocol
from terralab3d.domain.constellations.models import ConstellationNode
from terralab3d.domain.geometry import EquatorialCoordinate

class ConstellationArcCalculator(Protocol):
    """Defineix els càlculs purs de constel·lacions editables sense I/O ni renderitzat."""
    def arc_points(self, a: ConstellationNode, b: ConstellationNode, sample_count: int) -> tuple[EquatorialCoordinate, ...]: ...
