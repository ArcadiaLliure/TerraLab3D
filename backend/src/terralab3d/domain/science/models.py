"""Models de domini tipats per a la capacitat fonaments científics compartits."""


from dataclasses import dataclass
from enum import Enum

class AngleUnit(str, Enum):
    DEGREES = "degrees"
    RADIANS = "radians"

@dataclass(frozen=True, slots=True)
class ScientificTolerance:
    absolute: float
    relative: float

@dataclass(frozen=True, slots=True)
class ScientificComputationContext:
    reference_epoch: str
    tolerance: ScientificTolerance
    precision_profile: str
