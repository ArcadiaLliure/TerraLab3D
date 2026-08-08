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

    @property
    def lunar_orientation_kernel_load_count(self) -> int: ...

    def snapshot(
        self,
        utc: datetime,
        observer: ScientificObserver,
    ) -> SolarSystemSnapshot: ...

    def close(self) -> None: ...
