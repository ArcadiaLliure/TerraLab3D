"""Contractes de servei purs per a la capacitat coordenades."""


from typing import Protocol, Sequence
from terralab3d.domain.geometry import CartesianDirection, EquatorialCoordinate, HorizontalCoordinate
from .models import CoordinateTransformRequest, CoordinateTransformResult

class CoordinateTransformService(Protocol):
    """Transforma coordenades celestes sense projecció de pantalla."""
    def equatorial_to_horizontal(self, request: CoordinateTransformRequest) -> CoordinateTransformResult: ...
    def horizontal_to_direction(self, coordinate: HorizontalCoordinate) -> CartesianDirection: ...
    def transform_many(self, coordinates: Sequence[EquatorialCoordinate], *, observer_latitude_deg: float, observer_longitude_deg: float, julian_day: float) -> Sequence[HorizontalCoordinate]: ...
