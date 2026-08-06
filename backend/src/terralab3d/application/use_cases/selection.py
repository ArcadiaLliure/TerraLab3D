"""Contractes de casos d’ús de l’aplicació."""
from typing import Protocol
from terralab3d.application.events import ApplicationEvent
from terralab3d.domain.selection.models import PickResult

class SelectionUseCases(Protocol):
    """Coordina aquesta capacitat sense importar adaptadors ni APIs gràfiques."""
    def apply_pick(self, result: PickResult) -> tuple[ApplicationEvent, ...]: ...
    def clear(self) -> tuple[ApplicationEvent, ...]: ...
