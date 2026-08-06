"""Models de domini tipats per a la capacitat cel profund."""


from dataclasses import dataclass
from enum import Enum
from terralab3d.domain.geometry import EquatorialCoordinate
from terralab3d.domain.identifiers import DeepSkyObjectId

class DeepSkyKind(str, Enum):
    GALAXY = "galaxy"
    NEBULA = "nebula"
    OPEN_CLUSTER = "open_cluster"
    GLOBULAR_CLUSTER = "globular_cluster"
    OTHER = "other"

@dataclass(frozen=True, slots=True)
class DeepSkyObject:
    object_id: DeepSkyObjectId
    canonical_name: str
    kind: DeepSkyKind
    coordinate: EquatorialCoordinate
    major_axis_deg: float | None
    minor_axis_deg: float | None
    position_angle_deg: float | None
    apparent_magnitude: float | None
