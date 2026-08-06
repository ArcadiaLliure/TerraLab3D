"""Contractes de càlcul científic pur per a càmera i navegació 360°."""

from typing import Protocol
from terralab3d.domain.geometry import EquatorialCoordinate
from terralab3d.domain.navigation.models import CameraPose

class NavigationConstraintCalculator(Protocol):
    """Defineix els càlculs purs de càmera i navegació 360° sense I/O ni renderitzat."""
    def clamp_pose(self, pose: CameraPose) -> CameraPose: ...
    def focus_pose(self, target: EquatorialCoordinate, current: CameraPose) -> CameraPose: ...
