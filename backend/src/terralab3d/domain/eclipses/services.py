"""Cohesive pure services for one instantaneous astronomical event state."""

from __future__ import annotations

import time

from .calculations import (
    eclipse_scene_appearance,
    lunar_eclipse_state,
    sky_eclipse_dimming_factor,
    solar_eclipse_state,
    solar_totality_appearance,
    unavailable_solar_eclipse_state,
)
from .models import (
    AstronomicalEventEphemeris,
    AstronomicalEventSnapshot,
    LunarLimbProfile,
)


class AstronomicalEventCalculator:
    """Build one renderer-neutral snapshot without I/O or global state."""

    def calculate(
        self,
        ephemeris: AstronomicalEventEphemeris,
        *,
        observer_generation: int,
        source_solar_system_generation: int,
        separation_rate_deg_s: float | None = None,
        limb_profile: LunarLimbProfile | None = None,
    ) -> AstronomicalEventSnapshot:
        started = time.perf_counter()
        sun = ephemeris.body("sun")
        moon = ephemeris.body("moon")
        solar = (
            solar_eclipse_state(
                sun,
                moon,
                separation_rate_deg_s=separation_rate_deg_s,
                quality=ephemeris.quality,
            )
            if sun is not None and moon is not None
            else unavailable_solar_eclipse_state(ephemeris.quality)
        )
        lunar = lunar_eclipse_state(ephemeris)
        sky_dimming = sky_eclipse_dimming_factor(solar)
        solar_north = (
            sun.north_pole_position_angle_deg
            if sun is not None and sun.north_pole_position_angle_deg is not None
            else 0.0
        )
        return AstronomicalEventSnapshot(
            generation=source_solar_system_generation,
            timestamp_utc=ephemeris.timestamp_utc,
            observer_generation=observer_generation,
            source_solar_system_generation=source_solar_system_generation,
            kernel_generation=ephemeris.kernel_generation,
            solar=solar,
            lunar=lunar,
            sky_eclipse_dimming_factor=sky_dimming,
            scene_appearance=eclipse_scene_appearance(solar, sky_dimming),
            totality_appearance=solar_totality_appearance(
                solar,
                limb_profile,
                solar_north_position_angle_deg=solar_north,
            ),
            compute_ms=(time.perf_counter() - started) * 1000.0,
        )
