"""Contractes de càlcul científic pur per a atmosfera i extinció."""

from typing import Protocol


class AtmosphericExtinctionCalculator(Protocol):
    """Defineix els càlculs purs de atmosfera i extinció sense I/O ni renderitzat."""
    def airmass(self, altitude_deg: float) -> float: ...
    def extinction_magnitude(self, altitude_deg: float, coefficient: float) -> float: ...
