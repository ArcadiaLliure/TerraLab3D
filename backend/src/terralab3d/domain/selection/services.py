"""Contractes de servei purs per a la capacitat selecció."""


from typing import Protocol
from .models import PickResult, SelectionState

class SelectionModel(Protocol):
    """Aplica resultats de picking vigents a un estat de selecció immutable."""
    def apply_pick(self, state: SelectionState, result: PickResult, *, current_generation: int) -> SelectionState: ...
