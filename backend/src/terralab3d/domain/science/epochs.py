"""Èpoques, escales temporals i convencions de referència astronòmica."""
from dataclasses import dataclass
from datetime import datetime

@dataclass(frozen=True, slots=True)
class AstronomicalEpoch:
    name: str
    instant_utc: datetime
    timescale: str
