"""Contractes de càlcul científic pur per a telescopi, ocular i geometria òptica."""

from typing import Protocol
from terralab3d.domain.optics.models import FieldOfView, OpticalInstrument

class OpticalGeometryCalculator(Protocol):
    """Defineix els càlculs purs de telescopi, ocular i geometria òptica sense I/O ni renderitzat."""
    def field_of_view(self, instrument: OpticalInstrument) -> FieldOfView: ...
    def magnification(self, instrument: OpticalInstrument) -> float | None: ...
    def exit_pupil_mm(self, instrument: OpticalInstrument) -> float | None: ...
