"""Models de domini tipats per a la capacitat constel·lacions."""


from dataclasses import dataclass
from terralab3d.domain.geometry import EquatorialCoordinate
from terralab3d.domain.identifiers import ConstellationId, StarId

@dataclass(frozen=True, slots=True)
class ConstellationNode:
    coordinate: EquatorialCoordinate
    star_id: StarId | None
    star_name: str | None
    starts_new_stroke: bool = False

@dataclass(frozen=True, slots=True)
class EditableConstellation:
    constellation_id: ConstellationId
    name: str
    nodes: tuple[ConstellationNode, ...]
