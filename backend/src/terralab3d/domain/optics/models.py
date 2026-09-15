"""Models científics dels modes d'observació i dels instruments òptics."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class ObservationMode(str, Enum):
    EYE = "eye"
    CAMERA = "camera"
    TELESCOPE = "telescope"


class InstrumentKind(str, Enum):
    TELESCOPE = "telescope"
    CAMERA = "camera"


class FramingShape(str, Enum):
    CIRCLE = "circle"
    RECTANGLE = "rectangle"


@dataclass(frozen=True, slots=True)
class SensorFormat:
    key: str
    width_mm: float
    height_mm: float
    resolution_width_px: int | None = None
    resolution_height_px: int | None = None
    square_pixels: bool = True
    pixel_pitch_um: float | None = None
    pixel_pitch_x_um: float | None = None
    pixel_pitch_y_um: float | None = None


@dataclass(frozen=True, slots=True)
class CameraProfile:
    profile_id: str
    name: str
    sensor: SensorFormat
    built_in: bool = False


@dataclass(frozen=True, slots=True)
class CameraCaptureSettings:
    selected_profile_id: str
    focal_length_mm: float = 250.0
    f_number: float = 4.0
    iso: float = 800.0
    exposure_seconds: float = 2.0
    tracking_enabled: bool = False
    optical_transmission: float | None = None


@dataclass(frozen=True, slots=True)
class TelescopeSettings:
    focal_length_mm: float = 400.0
    aperture_diameter_mm: float = 80.0
    eyepiece_focal_length_mm: float = 20.0
    eyepiece_afov_deg: float = 50.0


@dataclass(frozen=True, slots=True)
class OpticalInstrument:
    """Contracte anterior conservat per als consumidors de l'esquelet."""

    kind: InstrumentKind
    focal_length_mm: float
    aperture_diameter_mm: float | None
    f_number: float | None
    eyepiece_focal_length_mm: float | None
    sensor: SensorFormat | None


@dataclass(frozen=True, slots=True)
class ExposureSettings:
    iso: int
    exposure_seconds: float


@dataclass(frozen=True, slots=True)
class FieldOfView:
    width_deg: float
    height_deg: float
    shape: FramingShape
    diagonal_deg: float | None = None
    aspect_ratio: float | None = None
    solid_angle_sr: float | None = None


@dataclass(frozen=True, slots=True)
class OpticalMetrics:
    pixel_scale_x_arcsec: float | None = None
    pixel_scale_y_arcsec: float | None = None
    magnification: float | None = None
    exit_pupil_mm: float | None = None
    true_fov_deg: float | None = None


@dataclass(frozen=True, slots=True)
class PhotographicPreview:
    model_id: str
    estimated_limit_magnitude: float
    captured_photon_index: float
    iso_detection_gain_magnitude: float
    atmospheric_transmission: float
    total_transmission: float
    short_exposure_penalty_magnitude: float
    sky_penalty_magnitude: float


@dataclass(frozen=True, slots=True)
class DeepCatalogStatus:
    state: str = "idle"
    deep_query_revision: int = 0
    resident_magnitude_limit: float = 8.0
    selected_star_count: int = 0
    truncated: bool = False
    message: str | None = None


@dataclass(frozen=True, slots=True)
class ObservationSnapshot:
    schema_version: int
    observation_revision: int
    mode: ObservationMode
    camera_profiles: tuple[CameraProfile, ...]
    camera: CameraCaptureSettings
    telescope: TelescopeSettings
    field: FieldOfView | None
    metrics: OpticalMetrics
    photographic_preview: PhotographicPreview | None
    deep_catalog: DeepCatalogStatus
    warning: str | None = None
