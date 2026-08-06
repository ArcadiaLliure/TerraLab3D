"""Contractes de casos d’ús de l’aplicació."""
from typing import Protocol
from terralab3d.application.events import ApplicationEvent
from terralab3d.domain.layers.models import LayerId

class LayerUseCases(Protocol):
    """Coordina aquesta capacitat sense importar adaptadors ni APIs gràfiques."""
    def set_visibility(self, layer_id: LayerId, visible: bool) -> tuple[ApplicationEvent, ...]: ...
