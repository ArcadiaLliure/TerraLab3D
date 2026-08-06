"""Contractes de càlcul científic pur per a selecció i inspecció."""

from typing import Protocol


class SelectionStalenessCalculator(Protocol):
    """Defineix els càlculs purs de selecció i inspecció sense I/O ni renderitzat."""
    def is_current(self, pick_generation: int, scene_generation: int) -> bool: ...
