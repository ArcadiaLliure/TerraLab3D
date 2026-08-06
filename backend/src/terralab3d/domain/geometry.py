"""DTO escalars, vectorials i de coordenades independents del renderer."""
from dataclasses import dataclass

@dataclass(frozen=True, slots=True)
class EquatorialCoordinate:
    right_ascension_deg: float
    declination_deg: float

@dataclass(frozen=True, slots=True)
class HorizontalCoordinate:
    altitude_deg: float
    azimuth_deg: float

@dataclass(frozen=True, slots=True)
class EclipticCoordinate:
    longitude_deg: float
    latitude_deg: float

@dataclass(frozen=True, slots=True)
class GalacticCoordinate:
    longitude_deg: float
    latitude_deg: float

@dataclass(frozen=True, slots=True)
class CartesianDirection:
    x: float
    y: float
    z: float

@dataclass(frozen=True, slots=True)
class WorldPoint:
    x_m: float
    y_m: float
    z_m: float

@dataclass(frozen=True, slots=True)
class AngularExtent:
    width_deg: float
    height_deg: float

@dataclass(frozen=True, slots=True)
class ScreenPoint:
    x_px: float
    y_px: float
