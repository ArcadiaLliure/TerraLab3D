"""Contracte del controlador d’aplicació."""

from typing import Protocol

from terralab3d.scene.deltas import SceneDelta
from .commands import ApplicationCommand
from .events import ApplicationEvent
from .session import ApplicationSession


class ApplicationController(Protocol):
    """Coordina casos d’ús sense importar adaptadors ni APIs gràfiques."""

    def handle(self, command: ApplicationCommand) -> tuple[ApplicationEvent, ...]: ...
    def session(self) -> ApplicationSession: ...
    def build_scene_delta(self) -> SceneDelta: ...
    def close(self) -> None: ...
