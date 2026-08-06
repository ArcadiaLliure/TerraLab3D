"""Models de domini tipats per a la capacitat òptica."""


from dataclasses import dataclass
from enum import Enum

class InstrumentKind(str, Enum):
    TELESCOPE = "telescope"
    CAMERA = "camera"

class FramingShape(str, Enum):
    CIRCLE = "circle"
    RECTANGLE = "rectangle"

@dataclass(frozen=True, slots=True)
class SensorFormat:
    key: str
    width_mm: float
    height_mm: float

@dataclass(frozen=True, slots=True)
class OpticalInstrument:
    kind: InstrumentKind
    focal_length_mm: float
    aperture_diameter_mm: float | None
    f_number: float | None
    eyepiece_focal_length_mm: float | None
    sensor: SensorFormat | None

@dataclass(frozen=True, slots=True)
class ExposureSettings:
    iso: int
    exposure_seconds: float

@dataclass(frozen=True, slots=True)
class FieldOfView:
    width_deg: float
    height_deg: float
    shape: FramingShape
