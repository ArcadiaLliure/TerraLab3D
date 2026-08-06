"""Port per publicar actualitzacions incrementals d’escena."""
from typing import Protocol
from terralab3d.scene.deltas import SceneDelta

class SceneOutputPort(Protocol):
    def publish(self, delta: SceneDelta) -> None: ...
