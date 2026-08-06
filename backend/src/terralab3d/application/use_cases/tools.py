"""Contractes de casos d’ús de l’aplicació."""
from typing import Protocol
from terralab3d.application.events import ApplicationEvent
from terralab3d.domain.measurements.models import MeasurementKind

class ToolUseCases(Protocol):
    """Coordina aquesta capacitat sense importar adaptadors ni APIs gràfiques."""
    def start_measurement(self, kind: MeasurementKind) -> tuple[ApplicationEvent, ...]: ...
    def apply_constellation_edit(self, command_id: str) -> tuple[ApplicationEvent, ...]: ...
