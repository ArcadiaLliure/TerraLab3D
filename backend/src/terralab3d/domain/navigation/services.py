"""Contractes de servei purs per a la capacitat navegació."""


from typing import Protocol
from .models import CameraNavigationState, CameraPose

class CameraIntentModel(Protocol):
    """Aplica la intenció de càmera sense dependre del renderer."""
    def replace_pose(self, state: CameraNavigationState, pose: CameraPose) -> CameraNavigationState: ...
    def track_target(self, state: CameraNavigationState, target_id: str) -> CameraNavigationState: ...
    def release_tracking(self, state: CameraNavigationState) -> CameraNavigationState: ...
