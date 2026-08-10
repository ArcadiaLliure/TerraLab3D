"""Composició de l'aparença galàctica sense I/O ni renderitzat."""

from __future__ import annotations

from terralab3d.domain.galactic.calculations import galactic_visibility_factor
from terralab3d.domain.galactic.models import GalacticAppearance


class GalacticVisibilityModel:
    """Aplica l'estat del cel als controls visuals configurats de la capa."""

    def evaluate(
        self,
        appearance: GalacticAppearance,
        *,
        sky_brightness_normalized: float,
        light_pollution_enabled: bool,
        bortle_class: float | None,
    ) -> GalacticAppearance:
        visibility = galactic_visibility_factor(
            sky_brightness_normalized=sky_brightness_normalized,
            light_pollution_enabled=light_pollution_enabled,
            bortle_class=bortle_class,
        )
        return GalacticAppearance(
            opacity=appearance.opacity * visibility,
            dust_density_strength=appearance.dust_density_strength,
            dust_extinction_strength=appearance.dust_extinction_strength,
        )
