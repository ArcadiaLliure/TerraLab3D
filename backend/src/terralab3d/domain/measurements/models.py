"""Models de domini tipats per a la capacitat mesures."""


from dataclasses import dataclass
from enum import Enum
from terralab3d.domain.geometry import HorizontalCoordinate
from terralab3d.domain.identifiers import MeasurementId

class MeasurementKind(str, Enum):
    RULER = "ruler"
    SQUARE = "square"
    RECTANGLE = "rectangle"
    CIRCLE = "circle"

@dataclass(frozen=True, slots=True)
class Measurement:
    measurement_id: MeasurementId
    kind: MeasurementKind
    start: HorizontalCoordinate
    end: HorizontalCoordinate
    rotation_deg: float = 0.0

@dataclass(frozen=True, slots=True)
class MeasurementGeometry:
    paths: tuple[tuple[HorizontalCoordinate, ...], ...]
    label: str
    anchor: HorizontalCoordinate
