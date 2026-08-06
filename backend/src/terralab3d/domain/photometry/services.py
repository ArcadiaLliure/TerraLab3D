"""Serveis de domini per a la fotometria astronòmica."""
from typing import Protocol
from .models import DetectionThreshold

class VisibilityContrastModel(Protocol):
    """Calcula el llindar de detecció a partir del fons i l’instrument."""
    def threshold(self, *, sky_luminance: float, instrument_gain: float) -> DetectionThreshold: ...
