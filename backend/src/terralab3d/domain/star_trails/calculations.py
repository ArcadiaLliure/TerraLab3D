"""Contractes de càlcul científic pur per a traces circumpolars."""

from typing import Protocol
from datetime import datetime
from terralab3d.domain.star_trails.models import StarTrailGeometry, StarTrailRequest

class StarTrailCalculator(Protocol):
    """Defineix els càlculs purs de traces circumpolars sense I/O ni renderitzat."""
    def sample_instants(self, request: StarTrailRequest) -> tuple[datetime, ...]: ...
    def describe_geometry(self, request: StarTrailRequest, version: int) -> StarTrailGeometry: ...
