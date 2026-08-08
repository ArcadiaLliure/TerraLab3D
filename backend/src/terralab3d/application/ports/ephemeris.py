"""Boundary for authoritative, renderer-neutral ephemerides."""

from datetime import datetime
from typing import Protocol

from terralab3d.domain.solar_system.models import (
    EphemerisMetadata,
    ScientificObserver,
    SolarSystemSnapshot,
)


class EphemerisPort(Protocol):
    @property
    def metadata(self) -> EphemerisMetadata: ...

    def snapshot(
        self,
        utc: datetime,
        observer: ScientificObserver,
    ) -> SolarSystemSnapshot: ...

    def close(self) -> None: ...
