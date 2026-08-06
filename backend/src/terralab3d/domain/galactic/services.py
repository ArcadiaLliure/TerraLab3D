"""Contractes de servei purs per a la capacitat Via Làctia i pols."""


from typing import Protocol
from .models import GalacticAppearance

class GalacticVisibilityModel(Protocol):
    """Resol visibilitat de Via Làctia i pols sense mostrejar textures."""
    def evaluate(self, *, bortle: float, magnitude_limit: float, atmosphere_extinction: float, instrument_gain: float) -> GalacticAppearance: ...
