"""Models immutables del catàleg i els documents de constel·lacions."""

from dataclasses import dataclass

from terralab3d.domain.geometry import EquatorialCoordinate
from terralab3d.domain.identifiers import ConstellationId


@dataclass(frozen=True, slots=True)
class ConstellationVisualComponent:
    component_id: str
    source_name: str
    rank: int
    strokes: tuple[tuple[EquatorialCoordinate, ...], ...]


@dataclass(frozen=True, slots=True)
class ConstellationCatalogEntry:
    constellation_id: ConstellationId
    name: str
    center: EquatorialCoordinate
    angular_radius_deg: float
    visual_components: tuple[ConstellationVisualComponent, ...]
    frame: str = "ICRS"


@dataclass(frozen=True, slots=True)
class ConstellationCatalog:
    catalog_version: str
    source_frame: str
    frame: str
    entries: tuple[ConstellationCatalogEntry, ...]


@dataclass(frozen=True, slots=True)
class ConstellationNode:
    node_id: str
    coordinate: EquatorialCoordinate
    source_id: str | None = None
    star_name: str | None = None
    resource_id: str | None = None
    resource_version: str | None = None
    catalog_index: int | None = None
    starts_new_stroke: bool = False


@dataclass(frozen=True, slots=True)
class EditableConstellation:
    constellation_id: ConstellationId
    name: str
    nodes: tuple[ConstellationNode, ...] = ()


@dataclass(frozen=True, slots=True)
class ConstellationDocument:
    schema_version: int = 1
    revision: int = 0
    constellations: tuple[EditableConstellation, ...] = ()
