"""Contractes de servei purs per a la capacitat clima."""


from typing import Protocol
from .models import ClimateState

class ClimateFallbackModel(Protocol):
    """Produeix un clima de reserva determinista a partir d’una llavor explícita."""
    def state_for(self, *, day_of_year: int, hour_utc: float, seed: int) -> ClimateState: ...
