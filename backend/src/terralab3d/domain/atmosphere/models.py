"""Models de domini tipats per a la capacitat atmosfera.

AtmosphereState: estat atmosfèric complet per al snapshot del cel.
La turbidity és configurable (default 2.5, preparada per weather futur).
"""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class AtmosphereState:
    """Estat atmosfèric per al snapshot del cel.

    Atributs:
        turbidity: Terbolesa atmosfèrica (2.0 = clar, 10.0 = boirós). Default 2.5.
        extinction_coefficient: Coeficient d'extinció en mag/airmass. Default 0.25.
            Referència: 0.15 (excel·lent) a 0.45 (pobre).
        horizon_haze: Factor de boira a l'horitzó [0, 1]. Default 0.3.
        natural_sky_brightness: Brillantor natural del cel nocturn normalitzada [0, 1].
            Separada de la contaminació lumínica artificial.
    """
    turbidity: float = 2.5
    extinction_coefficient: float = 0.25
    horizon_haze: float = 0.3
    natural_sky_brightness: float = 0.05


@dataclass(frozen=True, slots=True)
class AtmosphereParameters:
    """Paràmetres atmosfèrics derivats (compatibilitat amb codi existent)."""
    sun_altitude_deg: float
    turbidity: float
    humidity_fraction: float
    extinction_coefficient: float
    cloud_cover_fraction: float
    night_sky_luminance: float


@dataclass(frozen=True, slots=True)
class SkyAppearance:
    """Aparença visual derivada del cel."""
    zenith_luminance: float
    horizon_luminance: float
    star_extinction: float
    deep_sky_extinction: float
