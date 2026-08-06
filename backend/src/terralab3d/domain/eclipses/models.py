"""Models de domini tipats per a la capacitat eclipsis i ocultacions."""


from dataclasses import dataclass
from datetime import datetime
from enum import Enum

class EclipseKind(str, Enum):
    SOLAR = "solar"
    LUNAR = "lunar"
    OCCULTATION = "occultation"

@dataclass(frozen=True, slots=True)
class EclipseContact:
    name: str
    instant_utc: datetime

@dataclass(frozen=True, slots=True)
class EclipseEvent:
    kind: EclipseKind
    contacts: tuple[EclipseContact, ...]
    maximum_utc: datetime

@dataclass(frozen=True, slots=True)
class EclipseInstantState:
    magnitude: float
    obscuration: float
    phase: str
