"""Models de domini tipats per a la capacitat sistema solar."""


from dataclasses import dataclass
from enum import Enum
from terralab3d.domain.geometry import EquatorialCoordinate, HorizontalCoordinate
from terralab3d.domain.identifiers import CelestialBodyId

class BodyKind(str, Enum):
    SUN = "sun"
    MOON = "moon"
    PLANET = "planet"

@dataclass(frozen=True, slots=True)
class ApparentBodyState:
    body_id: CelestialBodyId
    kind: BodyKind
    equatorial: EquatorialCoordinate
    horizontal: HorizontalCoordinate
    angular_diameter_deg: float
    illuminated_fraction: float
    apparent_magnitude: float

@dataclass(frozen=True, slots=True)
class EclipseState:
    solar_obscuration_fraction: float
    lunar_shadow_fraction: float
