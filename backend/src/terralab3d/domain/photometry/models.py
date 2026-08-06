"""Models de domini tipats per a la capacitat fotometria astronòmica compartida."""


from dataclasses import dataclass

@dataclass(frozen=True, slots=True)
class PhotometricSample:
    apparent_magnitude: float
    relative_flux: float
    color_index: float | None

@dataclass(frozen=True, slots=True)
class DetectionThreshold:
    limiting_magnitude: float
    minimum_contrast: float
