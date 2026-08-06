"""Contractes de servei purs per a la capacitat observador."""


from typing import Protocol
from .models import GeoLocation, ObserverProfile

class ObserverProfileFactory(Protocol):
    """Crea perfils d’observador validats des de valors geodèsics."""
    def create(self, location: GeoLocation, height_offset_m: float) -> ObserverProfile: ...
