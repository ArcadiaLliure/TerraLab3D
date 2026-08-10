"""Compose the visual sky from one authoritative ephemeris Sun."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from terralab3d.domain.atmosphere.calculations import twilight_suppression
from terralab3d.domain.atmosphere.models import AtmosphereState
from terralab3d.domain.light_pollution.calculations import resolve_light_pollution_state
from terralab3d.domain.light_pollution.models import LightPollutionMode
from terralab3d.domain.sky_background.solar_direction import twilight_factor, twilight_phase
from terralab3d.domain.sky_background.sky_palette import sky_light_palette
from terralab3d.domain.sky_background.visibility import SkyVisibilityCalculator, SkyVisibilityState
from terralab3d.domain.solar_system.models import ApparentBodyState


# During totality the sky remains a bright deep twilight.  Keeping roughly
# 4.5 magnitudes of daylight suppression exposes Venus and only the brightest
# stars instead of turning the scene into a normal night sky.
TOTALITY_TWILIGHT_SUPPRESSION_MAG = 4.5


@dataclass(frozen=True, slots=True)
class SkyEnvironmentSnapshot:
    generation: int
    solar_system_generation: int
    sun_altitude_deg: float
    sun_azimuth_deg: float
    sun_direction_enu: tuple[float, float, float]
    twilight_phase: str
    twilight_factor: float
    atmosphere_enabled: bool
    turbidity: float
    horizon_haze: float
    light_pollution_enabled: bool
    light_pollution_mode: str
    light_pollution_source: str
    bortle_class: float | None
    sqm_zenith: float | None
    configured_magnitude_limit: float | None
    visibility: SkyVisibilityState
    zenith_color_linear: tuple[float, float, float]
    horizon_color_linear: tuple[float, float, float]
    ground_color_linear: tuple[float, float, float]
    sky_diffuse_intensity: float
    solar_disc_transmission: float = 1.0
    sky_eclipse_dimming_factor: float = 1.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "generation": self.generation,
            "solarSystemGeneration": self.solar_system_generation,
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
            },
            "zenithColorLinear": list(self.zenith_color_linear),
            "horizonColorLinear": list(self.horizon_color_linear),
            "groundColorLinear": list(self.ground_color_linear),
            "skyDiffuseIntensity": self.sky_diffuse_intensity,
            "solarDiscTransmission": self.solar_disc_transmission,
            "skyEclipseDimmingFactor": self.sky_eclipse_dimming_factor,
        }


class SkyEnvironmentComposer:
    def __init__(self) -> None:
        self._visibility_calc = SkyVisibilityCalculator()
        self._generation = 0
        self.atmosphere_enabled = True
        self.light_pollution_enabled = True
        self.light_pollution_mode = LightPollutionMode.BORTLE
        self.bortle_value = 4.0
        self.magnitude_limit = 6.0
        self.automatic_bortle: float | None = None
        self.automatic_source = "unavailable"

    def set_automatic_estimate(self, bortle: float | None, source: str) -> None:
        self.automatic_bortle = bortle
        self.automatic_source = source

    def compose(
        self,
        sun: ApparentBodyState,
        solar_system_generation: int,
        *,
        solar_disc_transmission: float = 1.0,
        sky_eclipse_dimming_factor: float = 1.0,
    ) -> SkyEnvironmentSnapshot:
        self._generation += 1
        disc_transmission = max(0.0, min(1.0, float(solar_disc_transmission)))
        eclipse_dimming = max(0.0, min(1.0, float(sky_eclipse_dimming_factor)))
        solar_altitude = sun.horizontal.altitude_deg
        phase = twilight_phase(solar_altitude)
        night_factor = twilight_factor(solar_altitude)
        light_pollution = resolve_light_pollution_state(
            enabled=self.light_pollution_enabled,
            mode=self.light_pollution_mode,
            bortle_value=self.bortle_value,
            magnitude_limit=self.magnitude_limit,
            automatic_estimate_bortle=self.automatic_bortle,
            automatic_source=self.automatic_source,
        )
        atmosphere = AtmosphereState()
        normal_suppression = (
            twilight_suppression(solar_altitude) if self.atmosphere_enabled else 0.0
        )
        totality_suppression = min(
            normal_suppression,
            TOTALITY_TWILIGHT_SUPPRESSION_MAG,
        )
        suppression = totality_suppression + (
            normal_suppression - totality_suppression
        ) * eclipse_dimming
        effective_night_factor = min(
            1.0,
            night_factor + (1.0 - night_factor) * (1.0 - eclipse_dimming),
        )
        visibility = self._visibility_calc.calculate(
            bortle_zenith_mag=light_pollution.zenith_magnitude_limit,
            twilight_suppression_mag=suppression,
            artificial_brightness=light_pollution.artificial_sky_brightness,
            natural_brightness=atmosphere.natural_sky_brightness,
            twilight_factor=effective_night_factor if self.atmosphere_enabled else 1.0,
            extinction_coefficient=(
                atmosphere.extinction_coefficient if self.atmosphere_enabled else 0.0
            ),
        )
        palette = sky_light_palette(
            solar_altitude,
            night_factor,
            self.atmosphere_enabled,
        )
        color_scale = 0.08 + 0.92 * eclipse_dimming
        return SkyEnvironmentSnapshot(
            generation=self._generation,
            solar_system_generation=solar_system_generation,
            sun_altitude_deg=solar_altitude,
            sun_azimuth_deg=sun.horizontal.azimuth_deg,
            sun_direction_enu=sun.direction_enu,
            twilight_phase=phase.value,
            twilight_factor=night_factor,
            atmosphere_enabled=self.atmosphere_enabled,
            turbidity=atmosphere.turbidity,
            horizon_haze=atmosphere.horizon_haze,
            light_pollution_enabled=light_pollution.enabled,
            light_pollution_mode=light_pollution.mode.value,
            light_pollution_source=light_pollution.source.value,
            bortle_class=light_pollution.bortle_class,
            sqm_zenith=light_pollution.sqm_zenith,
            configured_magnitude_limit=light_pollution.configured_magnitude_limit,
            visibility=visibility,
            zenith_color_linear=tuple(value * color_scale for value in palette.zenith_color_linear),
            horizon_color_linear=tuple(value * color_scale for value in palette.horizon_color_linear),
            ground_color_linear=tuple(value * color_scale for value in palette.ground_color_linear),
            sky_diffuse_intensity=palette.diffuse_intensity * eclipse_dimming,
            solar_disc_transmission=disc_transmission,
            sky_eclipse_dimming_factor=eclipse_dimming,
        )
