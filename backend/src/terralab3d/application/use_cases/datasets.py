"""Contractes de casos d’ús de l’aplicació."""
from typing import Protocol
from terralab3d.application.events import ApplicationEvent

class DatasetUseCases(Protocol):
    """Coordina aquesta capacitat sense importar adaptadors ni APIs gràfiques."""
    def install(self, dataset_id: str) -> tuple[ApplicationEvent, ...]: ...
    def cancel(self, operation_id: str) -> tuple[ApplicationEvent, ...]: ...
