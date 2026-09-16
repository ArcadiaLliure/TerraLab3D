"""Models immutables de les mesures angulars sobre l'esfera celeste."""


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
    tracking: bool = True
    fixed_quaternion_xyzw: tuple[float, float, float, float] | None = None

@dataclass(frozen=True, slots=True)
class MeasurementGeometry:
    paths: tuple[tuple[HorizontalCoordinate, ...], ...]
    label: str
    anchor: HorizontalCoordinate


@dataclass(frozen=True, slots=True)
class MeasurementDocument:
    schema_version: int = 1
    revision: int = 0
    measurements: tuple[Measurement, ...] = ()
    selected_measurement_id: MeasurementId | None = None
    tracking_enabled: bool = True
