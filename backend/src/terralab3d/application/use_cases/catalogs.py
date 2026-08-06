"""Contractes de casos d’ús de l’aplicació."""
from typing import Protocol
from terralab3d.application.events import ApplicationEvent
from terralab3d.domain.stars.models import StarCatalogQuery

class CatalogUseCases(Protocol):
    """Coordina aquesta capacitat sense importar adaptadors ni APIs gràfiques."""
    def load_stars(self, query: StarCatalogQuery) -> tuple[ApplicationEvent, ...]: ...
    def load_deep_sky(self, query_text: str) -> tuple[ApplicationEvent, ...]: ...
