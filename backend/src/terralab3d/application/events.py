"""Esdeveniments tipats emesos per la capa d’aplicació."""
from dataclasses import dataclass
from typing import TypeAlias
from terralab3d.domain.feedback.models import UserFacingIssue
from terralab3d.domain.layers.models import LayerId
from terralab3d.domain.resources.models import DatasetState
from terralab3d.domain.selection.models import SelectionState

@dataclass(frozen=True, slots=True)
class SessionChanged:
    revision: int

@dataclass(frozen=True, slots=True)
class LayerChanged:
    layer_id: LayerId
    visible: bool

@dataclass(frozen=True, slots=True)
class SelectionChanged:
    state: SelectionState

@dataclass(frozen=True, slots=True)
class DatasetChanged:
    state: DatasetState

@dataclass(frozen=True, slots=True)
class OperationProgressed:
    operation_id: str
    progress_fraction: float | None
    message_key: str

@dataclass(frozen=True, slots=True)
class OperationFailed:
    operation_id: str
    issue: UserFacingIssue

@dataclass(frozen=True, slots=True)
class ResourcePublished:
    resource_id: str
    version: int

@dataclass(frozen=True, slots=True)
class SceneInvalidated:
    reason: str

ApplicationEvent: TypeAlias = (
    SessionChanged | LayerChanged | SelectionChanged | DatasetChanged |
    OperationProgressed | OperationFailed | ResourcePublished | SceneInvalidated
)
