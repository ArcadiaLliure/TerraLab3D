"""Models de domini tipats per a la capacitat estrelles."""


from dataclasses import dataclass
from terralab3d.domain.geometry import EquatorialCoordinate
from terralab3d.domain.identifiers import ResourceId, StarId

@dataclass(frozen=True, slots=True)
class StarRecord:
    star_id: StarId
    coordinate: EquatorialCoordinate
    magnitude: float
    color_index: float | None

@dataclass(frozen=True, slots=True)
class StarCatalogQuery:
    center: EquatorialCoordinate | None
    radius_deg: float | None
    magnitude_limit: float

@dataclass(frozen=True, slots=True)
class StarCatalogResource:
    resource_id: ResourceId
    version: int
    star_count: int
    position_buffer_key: str
    magnitude_buffer_key: str
    color_buffer_key: str
    identifier_buffer_key: str
