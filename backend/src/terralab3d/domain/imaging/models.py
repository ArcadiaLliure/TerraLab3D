"""Models de domini tipats per a la capacitat simulació fotogràfica."""


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
