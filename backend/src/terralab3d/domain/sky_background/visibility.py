"""Visibilitat estel·lar combinada.

Combina llum natural + contaminació lumínica + extinció atmosfèrica
per determinar la visibilitat final.

Contracte compartit amb el shader GLSL i el picker TypeScript.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class SkyVisibilityState:
    """Estat de visibilitat estel·lar per al shader i picker.

    Tots els camps són paràmetres que el shader (GPU) i el picker (CPU)
    necessiten per calcular la visibilitat de cada estrella individual.

    Atributs:
        zenith_magnitude_limit: Magnitud límit efectiva al zenit (Bortle + LP).
        extinction_coefficient: Coeficient d'extinció en mag/airmass.
        twilight_suppression: Penalització de magnitud per crepuscle.
        fade_width_mag: Amplada de la transició de fade en magnituds.
            Estrelles dins d'aquesta finestra s'atenuen suaument.
        sky_brightness_normalized: Brillantor total del cel normalitzada [0, 1].
            Combinació de natural + artificial + crepuscle.
    """
    zenith_magnitude_limit: float = 6.5 #S'ha canviat de 7.25 a 6.5
    extinction_coefficient: float = 0.25
    twilight_suppression: float = 0.0
    fade_width_mag: float = 0.75
    sky_brightness_normalized: float = 0.0


class SkyVisibilityCalculator:
    """Calcula la visibilitat final combinant tots els factors."""

    def calculate(
        self,
        bortle_zenith_mag: float,
        twilight_suppression_mag: float,
        artificial_brightness: float,
        natural_brightness: float,
        twilight_factor: float,
        extinction_coefficient: float = 0.25,
    ) -> SkyVisibilityState:
        """Resol l'estat final de visibilitat."""
        
        # Combinem brillantor (simplificat per al shader)
        # 1. Artificial sempre hi és (si mode està actiu)
        # 2. Natural (estrelles/galàxia) sempre hi és, atenuat pel sol
        # 3. Crepuscle afegeix brillantor (invers al twilight_factor on 0=dia, 1=nit)
        daylight_brightness = 1.0 - twilight_factor
        
        total_brightness = artificial_brightness + natural_brightness + daylight_brightness
        total_brightness = max(0.0, min(1.0, total_brightness))

        # El zenit limit empitjora si hi ha crepuscle extrem,
        # però el twilight_suppression_mag ja s'encarrega d'això al shader.
        # Passem els valors directament.
        
        return SkyVisibilityState(
            zenith_magnitude_limit=bortle_zenith_mag,
            extinction_coefficient=extinction_coefficient,
            twilight_suppression=twilight_suppression_mag,
            fade_width_mag=0.75,
            sky_brightness_normalized=total_brightness,
        )
