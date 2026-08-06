"""Contractes de càlcul científic pur per a temps astronòmic i simulació temporal."""

from typing import Protocol
from datetime import datetime

class AstronomicalTimescaleCalculator(Protocol):
    """Defineix els càlculs purs de temps astronòmic i simulació temporal sense I/O ni renderitzat."""
    def julian_day(self, instant_utc: datetime) -> float: ...
    def julian_centuries(self, instant_utc: datetime) -> float: ...
    def local_sidereal_angle_deg(self, instant_utc: datetime, longitude_deg: float) -> float: ...
