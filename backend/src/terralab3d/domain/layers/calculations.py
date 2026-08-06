"""Contractes de càlcul científic pur per a capes i visibilitat."""

from typing import Protocol
from terralab3d.domain.layers.models import LayerId, LayerState

class LayerDependencyCalculator(Protocol):
    """Defineix els càlculs purs de capes i visibilitat sense I/O ni renderitzat."""
    def can_enable(self, layer_id: LayerId, state: LayerState) -> bool: ...
