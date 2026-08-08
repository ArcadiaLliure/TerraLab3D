"""Compositor principal de l'estat del cel.

Aquest mòdul orquestra tots els subdominis (Sol, Atmosfera, Contaminació Lumínica)
i genera un 'SkyEnvironmentSnapshot' tipat que s'envia al frontend.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from terralab3d.domain.atmosphere.calculations import twilight_suppression
from terralab3d.domain.atmosphere.models import AtmosphereState
from terralab3d.domain.light_pollution.calculations import resolve_light_pollution_state
from terralab3d.domain.light_pollution.models import LightPollutionState, LightPollutionMode
from terralab3d.domain.sky_background.solar_direction import (
    SolarDirection,
    SolarSkyCalculator,
    twilight_factor,
    twilight_phase,
)
from terralab3d.domain.sky_background.visibility import SkyVisibilityState, SkyVisibilityCalculator


@dataclass(frozen=True, slots=True)
class SkyEnvironmentSnapshot:
    """Contracte complet de l'estat del cel per al frontend.

    L'atribut `generation` permet descartar missatges antics.
    Tot l'estat de GPU/UI deriva d'aquest snapshot.
    """
    generation: int
    
    # Solar / Twilight
    sun_altitude_deg: float
    sun_azimuth_deg: float
    sun_direction_enu: tuple[float, float, float]
    twilight_phase: str
    twilight_factor: float
    
    # Atmosphere
    atmosphere_enabled: bool
    turbidity: float
    horizon_haze: float
    
    # Light Pollution
    light_pollution_enabled: bool
    light_pollution_mode: str
    light_pollution_source: str
    bortle_class: float | None
    sqm_zenith: float | None
    configured_magnitude_limit: float | None
    
    # Visibility (per al shader estel·lar i picking)
    visibility: SkyVisibilityState
    
    def to_dict(self) -> dict[str, Any]:
        """Converteix l'snapshot a diccionari pla per JSON."""
        return {
            "generation": self.generation,
            
            "sunAltitudeDeg": self.sun_altitude_deg,
            "sunAzimuthDeg": self.sun_azimuth_deg,
            "sunDirectionENU": list(self.sun_direction_enu),
            "twilightPhase": self.twilight_phase,
            "twilightFactor": self.twilight_factor,
            
            "atmosphereEnabled": self.atmosphere_enabled,
            "turbidity": self.turbidity,
            "horizonHaze": self.horizon_haze,
            
            "lightPollutionEnabled": self.light_pollution_enabled,
            "lightPollutionMode": self.light_pollution_mode,
            "lightPollutionSource": self.light_pollution_source,
            "bortleClass": self.bortle_class,
            "sqmZenith": self.sqm_zenith,
            "configuredMagnitudeLimit": self.configured_magnitude_limit,
            
            "visibility": {
                "zenithMagnitudeLimit": self.visibility.zenith_magnitude_limit,
                "extinctionCoefficient": self.visibility.extinction_coefficient,
                "twilightSuppression": self.visibility.twilight_suppression,
                "fadeWidthMag": self.visibility.fade_width_mag,
                "skyBrightnessNormalized": self.visibility.sky_brightness_normalized,
            }
        }


class SkyEnvironmentComposer:
    """Compon l'estat complet del cel a partir de múltiples dominis."""

    def __init__(self) -> None:
        self._solar_calc = SolarSkyCalculator()
        self._visibility_calc = SkyVisibilityCalculator()
        self._generation = 0
        
        # Estat local mutable per UI controls
        self.atmosphere_enabled = True
        self.light_pollution_enabled = True
        self.light_pollution_mode = LightPollutionMode.BORTLE
        self.bortle_value = 4.0
        self.magnitude_limit = 6.0
        
        # En el futur, l'estimador automàtic s'injectaria aquí
        self.automatic_bortle: float | None = None
        self.automatic_source: str = "unavailable"

    def set_automatic_estimate(self, bortle: float | None, source: str) -> None:
        """Actualitza l'estimació automàtica quan canvia la ubicació."""
        self.automatic_bortle = bortle
        self.automatic_source = source

    def compose(
        self,
        utc_year: int,
        utc_month: int,
        utc_day: int,
        utc_hour: float,
        latitude_deg: float,
        longitude_deg: float,
    ) -> SkyEnvironmentSnapshot:
        """Genera un nou snapshot incrementant la generació."""
        self._generation += 1
        
        # 1. Domini Solar
        solar_dir = self._solar_calc.solar_position(
            utc_year, utc_month, utc_day, utc_hour, latitude_deg, longitude_deg
        )
        phase = twilight_phase(solar_dir.altitude_deg)
        t_factor = twilight_factor(solar_dir.altitude_deg)
        
        # 2. Domini Contaminació Lumínica
        lp_state = resolve_light_pollution_state(
            enabled=self.light_pollution_enabled,
            mode=self.light_pollution_mode,
            bortle_value=self.bortle_value,
            magnitude_limit=self.magnitude_limit,
            automatic_estimate_bortle=self.automatic_bortle,
            automatic_source=self.automatic_source,
        )
        
        # 3. Domini Atmosfera
        atmos_state = AtmosphereState()
        tw_suppression = twilight_suppression(solar_dir.altitude_deg) if self.atmosphere_enabled else 0.0
        
        # 4. Visibilitat Combinada
        vis_state = self._visibility_calc.calculate(
            bortle_zenith_mag=lp_state.zenith_magnitude_limit,
            twilight_suppression_mag=tw_suppression,
            artificial_brightness=lp_state.artificial_sky_brightness,
            natural_brightness=atmos_state.natural_sky_brightness,
            twilight_factor=t_factor if self.atmosphere_enabled else 1.0,
            extinction_coefficient=atmos_state.extinction_coefficient if self.atmosphere_enabled else 0.0,
        )
        
        return SkyEnvironmentSnapshot(
            generation=self._generation,
            sun_altitude_deg=solar_dir.altitude_deg,
            sun_azimuth_deg=solar_dir.azimuth_deg,
            sun_direction_enu=solar_dir.direction_enu,
            twilight_phase=phase.value,
            twilight_factor=t_factor,
            atmosphere_enabled=self.atmosphere_enabled,
            turbidity=atmos_state.turbidity,
            horizon_haze=atmos_state.horizon_haze,
            light_pollution_enabled=lp_state.enabled,
            light_pollution_mode=lp_state.mode.value,
            light_pollution_source=lp_state.source.value,
            bortle_class=lp_state.bortle_class,
            sqm_zenith=lp_state.sqm_zenith,
            configured_magnitude_limit=lp_state.configured_magnitude_limit,
            visibility=vis_state,
        )
