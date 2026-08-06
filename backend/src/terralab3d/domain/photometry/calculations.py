"""Contractes de càlcul científic pur per a fotometria astronòmica compartida."""

from typing import Protocol
from terralab3d.domain.photometry.models import DetectionThreshold

class PhotometryCalculator(Protocol):
    """Defineix els càlculs purs de fotometria astronòmica compartida sense I/O ni renderitzat."""
    def magnitude_to_relative_flux(self, magnitude: float, zero_point: float) -> float: ...
    def relative_flux_to_magnitude(self, relative_flux: float, zero_point: float) -> float: ...
    def detection_threshold(self, sky_luminance: float, instrument_gain: float) -> DetectionThreshold: ...
