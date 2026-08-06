"""Contractes de casos d’ús de l’aplicació."""
from typing import Protocol
from terralab3d.application.events import ApplicationEvent
from terralab3d.domain.optics.models import ExposureSettings, OpticalInstrument

class OpticsUseCases(Protocol):
    """Coordina aquesta capacitat sense importar adaptadors ni APIs gràfiques."""
    def configure(self, instrument: OpticalInstrument, exposure: ExposureSettings) -> tuple[ApplicationEvent, ...]: ...
