"""Càlculs atmosfèrics purs: airmass, extinció i supressió de crepuscle.

Funcions pures sense I/O ni renderitzat.
El shader GLSL ha de reproduir-ne la semàntica.

Referència airmass Kasten-Young (1989):
    X(h) = 1 / (sin(h) + 0.50572 * (h + 6.07995)^(-1.6364))
    Estable a l'horitzó (h=0°): retorna ~38 en lloc d'infinit.
"""

from __future__ import annotations

import math
from typing import Protocol
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class AtmosphereState:
    """Estat atmosfèric complet per al snapshot del cel.

    Atributs:
        turbidity: Terbolesa atmosfèrica (2.0 = clar, 10.0 = boirós). Default 2.5.
        extinction_coefficient: Coeficient d'extinció en mag/airmass. Default 0.25.
        horizon_haze: Factor de boira a l'horitzó [0, 1]. Default 0.3.
        natural_sky_brightness: Brillantor natural del cel nocturn normalitzada [0, 1].
    """
    turbidity: float = 2.5
    extinction_coefficient: float = 0.25
    horizon_haze: float = 0.3
    natural_sky_brightness: float = 0.05


def airmass_from_altitude_deg(altitude_deg: float) -> float:
    """Calcula l'airmass amb la fórmula de Kasten-Young (1989).

    Estable a l'horitzó (0°) i per sota. NO genera NaN ni Infinity.

    Args:
        altitude_deg: Altitud de vista en graus [-90, +90].

    Returns:
        Airmass adimensional. Valor 1.0 al zenit, ~38 a l'horitzó.
    """
    # Clamp a un mínim de 0° per a l'airmass
    # (per sota de l'horitzó l'objecte no és visible, però retornem
    # un valor gran finit en lloc d'infinit)
    h = max(0.0, altitude_deg)

    if h >= 90.0:
        return 1.0

    # Kasten-Young: estable fins a h=0°
    h_rad = math.radians(h)
    sin_h = math.sin(h_rad)

    # La fórmula Kasten-Young usa graus per al terme correctiu
    denominator = sin_h + 0.50572 * math.pow(h + 6.07995, -1.6364)

    if denominator < 1e-10:
        return 40.0  # Valor màxim pràctic

    return 1.0 / denominator


def extinction_loss_mag(altitude_deg: float, coefficient: float = 0.25) -> float:
    """Calcula la pèrdua de magnitud per extinció atmosfèrica.

    m_loss = k * (X(h) - 1)

    On:
        k = coeficient d'extinció (mag/airmass), típicament 0.15-0.45
        X(h) = airmass a l'altitud h

    Args:
        altitude_deg: Altitud de vista en graus.
        coefficient: Coeficient d'extinció en mag/airmass.

    Returns:
        Pèrdua de magnitud (sempre >= 0).
    """
    X = airmass_from_altitude_deg(altitude_deg)
    return max(0.0, coefficient * (X - 1.0))


def twilight_suppression(sun_altitude_deg: float) -> float:
    """Factor de supressió d'estrelles per crepuscle [0, magnituds penalitzades].

    Quan el cel està il·luminat pel Sol (crepuscle/dia), les estrelles febles
    desapareixen progressivament.

    Returns:
        Penalització en magnituds per subtreure del límit de magnitud.
        0.0 = nit plena (cap supressió)
        ~7.0 = dia ple (pràcticament totes les estrelles suprimides)
    """
    if sun_altitude_deg <= -18.0:
        return 0.0
    if sun_altitude_deg >= 0.0:
        # Dia ple: supressió total
        # Les estrelles desapareixen completament
        return 7.0 + max(0.0, sun_altitude_deg) * 0.1

    # Crepuscle: transició suau
    # -18° → 0 mag supressió
    # 0° → 7.0 mag supressió
    t = (sun_altitude_deg + 18.0) / 18.0  # [0, 1]
    # Corba no lineal: la supressió accelera cap al final
    return 7.0 * (t * t * (3.0 - 2.0 * t))


def effective_star_limit(
    zenith_magnitude_limit: float,
    altitude_deg: float,
    extinction_coefficient: float = 0.25,
    twilight_suppression_mag: float = 0.0,
) -> float:
    """Calcula la magnitud límit efectiva per a una altitud de vista.

    m_lim(h) = m_lim_zenith - k * (X(h) - 1) - twilight_suppression

    Referència TerraLab:
        m_lim_h = m_lim_zenith - k * (1/sin(h) - 1)

    Millora: usem Kasten-Young en lloc de 1/sin(h) per estabilitat.

    Args:
        zenith_magnitude_limit: Magnitud límit al zenit.
        altitude_deg: Altitud de vista en graus.
        extinction_coefficient: Coeficient d'extinció.
        twilight_suppression_mag: Supressió per crepuscle en magnituds.

    Returns:
        Magnitud límit efectiva a l'altitud donada.
    """
    ext = extinction_loss_mag(altitude_deg, extinction_coefficient)
    return zenith_magnitude_limit - ext - twilight_suppression_mag


class AtmosphericExtinctionCalculator(Protocol):
    """Contracte per als càlculs d'extinció atmosfèrica."""

    def airmass(self, altitude_deg: float) -> float:
        """Calcula l'airmass a una altitud donada."""
        ...

    def extinction_magnitude(self, altitude_deg: float, coefficient: float) -> float:
        """Calcula la pèrdua de magnitud per extinció."""
        ...
