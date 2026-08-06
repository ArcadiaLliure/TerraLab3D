"""Contractes de càlcul científic pur per a estrelles i catàleg Gaia."""

from typing import Protocol
from terralab3d.domain.stars.models import StarRecord

class StarVisibilityCalculator(Protocol):
    """Defineix els càlculs purs de estrelles i catàleg Gaia sense I/O ni renderitzat."""
    def visible(self, record: StarRecord, magnitude_limit: float, extinction: float) -> bool: ...
    def apparent_magnitude(self, record: StarRecord, extinction: float) -> float: ...
