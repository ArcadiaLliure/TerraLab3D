"""Contractes de càlcul científic pur per a meteorologia."""

from typing import Protocol
from terralab3d.domain.climate.models import ClimateState

class ClimateOpticsCalculator(Protocol):
    """Defineix els càlculs purs de meteorologia sense I/O ni renderitzat."""
    def transparency(self, state: ClimateState) -> float: ...
    def cloud_extinction(self, state: ClimateState) -> float: ...
