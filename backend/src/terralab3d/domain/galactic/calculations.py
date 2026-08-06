"""Contractes de càlcul científic pur per a Via Làctia i pols Planck."""

from typing import Protocol
from terralab3d.domain.galactic.models import GalacticAppearance

class GalacticVisibilityCalculator(Protocol):
    """Defineix els càlculs purs de Via Làctia i pols Planck sense I/O ni renderitzat."""
    def effective_opacity(self, appearance: GalacticAppearance, sky_luminance: float) -> float: ...
    def sidereal_rotation_rad(self, local_sidereal_angle_deg: float, ra_offset_deg: float) -> float: ...
