"""Operacions incrementals de l’escena retinguda."""
from dataclasses import dataclass
from typing import TypeAlias
from .entities import SceneComponent, SceneEntity
from .ids import SceneEntityId, SceneGeneration, SceneResourceId
from .resources import SceneResourceDescriptor

@dataclass(frozen=True, slots=True)
class RegisterResource:
    descriptor: SceneResourceDescriptor

@dataclass(frozen=True, slots=True)
class UpdateResource:
    descriptor: SceneResourceDescriptor

@dataclass(frozen=True, slots=True)
class DisposeResource:
    resource_id: SceneResourceId
    expected_version: int

@dataclass(frozen=True, slots=True)
class CreateEntity:
    entity: SceneEntity

@dataclass(frozen=True, slots=True)
class ReplaceComponent:
    entity_id: SceneEntityId
    component: SceneComponent

@dataclass(frozen=True, slots=True)
class RemoveEntity:
    entity_id: SceneEntityId

SceneOperation: TypeAlias = (
    RegisterResource
    | UpdateResource
    | DisposeResource
    | CreateEntity
    | ReplaceComponent
    | RemoveEntity
)

@dataclass(frozen=True, slots=True)
class SceneDelta:
    base_generation: SceneGeneration
    generation: SceneGeneration
    operations: tuple[SceneOperation, ...]
