"""Models de domini tipats per a la capacitat cerca."""


from dataclasses import dataclass
from enum import Enum
from terralab3d.domain.geometry import EquatorialCoordinate

class SearchTargetKind(str, Enum):
    STAR = "star"
    BODY = "body"
    DEEP_SKY = "deep_sky"
    COORDINATE = "coordinate"

@dataclass(frozen=True, slots=True)
class SearchQuery:
    text: str
    kinds: frozenset[SearchTargetKind]
    limit: int = 20

@dataclass(frozen=True, slots=True)
class SearchResult:
    target_ref: str
    kind: SearchTargetKind
    display_name: str
    score: float
    availability: str = "available"
    coordinate_snapshot: EquatorialCoordinate | None = None
    resource_id: str | None = None
    matched_alias: str | None = None

