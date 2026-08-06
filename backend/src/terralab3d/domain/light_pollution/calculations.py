"""Contractes de càlcul científic pur per a contaminació lumínica."""

from typing import Protocol
from terralab3d.domain.light_pollution.models import LightPollutionState, VisibilityLimit

class LightPollutionCalculator(Protocol):
    """Defineix els càlculs purs de contaminació lumínica sense I/O ni renderitzat."""
    def limiting_magnitude(self, state: LightPollutionState, atmospheric_extinction: float) -> VisibilityLimit: ...
    def sky_luminance(self, state: LightPollutionState) -> float: ...
