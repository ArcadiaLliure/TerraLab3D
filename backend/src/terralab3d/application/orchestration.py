"""Contractes d’orquestració de casos d’ús."""

from typing import Protocol

from terralab3d.scene.deltas import SceneDelta
from terralab3d.scene.state import SceneState
from .session import ApplicationSession


class SceneOrchestrator(Protocol):
    """Tradueix l’estat autoritatiu a actualitzacions incrementals d’escena."""

    def reconcile(self, session: ApplicationSession, previous: SceneState) -> SceneDelta: ...
