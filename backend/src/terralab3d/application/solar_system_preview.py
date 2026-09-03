"""Coherent lightweight celestial state used while scrubbing the timeline."""

from __future__ import annotations

import math
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from terralab3d.application.ports.astronomical_events import (
    AstronomicalEventEphemerisPort,
)
from terralab3d.domain.eclipses.models import (
    AstronomicalEventEphemeris,
    AstronomicalEventSnapshot,
)
from terralab3d.domain.eclipses.services import AstronomicalEventCalculator
from terralab3d.domain.solar_system.calculations import (
    AU_KM,
    illuminated_fraction,
    moon_apparent_magnitude,
    planet_apparent_magnitude,
    sun_apparent_magnitude,
)
from terralab3d.domain.solar_system.models import ScientificObserver


PREVIEW_BODY_IDS = (
    "sun",
    "moon",
    "mercury",
    "venus",
    "mars",
    "jupiter",
    "saturn",
    "uranus",
    "neptune",
    "pluto",
)


@dataclass(frozen=True, slots=True)
class SolarSystemPreviewBody:
    body_id: str
    direction_enu: tuple[float, float, float]
    altitude_deg: float
    azimuth_deg: float
    distance_km: float
    angular_radius_deg: float
    illumination_fraction: float
    phase_angle_deg: float
    apparent_magnitude: float | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.body_id,
            "directionENU": list(self.direction_enu),
            "altitudeDeg": self.altitude_deg,
            "azimuthDeg": self.azimuth_deg,
            "distanceKm": self.distance_km,
            "angularRadiusDeg": self.angular_radius_deg,
            "illuminationFraction": self.illumination_fraction,
            "phaseAngleDeg": self.phase_angle_deg,
            "apparentMagnitude": self.apparent_magnitude,
        }


@dataclass(frozen=True, slots=True)
class SolarSystemPreviewSnapshot:
    generation: int
    timestamp_utc: datetime
    observer_generation: int
    source: str
    quality: str
    compute_ms: float
    bodies: tuple[SolarSystemPreviewBody, ...]
    event: AstronomicalEventSnapshot

    def to_dict(self) -> dict[str, Any]:
        return {
            "generation": self.generation,
            "observerGeneration": self.observer_generation,
            "bodies": [body.to_dict() for body in self.bodies],
        }


class SolarSystemPreviewService:
    """Calculates positions and preview photometry without orientation batches."""

    def __init__(self, ephemeris: AstronomicalEventEphemerisPort) -> None:
        self._ephemeris = ephemeris

    def calculate(
        self,
        utc: datetime,
        observer: ScientificObserver,
        *,
        generation: int,
        observer_generation: int,
        additional_body_ids: tuple[str, ...] = (),
    ) -> SolarSystemPreviewSnapshot:
        started = time.perf_counter()
        ephemeris = self._ephemeris.event_ephemeris(
            utc,
            observer,
            PREVIEW_BODY_IDS + additional_body_ids,
            include_lunar_shadow_geometry=True,
            include_body_orientation=False,
            allow_unknown_radius=True,
        )
        bodies = self._preview_bodies(ephemeris)
        event = AstronomicalEventCalculator().calculate(
            ephemeris,
            observer_generation=observer_generation,
            source_solar_system_generation=generation,
        )
        return SolarSystemPreviewSnapshot(
            generation=generation,
            timestamp_utc=ephemeris.timestamp_utc,
            observer_generation=observer_generation,
            source=ephemeris.source,
            quality=ephemeris.quality.value,
            compute_ms=(time.perf_counter() - started) * 1000.0,
            bodies=bodies,
            event=event,
        )

    @classmethod
    def _preview_bodies(
        cls,
        ephemeris: AstronomicalEventEphemeris,
    ) -> tuple[SolarSystemPreviewBody, ...]:
        sun = ephemeris.body("sun")
        sun_position = (
            _scaled(sun.direction_icrf, sun.distance_km)
            if sun is not None
            else None
        )
        return tuple(cls._preview_body(body, sun_position) for body in ephemeris.bodies)

    @staticmethod
    def _preview_body(
        body: Any,
        sun_position: tuple[float, float, float] | None,
    ) -> SolarSystemPreviewBody:
        east, _up, north = body.direction_enu
        phase_angle = _phase_angle_deg(body, sun_position)
        return SolarSystemPreviewBody(
            body_id=body.body_id,
            direction_enu=body.direction_enu,
            altitude_deg=body.altitude_deg,
            azimuth_deg=math.degrees(math.atan2(east, north)) % 360.0,
            distance_km=body.distance_km,
            angular_radius_deg=body.angular_radius_deg,
            illumination_fraction=illuminated_fraction(phase_angle),
            phase_angle_deg=phase_angle,
            apparent_magnitude=_apparent_magnitude(body, sun_position, phase_angle),
        )


def _phase_angle_deg(
    body: Any,
    sun_position: tuple[float, float, float] | None,
) -> float:
    if body.body_id == "sun" or sun_position is None:
        return 0.0
    body_position = _scaled(body.direction_icrf, body.distance_km)
    body_to_sun = _subtract(sun_position, body_position)
    body_to_observer = tuple(-value for value in body_position)
    denominator = _length(body_to_sun) * _length(body_to_observer)
    if denominator <= 1e-12:
        return 0.0
    cosine = max(-1.0, min(1.0, _dot(body_to_sun, body_to_observer) / denominator))
    return math.degrees(math.acos(cosine))


def _apparent_magnitude(
    body: Any,
    sun_position: tuple[float, float, float] | None,
    phase_angle_deg: float,
) -> float | None:
    observer_distance_au = max(body.distance_km / AU_KM, 1e-12)
    if body.body_id == "sun":
        return sun_apparent_magnitude(observer_distance_au)
    if sun_position is None:
        return None
    body_position = _scaled(body.direction_icrf, body.distance_km)
    sun_distance_au = max(
        _length(_subtract(sun_position, body_position)) / AU_KM,
        1e-12,
    )
    if body.body_id == "moon":
        return moon_apparent_magnitude(
            observer_distance_au,
            sun_distance_au,
            phase_angle_deg,
        )
    return planet_apparent_magnitude(
        int(body.naif_id),
        sun_distance_au,
        observer_distance_au,
        phase_angle_deg,
    )


def _scaled(
    direction: tuple[float, float, float],
    distance: float,
) -> tuple[float, float, float]:
    return tuple(component * distance for component in direction)  # type: ignore[return-value]


def _subtract(
    first: tuple[float, float, float],
    second: tuple[float, float, float],
) -> tuple[float, float, float]:
    return tuple(a - b for a, b in zip(first, second, strict=True))  # type: ignore[return-value]


def _dot(
    first: tuple[float, float, float],
    second: tuple[float, float, float],
) -> float:
    return sum(a * b for a, b in zip(first, second, strict=True))


def _length(vector: tuple[float, float, float]) -> float:
    return math.sqrt(_dot(vector, vector))
