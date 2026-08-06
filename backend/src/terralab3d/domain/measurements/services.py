"""Contractes de servei purs per a la capacitat mesures."""


from typing import Protocol
from .models import Measurement, MeasurementGeometry

class MeasurementGeometryModel(Protocol):
    """Construeix geometria esfèrica i etiquetes per a entitats de mesura."""
    def geometry(self, measurement: Measurement) -> MeasurementGeometry: ...
