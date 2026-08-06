"""Serveis de domini per a eclipsis i ocultacions."""
from datetime import datetime
from typing import Protocol
from .models import EclipseEvent, EclipseInstantState

class EclipseModel(Protocol):
    """Resol l’estat instantani d’un esdeveniment d’eclipsi."""
    def resolve(self, event: EclipseEvent, instant_utc: datetime) -> EclipseInstantState: ...
