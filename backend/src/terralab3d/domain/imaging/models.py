"""Models de la previsualització fotogràfica estimada."""

from dataclasses import dataclass

from terralab3d.domain.optics.models import ExposureSettings, OpticalInstrument


@dataclass(frozen=True, slots=True)
class ImagingSession:
    instrument: OpticalInstrument
    exposure: ExposureSettings
    tracking_enabled: bool


@dataclass(frozen=True, slots=True)
class ImagingSignalEstimate:
    signal_electrons: float
    noise_electrons: float
    signal_to_noise_ratio: float
    saturated: bool


@dataclass(frozen=True, slots=True)
class PhotographicLimitingMagnitudeInputs:
    focal_length_mm: float
    f_number: float
    iso: float
    exposure_seconds: float
    atmospheric_loss_magnitude: float
    eye_limit_magnitude: float
    optical_transmission: float | None = None
