"""Contractes de càlcul científic pur per a ubicació de l’observador."""

from typing import Protocol
from terralab3d.domain.observer.models import ObserverProfile

class ObserverGeodesyCalculator(Protocol):
    """Defineix els càlculs purs d’ubicació de l’observador sense I/O ni renderitzat."""
    def geodetic_to_ecef(self, latitude_deg: float, longitude_deg: float, height_m: float) -> tuple[float, float, float]: ...
    def effective_height_m(self, terrain_height_m: float, offset_m: float) -> float: ...
