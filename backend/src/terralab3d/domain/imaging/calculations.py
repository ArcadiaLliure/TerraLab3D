"""Contractes de càlcul científic pur per a simulació fotogràfica."""

from typing import Protocol
from terralab3d.domain.imaging.models import ImagingSession, ImagingSignalEstimate

class ImagingSignalCalculator(Protocol):
    """Defineix els càlculs purs de simulació fotogràfica sense I/O ni renderitzat."""
    def estimate(self, session: ImagingSession, relative_flux: float, sky_flux: float) -> ImagingSignalEstimate: ...
    def trail_length_deg(self, exposure_s: float, declination_deg: float, tracking_enabled: bool) -> float: ...
