"""Contractes de càlcul científic pur per a cerca astronòmica."""

from typing import Protocol
from terralab3d.domain.geometry import EquatorialCoordinate

class SearchNormalizationCalculator(Protocol):
    """Defineix els càlculs purs de cerca astronòmica sense I/O ni renderitzat."""
    def normalize_query(self, text: str) -> str: ...
    def coordinate_query(self, text: str) -> EquatorialCoordinate | None: ...
