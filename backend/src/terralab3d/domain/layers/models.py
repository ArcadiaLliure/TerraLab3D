"""Models de domini tipats per a la capacitat capes."""


from dataclasses import dataclass
from enum import Enum

class LayerId(str, Enum):
    ATMOSPHERE = "atmosphere"
    STARS = "stars"
    SOLAR_SYSTEM = "solar_system"
    MILKY_WAY = "milky_way"
    PLANCK_DUST = "planck_dust"
    DEEP_SKY = "deep_sky"
    WEATHER = "weather"
    HORIZON = "horizon"
    TERRAIN = "terrain"
    SURFACE = "surface"
    CONSTELLATIONS = "constellations"
    MEASUREMENTS = "measurements"
    SCOPE = "scope"

@dataclass(frozen=True, slots=True)
class LayerState:
    visible: frozenset[LayerId]
    available: frozenset[LayerId]
