"""Contractes de servei purs per a la capacitat temps astronòmic."""


from datetime import timedelta
from typing import Protocol
from .models import ClockState

class AstronomicalClockModel(Protocol):
    """Avança l’estat immutable del rellotge sense posseir un scheduler."""
    def advance(self, state: ClockState, elapsed: timedelta) -> ClockState: ...
