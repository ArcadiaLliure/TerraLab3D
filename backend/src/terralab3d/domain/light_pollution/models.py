"""Models de domini tipats per a contaminació lumínica.

Modes:
    AUTOMATIC: Usa dades geogràfiques reals (DVNL/SQM) si disponibles.
    BORTLE: L'usuari defineix la classe Bortle (1-9).
    MAGNITUDE: L'usuari defineix la magnitud límit zenital directament.

Relació canònica Bortle↔magnitud (paritat TerraLab):
    m_lim_zenith = 7.6 - 0.5 * (Bortle - 1)
    Bortle 1 → 7.6 mag (cel excel·lent)
    Bortle 9 → 3.6 mag (centre urbà)

Aquesta relació és empírica i aproximada, NO una equivalència exacta.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class LightPollutionMode(str, Enum):
    """Mode de contaminació lumínica."""
    AUTOMATIC = "automatic"
    BORTLE = "bortle"
    MAGNITUDE = "magnitude"


class LightPollutionSource(str, Enum):
    """Font de les dades de contaminació lumínica."""
    DATASET = "dataset"
    MANUAL_BORTLE = "manual_bortle"
    MANUAL_MAGNITUDE = "manual_magnitude"
    FALLBACK = "fallback"
    UNAVAILABLE = "unavailable"


@dataclass(frozen=True, slots=True)
class LightPollutionState:
    """Estat complet de contaminació lumínica.

    Atributs:
        enabled: Si la contaminació lumínica està activada.
        mode: Mode actiu (automatic/bortle/magnitude).
        source: Font de les dades.
        bortle_class: Classe Bortle efectiva [1-9], o None si no aplica.
        sqm_zenith: Brillantor del cel en mag/arcsec² (SQM zenital), o None.
        configured_magnitude_limit: Magnitud límit configurada manualment, o None.
        zenith_magnitude_limit: Magnitud límit zenital efectiva resultant.
        artificial_sky_brightness: Brillantor artificial normalitzada [0, 1].
    """
    enabled: bool = True
    mode: LightPollutionMode = LightPollutionMode.BORTLE
    source: LightPollutionSource = LightPollutionSource.MANUAL_BORTLE
    bortle_class: float | None = 4.0
    sqm_zenith: float | None = None
    configured_magnitude_limit: float | None = None
    zenith_magnitude_limit: float = 6.1
    artificial_sky_brightness: float = 0.15


@dataclass(frozen=True, slots=True)
class LightPollutionEstimate:
    """Resultat d'una estimació automàtica de contaminació lumínica.

    Retornat pel port d'estimació geogràfica.
    """
    sqm_zenith: float | None = None
    bortle_equivalent: float | None = None
    source: str = "unavailable"


@dataclass(frozen=True, slots=True)
class VisibilityLimit:
    """Límits de visibilitat derivats de la contaminació lumínica."""
    naked_eye_magnitude: float
    deep_sky_contrast: float
    galactic_contrast: float
