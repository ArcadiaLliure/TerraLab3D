"""Models de domini tipats per a la capacitat atmosfera."""


from dataclasses import dataclass

@dataclass(frozen=True, slots=True)
class AtmosphereParameters:
    sun_altitude_deg: float
    turbidity: float
    humidity_fraction: float
    extinction_coefficient: float
    cloud_cover_fraction: float
    night_sky_luminance: float

@dataclass(frozen=True, slots=True)
class SkyAppearance:
    zenith_luminance: float
    horizon_luminance: float
    star_extinction: float
    deep_sky_extinction: float
