"""Serveis de domini per a la simulació fotogràfica."""
from typing import Protocol
from .models import ImagingSession, ImagingSignalEstimate

class ExposurePreviewModel(Protocol):
    """Compon una estimació de captura sense renderitzar una imatge."""
    def preview(self, session: ImagingSession, *, relative_flux: float, sky_flux: float) -> ImagingSignalEstimate: ...
