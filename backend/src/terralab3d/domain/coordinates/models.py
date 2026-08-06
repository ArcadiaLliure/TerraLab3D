"""Models de domini tipats per a la capacitat coordenades."""


from dataclasses import dataclass
from terralab3d.domain.geometry import EquatorialCoordinate, HorizontalCoordinate

@dataclass(frozen=True, slots=True)
class CoordinateTransformRequest:
    equatorial: EquatorialCoordinate
    observer_latitude_deg: float
    observer_longitude_deg: float
    julian_day: float

@dataclass(frozen=True, slots=True)
class CoordinateTransformResult:
    horizontal: HorizontalCoordinate
    local_sidereal_deg: float
