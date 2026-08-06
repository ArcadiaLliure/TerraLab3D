"""Contractes de casos d’ús de l’aplicació."""
from typing import Protocol
from terralab3d.application.events import ApplicationEvent
from terralab3d.domain.horizon.models import HorizonRequest
from terralab3d.domain.terrain.models import TerrainTileRequest

class TerrainUseCases(Protocol):
    """Coordina aquesta capacitat sense importar adaptadors ni APIs gràfiques."""
    def request_horizon(self, request: HorizonRequest) -> tuple[ApplicationEvent, ...]: ...
    def request_tile(self, request: TerrainTileRequest) -> tuple[ApplicationEvent, ...]: ...
