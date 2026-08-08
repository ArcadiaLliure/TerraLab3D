"""Càlculs purs de contaminació lumínica.

Relació canònica Bortle↔magnitud (paritat TerraLab):
    m_lim_zenith = 7.6 - 0.5 * (Bortle - 1)

Mapeig SQM→Bortle: ordinal empíric, NO equivalència exacta.
"""

from __future__ import annotations

from .models import (
    LightPollutionMode,
    LightPollutionSource,
    LightPollutionState,
)


def clamp_bortle(value: float) -> float:
    """Clamp el valor Bortle a [1, 9]."""
    return max(1.0, min(9.0, float(value)))


def bortle_to_zenith_magnitude_limit(bortle_class: float) -> float:
    """Converteix classe Bortle a magnitud límit zenital.

    Relació canònica (paritat TerraLab):
        m_lim_zenith = 7.6 - 0.5 * (Bortle - 1)

    Bortle 1 → 7.6 mag
    Bortle 5 → 5.6 mag
    Bortle 9 → 3.6 mag

    NOTA: Aquesta relació és empírica i aproximada.
    """
    b = clamp_bortle(bortle_class)
    return 7.6 - 0.5 * (b - 1.0)


def magnitude_to_bortle_approximate(magnitude_limit: float) -> float:
    """Converteix magnitud límit a classe Bortle equivalent (aproximat).

    Inversa de bortle_to_zenith_magnitude_limit, clampada a [1, 9].
    Etiquetar com APROXIMAT a la UI.
    """
    bortle = 1.0 + (7.6 - float(magnitude_limit)) / 0.5
    return clamp_bortle(bortle)


def sqm_to_bortle(sqm: float) -> int:
    """Converteix lectura SQM zenital (mag/arcsec²) a classe Bortle.

    Mapeig ordinal empíric — paritat amb TerraLab/bortle.py.
    NO és una equivalència exacta.
    """
    if sqm >= 21.99:
        return 1
    if sqm >= 21.89:
        return 2
    if sqm >= 21.69:
        return 3
    if sqm >= 20.49:
        return 4
    if sqm >= 19.50:
        return 5
    if sqm >= 18.94:
        return 6
    if sqm >= 18.38:
        return 7
    if sqm >= 17.80:
        return 8
    return 9


def artificial_sky_brightness(bortle_class: float) -> float:
    """Calcula la brillantor artificial normalitzada [0, 1].

    Bortle 1 → 0.0 (cap contaminació)
    Bortle 9 → 1.0 (màxima contaminació)

    Escala no lineal: la contaminació augmenta ràpidament
    en zones urbanes.
    """
    b = clamp_bortle(bortle_class)
    # Normalitzat lineal de [1, 9] a [0, 1]
    linear = (b - 1.0) / 8.0
    # Corba lleugerament convexa per representar que la LP
    # augmenta més ràpidament en Bortle alt
    return linear * linear * (3.0 - 2.0 * linear)


def resolve_light_pollution_state(
    enabled: bool,
    mode: LightPollutionMode,
    bortle_value: float = 4.0,
    magnitude_limit: float = 6.0,
    automatic_estimate_bortle: float | None = None,
    automatic_source: str = "unavailable",
) -> LightPollutionState:
    """Resol l'estat complet de contaminació lumínica.

    Semàntica de cada mode:
        AUTOMATIC: Usa automatic_estimate_bortle si disponible.
                   Si no, retorna source=UNAVAILABLE amb Bortle 1 (conservador).
        BORTLE: Usa bortle_value directament.
        MAGNITUDE: Usa magnitude_limit, calcula Bortle equivalent.

    Si enabled=False: retorna Bortle 1 (cel perfecte, cap contaminació).
    """
    if not enabled:
        return LightPollutionState(
            enabled=False,
            mode=mode,
            source=LightPollutionSource.UNAVAILABLE,
            bortle_class=1.0,
            sqm_zenith=None,
            configured_magnitude_limit=None,
            zenith_magnitude_limit=7.6,
            artificial_sky_brightness=0.0,
        )

    if mode == LightPollutionMode.AUTOMATIC:
        if automatic_estimate_bortle is not None:
            bortle = clamp_bortle(automatic_estimate_bortle)
            return LightPollutionState(
                enabled=True,
                mode=mode,
                source=LightPollutionSource.DATASET if automatic_source == "dataset" else LightPollutionSource.FALLBACK,
                bortle_class=bortle,
                sqm_zenith=None,
                configured_magnitude_limit=None,
                zenith_magnitude_limit=bortle_to_zenith_magnitude_limit(bortle),
                artificial_sky_brightness=artificial_sky_brightness(bortle),
            )
        # Sense dades automàtiques: retorna unavailable amb Bortle 1 conservador
        return LightPollutionState(
            enabled=True,
            mode=mode,
            source=LightPollutionSource.UNAVAILABLE,
            bortle_class=None,
            sqm_zenith=None,
            configured_magnitude_limit=None,
            zenith_magnitude_limit=7.6,
            artificial_sky_brightness=0.0,
        )

    if mode == LightPollutionMode.BORTLE:
        bortle = clamp_bortle(bortle_value)
        return LightPollutionState(
            enabled=True,
            mode=mode,
            source=LightPollutionSource.MANUAL_BORTLE,
            bortle_class=bortle,
            sqm_zenith=None,
            configured_magnitude_limit=None,
            zenith_magnitude_limit=bortle_to_zenith_magnitude_limit(bortle),
            artificial_sky_brightness=artificial_sky_brightness(bortle),
        )

    # MAGNITUDE mode
    mag = float(magnitude_limit)
    bortle_equiv = magnitude_to_bortle_approximate(mag)
    return LightPollutionState(
        enabled=True,
        mode=mode,
        source=LightPollutionSource.MANUAL_MAGNITUDE,
        bortle_class=bortle_equiv,
        sqm_zenith=None,
        configured_magnitude_limit=mag,
        zenith_magnitude_limit=mag,
        artificial_sky_brightness=artificial_sky_brightness(bortle_equiv),
    )
