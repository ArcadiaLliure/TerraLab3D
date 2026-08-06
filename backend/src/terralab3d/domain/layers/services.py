"""Contractes de servei purs per a la capacitat capes."""


from typing import Protocol
from .models import LayerId, LayerState

class LayerPolicy(Protocol):
    """Valida dependències i disponibilitat per a transicions de capes."""
    def set_visibility(self, state: LayerState, layer_id: LayerId, visible: bool) -> LayerState: ...
