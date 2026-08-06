"""Contractes de càlcul científic pur per a eclipsis i ocultacions."""

from typing import Protocol
from datetime import datetime
from terralab3d.domain.eclipses.models import EclipseEvent, EclipseInstantState

class EclipseGeometryCalculator(Protocol):
    """Defineix els càlculs purs de eclipsis i ocultacions sense I/O ni renderitzat."""
    def instant_state(self, sun_angular_radius_deg: float, moon_angular_radius_deg: float, separation_deg: float) -> EclipseInstantState: ...
    def find_contacts(self, start_utc: datetime, end_utc: datetime) -> EclipseEvent | None: ...
