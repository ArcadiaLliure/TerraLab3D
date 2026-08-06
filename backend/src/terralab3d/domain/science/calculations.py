"""Contractes de càlcul científic pur per a fonaments científics compartits."""

from typing import Protocol


class ScientificUnitsCalculator(Protocol):
    """Defineix els càlculs purs de fonaments científics compartits sense I/O ni renderitzat."""
    def convert_angle(self, value: float, source_unit: str, target_unit: str) -> float: ...
    def normalize_periodic(self, value: float, period: float) -> float: ...
