"""Compose compact local-scene lighting without recalculating ephemerides."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import math
from typing import Any, Literal

from terralab3d.domain.atmosphere.calculations import extinction_loss_mag
from terralab3d.domain.sky_background.sky_environment import SkyEnvironmentSnapshot
from terralab3d.domain.solar_system.models import (
    ApparentBodyState,
    EphemerisQuality,
    SolarSystemSnapshot,
)


IntensityKind = Literal["physical", "relative", "visual"]
DirectLightQuality = Literal["scientific", "approximate", "fallback", "unavailable"]
DiffuseLightQuality = Literal["scientific", "approximate", "fallback"]
ColorLinear = tuple[float, float, float]
DirectionENU = tuple[float, float, float]

_FULL_MOON_REFERENCE_MAGNITUDE = -12.74
_SUN_VISUAL_INTENSITY = 3.0
# Visual PBR scale, not lux.  The previous 0.045 full-Moon reference became
# imperceptible after atmospheric extinction on the deliberately dark local
# terrain.  This remains far below the Sun while making measured lunar flux
# observable without changing the Moon disc, its phase or its terminator.
_FULL_MOON_VISUAL_INTENSITY = 0.8


@dataclass(frozen=True, slots=True)
class DirectLightState:
    enabled: bool
    direction_to_source_enu: DirectionENU
    altitude_deg: float
    color_linear: ColorLinear
    intensity: float
    intensity_kind: IntensityKind
    quality: DirectLightQuality

    def to_dict(self) -> dict[str, Any]:
        return {
            "enabled": self.enabled,
            "directionToSourceENU": list(self.direction_to_source_enu),
            "altitudeDeg": self.altitude_deg,
            "colorLinear": list(self.color_linear),
            "intensity": self.intensity,
            "intensityKind": self.intensity_kind,
            "quality": self.quality,
        }


@dataclass(frozen=True, slots=True)
class DiffuseSkyLightState:
    enabled: bool
    zenith_color_linear: ColorLinear
    horizon_color_linear: ColorLinear
    ground_color_linear: ColorLinear
    intensity: float
    quality: DiffuseLightQuality

    def to_dict(self) -> dict[str, Any]:
        return {
            "enabled": self.enabled,
            "zenithColorLinear": list(self.zenith_color_linear),
            "horizonColorLinear": list(self.horizon_color_linear),
            "groundColorLinear": list(self.ground_color_linear),
            "intensity": self.intensity,
            "quality": self.quality,
        }


@dataclass(frozen=True, slots=True)
class LightingEnvironmentSnapshot:
    generation: int
    timestamp_utc: datetime
    source_sky_generation: int
    source_solar_system_generation: int
    sun: DirectLightState
    moon: DirectLightState
    sky_diffuse: DiffuseSkyLightState
    direct_solar_visibility_factor: float = 1.0
    exposure_hint: float | None = None

    def to_dict(self) -> dict[str, Any]:
        timestamp = self.timestamp_utc.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
        payload: dict[str, Any] = {
            "generation": self.generation,
            "timestampUtc": timestamp,
            "sourceSkyGeneration": self.source_sky_generation,
            "sourceSolarSystemGeneration": self.source_solar_system_generation,
            "directSolarVisibilityFactor": self.direct_solar_visibility_factor,
            "sun": self.sun.to_dict(),
            "moon": self.moon.to_dict(),
            "skyDiffuse": self.sky_diffuse.to_dict(),
        }
        if self.exposure_hint is not None:
            payload["exposureHint"] = self.exposure_hint
        return payload


class LightingEnvironmentComposer:
    """Transform Step 7/8 snapshots into small renderer-neutral light state."""

    def __init__(self) -> None:
        self._generation = 0
        self.snapshot_count = 0

    def compose(
        self,
        sky: SkyEnvironmentSnapshot,
        solar_system: SolarSystemSnapshot,
        *,
        direct_solar_visibility_factor: float = 1.0,
    ) -> LightingEnvironmentSnapshot:
        visibility = _finite_clamp01(
            direct_solar_visibility_factor,
            "directSolarVisibilityFactor",
        )
        self._generation += 1
        self.snapshot_count += 1
        return LightingEnvironmentSnapshot(
            generation=self._generation,
            timestamp_utc=solar_system.timestamp_utc,
            source_sky_generation=sky.generation,
            source_solar_system_generation=solar_system.generation,
            sun=self._compose_sun(sky, solar_system.sun, visibility),
            moon=self._compose_moon(sky, solar_system.moon),
            sky_diffuse=self._compose_diffuse(sky),
            # Pas 9 has one explicit hook and does not need to refactor lighting.
            direct_solar_visibility_factor=visibility,
        )

    def metrics(self) -> dict[str, int]:
        return {"lighting_snapshot_count": self.snapshot_count}

    @staticmethod
    def _compose_sun(
        sky: SkyEnvironmentSnapshot,
        sun: ApparentBodyState,
        visibility: float,
    ) -> DirectLightState:
        direction = _normalize_direction(sun.direction_enu, "sun.directionENU")
        altitude = _finite(sun.horizontal.altitude_deg, "sun.altitudeDeg")
        transmission = _atmospheric_transmission(sky, altitude)
        intensity = _SUN_VISUAL_INTENSITY * transmission * visibility if altitude > 0.0 else 0.0
        return DirectLightState(
            enabled=intensity > 0.0,
            direction_to_source_enu=direction,
            altitude_deg=altitude,
            color_linear=_extinguished_color(
                base=(1.0, 0.956, 0.838),
                warm=(1.0, 0.318, 0.048),
                transmission=transmission,
            ),
            intensity=_non_negative_finite(intensity, "sun.intensity"),
            intensity_kind="visual",
            quality=(
                "scientific"
                if sun.quality is EphemerisQuality.PRECISE
                else "approximate"
            ),
        )

    @staticmethod
    def _compose_moon(
        sky: SkyEnvironmentSnapshot,
        moon: ApparentBodyState | None,
    ) -> DirectLightState:
        if moon is None:
            return DirectLightState(
                enabled=False,
                direction_to_source_enu=(0.0, 1.0, 0.0),
                altitude_deg=-90.0,
                color_linear=(0.0, 0.0, 0.0),
                intensity=0.0,
                intensity_kind="visual",
                quality="unavailable",
            )

        direction = _normalize_direction(moon.direction_enu, "moon.directionENU")
        altitude = _finite(moon.horizontal.altitude_deg, "moon.altitudeDeg")
        transmission = _atmospheric_transmission(sky, altitude)
        if moon.apparent_magnitude is not None:
            magnitude = _finite(moon.apparent_magnitude, "moon.apparentMagnitude")
            # Apparent magnitude already incorporates phase and distance.
            relative_flux = 10.0 ** (-0.4 * (magnitude - _FULL_MOON_REFERENCE_MAGNITUDE))
            intensity = _FULL_MOON_VISUAL_INTENSITY * min(relative_flux, 1.5)
            intensity_kind: IntensityKind = "relative"
            quality: DirectLightQuality = (
                "scientific"
                if moon.quality is EphemerisQuality.PRECISE
                else "approximate"
            )
        else:
            phase = _finite_clamp01(moon.illumination_fraction, "moon.illuminationFraction")
            distance = max(_finite(moon.distance_km, "moon.distanceKm"), 1.0)
            intensity = _FULL_MOON_VISUAL_INTENSITY * phase * (384_400.0 / distance) ** 2
            intensity_kind = "visual"
            quality = "approximate"
        if altitude <= 0.0:
            intensity = 0.0
        else:
            intensity *= transmission
        return DirectLightState(
            enabled=intensity > 1e-9,
            direction_to_source_enu=direction,
            altitude_deg=altitude,
            color_linear=_extinguished_color(
                base=(0.617, 0.724, 1.0),
                warm=(0.86, 0.50, 0.23),
                transmission=transmission,
            ),
            intensity=_non_negative_finite(intensity, "moon.intensity"),
            intensity_kind=intensity_kind,
            quality=quality,
        )

    @staticmethod
    def _compose_diffuse(sky: SkyEnvironmentSnapshot) -> DiffuseSkyLightState:
        return DiffuseSkyLightState(
            enabled=sky.atmosphere_enabled and sky.sky_diffuse_intensity > 0.0,
            zenith_color_linear=_validate_color(sky.zenith_color_linear, "sky.zenithColorLinear"),
            horizon_color_linear=_validate_color(sky.horizon_color_linear, "sky.horizonColorLinear"),
            ground_color_linear=_validate_color(sky.ground_color_linear, "sky.groundColorLinear"),
            intensity=_non_negative_finite(sky.sky_diffuse_intensity, "sky.diffuseIntensity"),
            quality="approximate",
        )


def _atmospheric_transmission(sky: SkyEnvironmentSnapshot, altitude_deg: float) -> float:
    if not sky.atmosphere_enabled:
        return 1.0
    loss = extinction_loss_mag(altitude_deg, sky.visibility.extinction_coefficient)
    return max(0.0, min(1.0, 10.0 ** (-0.4 * min(loss, 20.0))))


def _extinguished_color(
    *,
    base: ColorLinear,
    warm: ColorLinear,
    transmission: float,
) -> ColorLinear:
    warm_fraction = 1.0 - max(0.0, min(1.0, transmission))
    return tuple(
        base_value + (warm_value - base_value) * warm_fraction
        for base_value, warm_value in zip(base, warm, strict=True)
    )  # type: ignore[return-value]


def _normalize_direction(value: DirectionENU, field: str) -> DirectionENU:
    components = tuple(_finite(component, field) for component in value)
    length = math.sqrt(sum(component * component for component in components))
    if length <= 1e-12:
        raise ValueError(f"{field} is degenerate")
    return tuple(component / length for component in components)  # type: ignore[return-value]


def _validate_color(value: ColorLinear, field: str) -> ColorLinear:
    return tuple(
        _finite_clamp01(component, field) for component in value
    )  # type: ignore[return-value]


def _finite(value: float, field: str) -> float:
    result = float(value)
    if not math.isfinite(result):
        raise ValueError(f"{field} must be finite")
    return result


def _finite_clamp01(value: float, field: str) -> float:
    return max(0.0, min(1.0, _finite(value, field)))


def _non_negative_finite(value: float, field: str) -> float:
    result = _finite(value, field)
    if result < 0.0:
        raise ValueError(f"{field} must be non-negative")
    return result
