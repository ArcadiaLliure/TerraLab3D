"""Contractes de servei purs per a la capacitat contaminació lumínica."""


from typing import Protocol
from .models import LightPollutionState, VisibilityLimit

class LightPollutionModel(Protocol):
    """Resol la visibilitat astronòmica efectiva des de la contaminació lumínica."""
    def evaluate(self, state: LightPollutionState, *, observer_elevation_m: float) -> VisibilityLimit: ...
