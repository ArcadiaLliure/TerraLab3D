"""Contractes de càlcul científic pur per a coordenades i transformacions astronòmiques."""

from typing import Protocol
from terralab3d.domain.geometry import CartesianDirection, EquatorialCoordinate, HorizontalCoordinate
from terralab3d.domain.coordinates.models import CoordinateTransformRequest

class CelestialTransformCalculator(Protocol):
    """Defineix els càlculs purs de coordenades i transformacions astronòmiques sense I/O ni renderitzat."""
    def equatorial_to_horizontal(self, coordinate: EquatorialCoordinate, request: CoordinateTransformRequest) -> HorizontalCoordinate: ...
    def horizontal_to_equatorial(self, coordinate: HorizontalCoordinate, request: CoordinateTransformRequest) -> EquatorialCoordinate: ...
    def equatorial_to_direction(self, coordinate: EquatorialCoordinate) -> CartesianDirection: ...
