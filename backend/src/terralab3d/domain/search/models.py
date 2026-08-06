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
    target_id: str
    kind: SearchTargetKind
    display_name: str
    coordinate: EquatorialCoordinate
    score: float
