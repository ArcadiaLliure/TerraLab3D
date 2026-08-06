"""Contractes de càlcul científic pur per a mesures angulars i formes."""

from typing import Protocol
from terralab3d.domain.geometry import HorizontalCoordinate
from terralab3d.domain.measurements.models import Measurement, MeasurementGeometry

class MeasurementCalculator(Protocol):
    """Defineix els càlculs purs de mesures angulars i formes sense I/O ni renderitzat."""
    def angular_distance_deg(self, a: HorizontalCoordinate, b: HorizontalCoordinate) -> float: ...
    def geometry(self, measurement: Measurement) -> MeasurementGeometry: ...
