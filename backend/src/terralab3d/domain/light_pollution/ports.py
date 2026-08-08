"""Port per a estimació geogràfica automàtica de contaminació lumínica.

En el futur, l'adaptador real llegirà dades DVNL/SQM des del raster
georeferenciat. Ara l'adaptador placeholder retorna 'unavailable'.
"""

from __future__ import annotations

from typing import Protocol
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class LightPollutionEstimate:
    """Resultat d'una estimació geogràfica de contaminació lumínica.

    Atributs:
        sqm_zenith: Brillantor del cel en mag/arcsec² o None.
        bortle_equivalent: Classe Bortle equivalent o None.
        source: Origen de l'estimació: 'dataset', 'fallback', 'unavailable'.
    """
    sqm_zenith: float | None = None
    bortle_equivalent: float | None = None
    source: str = "unavailable"


class LightPollutionEstimatePort(Protocol):
    """Port per a estimació automàtica de contaminació lumínica.

    L'adaptador real (futur Pas 23) consultarà el raster DVNL/SQM.
    L'adaptador placeholder retorna 'unavailable'.
    """

    def estimate(
        self,
        latitude_deg: float,
        longitude_deg: float,
        *,
        elevation_m: float = 0.0,
    ) -> LightPollutionEstimate:
        """Estima la contaminació lumínica per a una ubicació geogràfica.

        Si no hi ha dades disponibles, retorna source='unavailable'.
        """
        ...


class UnavailableLightPollutionEstimator:
    """Adaptador placeholder que sempre retorna 'unavailable'.

    S'usarà fins que s'integri el raster DVNL/SQM al Pas 23.
    """

    def estimate(
        self,
        latitude_deg: float,
        longitude_deg: float,
        *,
        elevation_m: float = 0.0,
    ) -> LightPollutionEstimate:
        return LightPollutionEstimate(
            sqm_zenith=None,
            bortle_equivalent=None,
            source="unavailable",
        )
