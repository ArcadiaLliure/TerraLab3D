"""Models de domini tipats per a la capacitat temps astronòmic."""


from dataclasses import dataclass
from datetime import datetime
from enum import Enum

class ClockMode(str, Enum):
    PAUSED = "paused"
    REAL_TIME = "real_time"
    SIMULATED = "simulated"

@dataclass(frozen=True, slots=True)
class SimulationInstant:
    utc: datetime

@dataclass(frozen=True, slots=True)
class ClockState:
    instant: SimulationInstant
    mode: ClockMode
    rate: float
