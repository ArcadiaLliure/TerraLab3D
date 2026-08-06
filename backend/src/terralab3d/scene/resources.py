"""Descriptors persistents de recursos de l’escena."""
from dataclasses import dataclass
from enum import Enum
from .ids import SceneResourceId

class ResourceKind(str, Enum):
    BUFFER = "buffer"
    INDEX_BUFFER = "index_buffer"
    TEXTURE_2D = "texture_2d"
    TEXTURE_CUBE = "texture_cube"
    TEXTURE_ARRAY = "texture_array"
    FONT_ATLAS = "font_atlas"
    MATERIAL_PARAMETERS = "material_parameters"

class ResourceLifetime(str, Enum):
    STATIC = "static"
    SESSION = "session"
    VIEW = "view"
    TRANSIENT = "transient"

@dataclass(frozen=True, slots=True)
class BufferSlice:
    byte_offset: int
    byte_length: int
    component_type: str
    component_count: int
    semantic: str

@dataclass(frozen=True, slots=True)
class SceneResourceDescriptor:
    resource_id: SceneResourceId
    version: int
    kind: ResourceKind
    lifetime: ResourceLifetime
    owner_id: str
    content_key: str
    byte_length: int
    dependencies: tuple[SceneResourceId, ...] = ()
