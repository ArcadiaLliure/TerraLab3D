"""Port d'atmosfera; el kernel només rep el camp immutable ja resolt."""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from terralab3d.domain.light_pollution.optical_field import OpticalField, TileBounds
from terralab3d.domain.light_pollution.source_model import GeodeticPosition


@dataclass(frozen=True, slots=True)
class OpticalTileSpec:
    tile_id: str
    version: str
    bounds: TileBounds

    def __post_init__(self) -> None:
        if not self.tile_id or not self.version:
            raise ValueError("Definició de tile sense identitat/versió")


@dataclass(frozen=True, slots=True)
class OpticalFieldRequest:
    origin: GeodeticPosition
    time_utc: datetime
    tiles: tuple[OpticalTileSpec, ...]
    top_m: float = 10000.0
    vertical_step_m: float = 100.0
    radius_m: float = 6371008.8

    def __post_init__(self) -> None:
        if (
            not self.tiles
            or len({t.tile_id for t in self.tiles}) != len(self.tiles)
            or self.time_utc.tzinfo is None
            or self.time_utc.utcoffset() is None
            or any(
                not math.isfinite(v) or v <= 0
                for v in (self.top_m, self.vertical_step_m, self.radius_m)
            )
        ):
            raise ValueError(
                "Petició atmosfèrica no finita, duplicada o sense zona temporal"
            )


class AtmosphericOpticsProvider(Protocol):
    def resolve(self, request: OpticalFieldRequest) -> OpticalField: ...
