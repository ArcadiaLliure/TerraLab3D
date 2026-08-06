"""Models de domini tipats per a la capacitat fons celeste, dia, nit i crepuscle."""


from dataclasses import dataclass
from terralab3d.domain.geometry import CartesianDirection

@dataclass(frozen=True, slots=True)
class SkyBackgroundState:
    sun_direction: CartesianDirection
    zenith_luminance: float
    horizon_luminance: float
    twilight_factor: float
    night_factor: float
