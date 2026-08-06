"""Models de domini tipats per a la capacitat navegació."""


from dataclasses import dataclass
from enum import Enum

class TrackingMode(str, Enum):
    FREE = "free"
    CELESTIAL_TARGET = "celestial_target"
    EQUATORIAL_COORDINATE = "equatorial_coordinate"

@dataclass(frozen=True, slots=True)
class CameraPose:
    azimuth_deg: float
    altitude_deg: float
    horizontal_fov_deg: float
    roll_deg: float = 0.0

@dataclass(frozen=True, slots=True)
class CameraNavigationState:
    pose: CameraPose
    tracking_mode: TrackingMode
    target_id: str | None = None
