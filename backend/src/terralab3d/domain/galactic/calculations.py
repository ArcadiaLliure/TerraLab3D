"""Càlculs purs compartits per a orientació i visibilitat galàctiques."""

from __future__ import annotations

import math


EQUATORIAL_TO_GALACTIC_J2000 = (
    (-0.0548755604, -0.8734370902, -0.4838350155),
    (0.4941094279, -0.4448296300, 0.7469822445),
    (-0.8676661490, -0.1980763734, 0.4559837762),
)


def equatorial_to_galactic_direction(
    direction: tuple[float, float, float],
) -> tuple[float, float, float]:
    """Transforma un vector unitari ICRF/J2000 amb la matriu IAU 2000."""

    norm = math.sqrt(sum(component * component for component in direction))
    if norm <= 0.0 or not math.isfinite(norm):
        raise ValueError("La direcció equatorial ha de ser finita i no nul·la")
    unit = tuple(component / norm for component in direction)
    return tuple(
        sum(row[index] * unit[index] for index in range(3))
        for row in EQUATORIAL_TO_GALACTIC_J2000
    )  # type: ignore[return-value]


def galactic_visibility_factor(
    *,
    sky_brightness_normalized: float,
    light_pollution_enabled: bool,
    bortle_class: float | None,
) -> float:
    """Factor visual continu del fons difús; no conté regles dia/nit discretes."""

    darkness = _clamp01(1.0 - sky_brightness_normalized)
    if light_pollution_enabled and bortle_class is not None:
        bortle_visibility = _clamp01(1.0 - (bortle_class - 1.0) / 8.0)
    else:
        bortle_visibility = 1.0
    return math.pow(darkness, 1.6) * (0.18 + 0.82 * bortle_visibility)


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, value))
