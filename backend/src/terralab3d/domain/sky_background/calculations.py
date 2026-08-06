"""Contractes de càlcul científic pur per a fons celeste, dia, nit i crepuscle."""

from typing import Protocol


class TwilightCalculator(Protocol):
    """Defineix els càlculs purs de fons celeste, dia, nit i crepuscle sense I/O ni renderitzat."""
    def twilight_factor(self, sun_altitude_deg: float) -> float: ...
    def night_factor(self, sun_altitude_deg: float, moon_luminance: float) -> float: ...
