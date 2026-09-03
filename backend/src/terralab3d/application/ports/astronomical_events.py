"""Lightweight ephemeris boundary for event geometry and apparent paths."""

from datetime import datetime
from typing import Protocol

from terralab3d.domain.eclipses.models import AstronomicalEventEphemeris
from terralab3d.domain.solar_system.models import ScientificObserver


class AstronomicalEventEphemerisPort(Protocol):
    """Query only requested bodies while sharing the authoritative lifecycle."""

    @property
    def kernel_generation(self) -> str: ...

    def event_ephemeris(
        self,
        utc: datetime,
        observer: ScientificObserver,
        body_ids: tuple[str, ...] = ("sun", "moon"),
        *,
        include_lunar_shadow_geometry: bool = False,
        include_body_orientation: bool = True,
        allow_unknown_radius: bool = False,
    ) -> AstronomicalEventEphemeris: ...
