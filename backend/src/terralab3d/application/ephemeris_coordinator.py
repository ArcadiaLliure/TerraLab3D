"""Latest-wins orchestration for ephemeris snapshots outside the render loop."""

from __future__ import annotations

import asyncio
import logging
from collections import deque
from dataclasses import dataclass
from datetime import datetime
from typing import Awaitable, Callable

from terralab3d.application.ports.ephemeris import EphemerisPort
from terralab3d.domain.solar_system.models import ScientificObserver, SolarSystemSnapshot
from terralab3d.domain.horizon.models import HorizonProfile
from terralab3d.domain.horizon.services import HorizonVisibilityEnricher

SnapshotPublisher = Callable[[SolarSystemSnapshot], Awaitable[int | None]]
log = logging.getLogger("terralab3d.ephemeris.coordinator")


@dataclass(frozen=True, slots=True)
class _Request:
    sequence: int
    generation_id: int
    observer_generation: int
    utc: datetime
    observer: ScientificObserver


class EphemerisCoordinator:
    """Maintains exactly one calculation in flight and one latest pending request."""

    def __init__(
        self,
        port: EphemerisPort,
        publisher: SnapshotPublisher,
        horizon_profile: Callable[[], HorizonProfile | None] | None = None,
    ) -> None:
        self._port = port
        self._publisher = publisher
        self._horizon_profile = horizon_profile
        self._horizon_enricher = HorizonVisibilityEnricher()
        self._generation = 0
        self._latest_requested_generation = 0
        self._pending: _Request | None = None
        self._task: asyncio.Task[None] | None = None
        self._closed = False
        self.request_count = 0
        self.coalesced_count = 0
        self.stale_count = 0
        self.bridge_bytes = 0
        self.last_bridge_bytes = 0
        self._compute_ms: deque[float] = deque(maxlen=256)
        self._lunar_orientation_compute_ms: deque[float] = deque(maxlen=256)
        self._orientation_batch_compute_ms: deque[float] = deque(maxlen=256)

    def request(
        self,
        utc: datetime,
        observer: ScientificObserver,
        observer_generation: int,
        *,
        generation_id: int | None = None,
    ) -> int:
        if self._closed:
            raise RuntimeError("EphemerisCoordinator is closed")
        self._generation += 1
        self._latest_requested_generation = self._generation
        effective_generation = self._generation if generation_id is None else generation_id
        request = _Request(
            self._generation,
            effective_generation,
            observer_generation,
            utc,
            observer,
        )
        self.request_count += 1
        if self._task is not None:
            if self._pending is not None:
                self.coalesced_count += 1
            self._pending = request
        else:
            self._pending = request
            self._task = asyncio.create_task(self._drain(), name="ephemeris-latest-wins")
        return request.generation_id

    async def wait_idle(self) -> None:
        task = self._task
        if task is not None:
            await asyncio.shield(task)

    async def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        self._pending = None
        task = self._task
        if task is not None:
            await task
        self._port.close()

    def metrics(self) -> dict[str, float | int]:
        samples = sorted(self._compute_ms)
        return {
            "ephemeris_request_count": self.request_count,
            "ephemeris_coalesced_count": self.coalesced_count,
            "ephemeris_stale_count": self.stale_count,
            "ephemeris_compute_ms_p50": _percentile(samples, 0.50),
            "ephemeris_compute_ms_p95": _percentile(samples, 0.95),
            "lunar_orientation_compute_ms_p50": _percentile(
                sorted(self._lunar_orientation_compute_ms), 0.50
            ),
            "lunar_orientation_compute_ms_p95": _percentile(
                sorted(self._lunar_orientation_compute_ms), 0.95
            ),
            "orientation_batch_duration_ms_p50": _percentile(
                sorted(self._orientation_batch_compute_ms), 0.50
            ),
            "orientation_batch_duration_ms_p95": _percentile(
                sorted(self._orientation_batch_compute_ms), 0.95
            ),
            "spice_query_count": getattr(self._port, "query_count", 0),
            "spice_query_duration_ms": getattr(
                self._port, "last_query_duration_ms", 0.0
            ),
            "orientation_query_count": getattr(
                self._port, "orientation_query_count", 0
            ),
            "moon_kernel_load_count": getattr(
                self._port, "lunar_orientation_kernel_load_count", 0
            ),
            "solar_system_bridge_bytes": self.last_bridge_bytes,
            "solar_system_bridge_bytes_total": self.bridge_bytes,
        }

    async def _drain(self) -> None:
        try:
            while self._pending is not None and not self._closed:
                request = self._pending
                self._pending = None
                try:
                    snapshot = await asyncio.to_thread(
                        self._port.snapshot,
                        request.utc,
                        request.observer,
                    )
                except Exception:
                    log.exception(
                        "Ephemeris calculation failed for generation %d",
                        request.generation_id,
                    )
                    continue
                self._compute_ms.append(snapshot.compute_ms)
                if snapshot.moon is not None and snapshot.moon.orientation is not None:
                    self._lunar_orientation_compute_ms.append(snapshot.moon.orientation.compute_ms)
                orientation_times = [
                    item.orientation.compute_ms
                    for item in (snapshot.planets + snapshot.satellites)
                    if item.orientation is not None
                ]
                self._orientation_batch_compute_ms.append(sum(orientation_times))
                if self._closed:
                    break
                if request.sequence < self._latest_requested_generation:
                    self.stale_count += 1
                    continue
                published = snapshot.with_generation(
                    request.generation_id,
                    request.observer_generation,
                )
                profile = self._horizon_profile() if self._horizon_profile is not None else None
                if profile is not None and profile.observer_generation == request.observer_generation:
                    published = self._horizon_enricher.enrich(published, profile)
                try:
                    byte_count = await self._publisher(published)
                except Exception:
                    log.exception(
                        "Ephemeris publication failed for generation %d",
                        request.generation_id,
                    )
                    continue
                if byte_count is not None:
                    self.last_bridge_bytes = byte_count
                    self.bridge_bytes += byte_count
        finally:
            self._task = None


def _percentile(samples: list[float], fraction: float) -> float:
    if not samples:
        return 0.0
    index = round((len(samples) - 1) * fraction)
    return float(samples[index])
