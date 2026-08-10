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
    CLUSTER_NEBULA = "cluster_nebula"
    STELLAR_ASSOCIATION = "stellar_association"
    OTHER = "other"

@dataclass(frozen=True, slots=True)
class DeepSkyObject:
    object_id: DeepSkyObjectId
    canonical_name: str
    aliases: tuple[str, ...]
    source_type: str
    visual_family: DeepSkyKind
    render_eligible: bool
    coordinate: EquatorialCoordinate
    major_axis_arcmin: float | None
    minor_axis_arcmin: float | None
    position_angle_deg: float | None
    v_magnitude: float | None
    b_magnitude: float | None
    surface_brightness: float | None
    hubble_type: str | None
    messier_number: str | None
    common_name: str | None
    flags: int
