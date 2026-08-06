"""Contractes de servei purs per a la capacitat horitzó."""
from typing import Protocol
from .models import HorizonProfile, HorizonRequest, HorizonSample

class HorizonModel(Protocol):
    """Consulta l’oclusió sobre un perfil d’horitzó ja construït."""
    def is_occluded(self, profile: HorizonProfile, *, azimuth_deg: float, altitude_deg: float) -> bool: ...

class HorizonProfileBuilder(Protocol):
    """Construeix un perfil sense posseir accés DEM ni planificació."""
    def build(self, request: HorizonRequest, elevation_samples: tuple[HorizonSample, ...]) -> HorizonProfile: ...
