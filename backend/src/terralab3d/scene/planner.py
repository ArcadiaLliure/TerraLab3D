"""Contracte de reconciliació de l’escena."""
from typing import Protocol
from terralab3d.application.session import ApplicationSession
from .deltas import SceneDelta
from .state import SceneState

class SceneUpdatePlanner(Protocol):
    """Produeix el delta vàlid més petit per a una revisió de sessió."""
    def reconcile(self, session: ApplicationSession, previous: SceneState) -> SceneDelta: ...
