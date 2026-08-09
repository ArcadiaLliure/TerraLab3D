"""Renderer-neutral sky colours shared by atmosphere and diffuse lighting."""

from __future__ import annotations

from dataclasses import dataclass


ColorLinear = tuple[float, float, float]
ColorSrgb = tuple[float, float, float]


@dataclass(frozen=True, slots=True)
class SkyLightPalette:
    """Linear-sRGB sky colours and visual diffuse-light strength.

    The source colours preserve the Step 7 visual palette.  Conversion to
    linear space happens once here so both the custom atmosphere shader and
    Three.js lighting consume the same values without double gamma.
    """

    zenith_color_linear: ColorLinear
    horizon_color_linear: ColorLinear
    ground_color_linear: ColorLinear
    diffuse_intensity: float


_DAY_ZENITH: ColorSrgb = (0.15, 0.35, 0.70)
_DAY_HORIZON: ColorSrgb = (0.55, 0.65, 0.75)
_SUNSET_ZENITH: ColorSrgb = (0.10, 0.20, 0.50)
_SUNSET_HORIZON: ColorSrgb = (0.90, 0.40, 0.10)
_CIVIL_ZENITH: ColorSrgb = (0.05, 0.10, 0.25)
_CIVIL_HORIZON: ColorSrgb = (0.40, 0.15, 0.10)
_NAUTICAL_ZENITH: ColorSrgb = (0.01, 0.02, 0.05)
_NAUTICAL_HORIZON: ColorSrgb = (0.05, 0.05, 0.10)
_NIGHT: ColorSrgb = (0.0, 0.0, 0.0)
_GROUND: ColorSrgb = (0.01, 0.01, 0.01)


def sky_light_palette(
    sun_altitude_deg: float,
    twilight_factor: float,
    atmosphere_enabled: bool,
) -> SkyLightPalette:
    """Resolve the established Step 7 palette for one authoritative Sun."""

    if not atmosphere_enabled:
        return SkyLightPalette(_NIGHT, _NIGHT, _NIGHT, 0.0)

    if sun_altitude_deg >= 6.0:
        zenith_srgb, horizon_srgb = _DAY_ZENITH, _DAY_HORIZON
    elif sun_altitude_deg >= 0.0:
        fraction = sun_altitude_deg / 6.0
        zenith_srgb = _mix(_SUNSET_ZENITH, _DAY_ZENITH, fraction)
        horizon_srgb = _mix(_SUNSET_HORIZON, _DAY_HORIZON, fraction)
    elif sun_altitude_deg >= -6.0:
        fraction = (sun_altitude_deg + 6.0) / 6.0
        zenith_srgb = _mix(_CIVIL_ZENITH, _SUNSET_ZENITH, fraction)
        horizon_srgb = _mix(_CIVIL_HORIZON, _SUNSET_HORIZON, fraction)
    elif sun_altitude_deg >= -12.0:
        fraction = (sun_altitude_deg + 12.0) / 6.0
        zenith_srgb = _mix(_NAUTICAL_ZENITH, _CIVIL_ZENITH, fraction)
        horizon_srgb = _mix(_NAUTICAL_HORIZON, _CIVIL_HORIZON, fraction)
    elif sun_altitude_deg >= -18.0:
        fraction = (sun_altitude_deg + 18.0) / 6.0
        zenith_srgb = _mix(_NIGHT, _NAUTICAL_ZENITH, fraction)
        horizon_srgb = _mix(_NIGHT, _NAUTICAL_HORIZON, fraction)
    else:
        zenith_srgb, horizon_srgb = _NIGHT, _NIGHT

    daylight = 1.0 - _clamp01(twilight_factor)
    return SkyLightPalette(
        zenith_color_linear=_srgb_to_linear(zenith_srgb),
        horizon_color_linear=_srgb_to_linear(horizon_srgb),
        ground_color_linear=_srgb_to_linear(_GROUND),
        # Visual approximation only. Bortle/SQM deliberately does not brighten
        # local ground because it is skyglow, not a spatial light source.
        diffuse_intensity=0.02 + 0.88 * daylight,
    )


def _mix(first: ColorSrgb, second: ColorSrgb, fraction: float) -> ColorSrgb:
    t = _clamp01(fraction)
    return tuple(a + (b - a) * t for a, b in zip(first, second, strict=True))  # type: ignore[return-value]


def _srgb_to_linear(color: ColorSrgb) -> ColorLinear:
    return tuple(_srgb_channel_to_linear(value) for value in color)  # type: ignore[return-value]


def _srgb_channel_to_linear(value: float) -> float:
    return value / 12.92 if value <= 0.04045 else ((value + 0.055) / 1.055) ** 2.4


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, value))
