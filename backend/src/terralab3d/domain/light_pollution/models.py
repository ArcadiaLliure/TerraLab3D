"""Models de domini tipats per a la capacitat contaminació lumínica."""


from dataclasses import dataclass
from enum import Enum

class LightPollutionMode(str, Enum):
    BORTLE = "bortle"
    MAGNITUDE = "magnitude"
    AUTOMATIC = "automatic"

@dataclass(frozen=True, slots=True)
class LightPollutionState:
    mode: LightPollutionMode
    bortle_class: float | None
    manual_magnitude_limit: float | None
    estimated_sky_brightness: float | None

@dataclass(frozen=True, slots=True)
class VisibilityLimit:
    naked_eye_magnitude: float
    deep_sky_contrast: float
    galactic_contrast: float
