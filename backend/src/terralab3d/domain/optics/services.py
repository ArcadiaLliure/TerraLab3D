"""Contractes de servei purs per a la capacitat òptica."""


from typing import Protocol
from .models import ExposureSettings, FieldOfView, FramingShape, OpticalInstrument

class OpticsModel(Protocol):
    """Resol enquadrament i guany instrumental sense dibuixar la màscara de scope."""
    def field_of_view(self, instrument: OpticalInstrument, *, shape: FramingShape, aspect_ratio_override: float | None = None) -> FieldOfView: ...
    def instrument_gain(self, instrument: OpticalInstrument, exposure: ExposureSettings) -> float: ...
