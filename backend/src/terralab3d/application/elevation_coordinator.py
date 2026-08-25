"""Async latest-wins lookup for bare observer elevation."""

from __future__ import annotations

import asyncio
import threading
import time
from collections import OrderedDict, deque
from dataclasses import dataclass

from terralab3d.application.ports.terrain import ElevationPort
from terralab3d.domain.elevation.models import ElevationSample
from terralab3d.domain.observer.models import GeoLocation


@dataclass(frozen=True, slots=True)
class ElevationResolution:
    generation: int
    sample: ElevationSample
    duration_ms: float
    cache_hit: bool


class ElevationCoordinator:
    def __init__(self, port: ElevationPort, *, cache_entries: int = 256) -> None:
        self._port = port
        self._cache_entries = max(1, int(cache_entries))
        self._cache: OrderedDict[tuple[float, float], ElevationSample] = OrderedDict()
        self._generation = 0
        self._latest_generation = 0
        self._cancel_event: threading.Event | None = None
        self._durations_ms: deque[float] = deque(maxlen=256)
        self.request_count = 0
        self.cache_hits = 0
        self.stale_count = 0

    async def resolve(self, location: GeoLocation) -> ElevationResolution | None:
        self._generation += 1
        generation = self._generation
        self._latest_generation = generation
        self.request_count += 1
        if self._cancel_event is not None:
            self._cancel_event.set()
        self._cancel_event = threading.Event()
        key = (round(location.latitude_deg, 8), round(location.longitude_deg, 8))
        cached = self._cache.pop(key, None)
        if cached is not None:
            self._cache[key] = cached
            self.cache_hits += 1
            return ElevationResolution(generation, cached, 0.0, True)
        started = time.perf_counter()
        sample = await asyncio.to_thread(
            self._port.elevation,
            location,
            self._cancel_event.is_set,
        )
        duration_ms = (time.perf_counter() - started) * 1000.0
        self._durations_ms.append(duration_ms)
        if generation != self._latest_generation:
            self.stale_count += 1
            return None
        self._cache[key] = sample
        while len(self._cache) > self._cache_entries:
            self._cache.popitem(last=False)
        return ElevationResolution(generation, sample, duration_ms, False)

    def cancel(self) -> None:
        self._latest_generation += 1
        if self._cancel_event is not None:
            self._cancel_event.set()

    def invalidate(self) -> None:
        """Cancel stale work and discard samples tied to an old DEM fingerprint."""

        self.cancel()
        self._cache.clear()

    def metrics(self) -> dict[str, float | int]:
        samples = sorted(self._durations_ms)
        return {
            "bareElevationP50Ms": _percentile(samples, 0.50),
            "bareElevationP95Ms": _percentile(samples, 0.95),
            "bareElevationRequests": self.request_count,
            "bareElevationCacheHits": self.cache_hits,
            "bareElevationStale": self.stale_count,
        }


def _percentile(samples: list[float], fraction: float) -> float:
    if not samples:
        return 0.0
    return float(samples[round((len(samples) - 1) * fraction)])
