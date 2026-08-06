"""Snapshot immutable de l’escena retinguda utilitzat per reconciliar."""
from dataclasses import dataclass
from .entities import SceneEntity
from .ids import SceneGeneration
from .resources import SceneResourceDescriptor

@dataclass(frozen=True, slots=True)
class SceneState:
    generation: SceneGeneration
    entities: tuple[SceneEntity, ...]
    resources: tuple[SceneResourceDescriptor, ...]
