"""Contractes de servei purs per a la capacitat atmosfera."""


from typing import Protocol
from .models import AtmosphereParameters, SkyAppearance

class AtmosphereModel(Protocol):
    """Resol paràmetres científics d’aparença del cel, no píxels."""
    def evaluate(self, parameters: AtmosphereParameters) -> SkyAppearance: ...
