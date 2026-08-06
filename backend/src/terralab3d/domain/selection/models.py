"""Models de domini tipats per a la capacitat selecció."""


from dataclasses import dataclass
from enum import Enum

class SelectionKind(str, Enum):
    STAR = "star"
    BODY = "body"
    DEEP_SKY = "deep_sky"
    TERRAIN = "terrain"
    CONSTELLATION = "constellation"
    MEASUREMENT = "measurement"

@dataclass(frozen=True, slots=True)
class PickResult:
    request_id: str
    scene_generation: int
    hit: bool
    target_id: str | None
    target_kind: SelectionKind | None
    distance: float | None
    world_x: float | None
    world_y: float | None
    world_z: float | None

@dataclass(frozen=True, slots=True)
class SelectionState:
    selected_id: str | None
    selected_kind: SelectionKind | None
    hovered_id: str | None
