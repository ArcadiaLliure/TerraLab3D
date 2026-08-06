"""Contractes de càlcul científic pur per a horitzó topogràfic."""

from typing import Protocol
from terralab3d.domain.horizon.models import HorizonProfile, HorizonRequest, HorizonSample

class HorizonCalculator(Protocol):
    """Defineix els càlculs purs de horitzó topogràfic sense I/O ni renderitzat."""
    def build_profile(self, request: HorizonRequest, samples: tuple[HorizonSample, ...]) -> HorizonProfile: ...
    def occludes(self, profile: HorizonProfile, azimuth_deg: float, altitude_deg: float) -> bool: ...
