"""Serveis de domini per a les traces circumpolars."""
from typing import Protocol
from .models import StarTrailGeometry, StarTrailRequest

class StarTrailModel(Protocol):
    """Converteix una petició temporal en una descripció de traces persistent."""
    def describe(self, request: StarTrailRequest, *, version: int) -> StarTrailGeometry: ...
