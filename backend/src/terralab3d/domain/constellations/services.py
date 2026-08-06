"""Contractes de servei purs per a la capacitat constel·lacions."""


from typing import Protocol
from .models import ConstellationNode, EditableConstellation

class ConstellationEditingModel(Protocol):
    """Aplica operacions d’edició pures a documents de constel·lació."""
    def append_node(self, constellation: EditableConstellation, node: ConstellationNode) -> EditableConstellation: ...
    def rename(self, constellation: EditableConstellation, name: str) -> EditableConstellation: ...
    def remove_node(self, constellation: EditableConstellation, node_index: int) -> EditableConstellation: ...
