"""Models de domini tipats per a la capacitat clima."""


from dataclasses import dataclass
from enum import Enum

class PrecipitationKind(str, Enum):
    NONE = "none"
    RAIN = "rain"
    SNOW = "snow"

class ClimateSource(str, Enum):
    REMOTE = "remote"
    FALLBACK = "fallback"

@dataclass(frozen=True, slots=True)
class ClimateState:
    cloud_cover_fraction: float
    humidity_fraction: float | None
    visibility_km: float | None
    precipitation: PrecipitationKind
    precipitation_intensity: float
    source: ClimateSource
