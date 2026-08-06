"""Contractes de casos d’ús de l’aplicació."""
from typing import Protocol
from terralab3d.application.events import ApplicationEvent
from datetime import datetime

class ClockUseCases(Protocol):
    """Coordina aquesta capacitat sense importar adaptadors ni APIs gràfiques."""
    def set_time(self, instant_utc: datetime) -> tuple[ApplicationEvent, ...]: ...
    def set_rate(self, rate: float) -> tuple[ApplicationEvent, ...]: ...
    def tick(self, elapsed_seconds: float) -> tuple[ApplicationEvent, ...]: ...
