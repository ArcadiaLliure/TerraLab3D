"""Contractes de casos d’ús de l’aplicació."""
from typing import Protocol
from terralab3d.application.events import ApplicationEvent
from terralab3d.domain.observer.models import GeoLocation

class ObserverUseCases(Protocol):
    """Coordina aquesta capacitat sense importar adaptadors ni APIs gràfiques."""
    def set_location(self, location: GeoLocation, height_offset_m: float) -> tuple[ApplicationEvent, ...]: ...
    def resolve_elevation(self, location: GeoLocation) -> tuple[ApplicationEvent, ...]: ...
