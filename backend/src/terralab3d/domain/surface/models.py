"""Models de domini tipats per a la capacitat superfícies, ortofoto i cobertura categòrica."""


from dataclasses import dataclass
from enum import Enum
from terralab3d.domain.identifiers import ResourceId

class SurfaceSampleKind(str, Enum):
    RGB = "rgb"
    CATEGORICAL = "categorical"

@dataclass(frozen=True, slots=True)
class SurfaceSampleGrid:
    kind: SurfaceSampleKind
    width: int
    height: int
    value_buffer_key: str
    legend_id: str | None

@dataclass(frozen=True, slots=True)
class SurfaceMaterialDescriptor:
    resource_id: ResourceId
    version: int
    style_key: str
    texture_resource_id: ResourceId | None
