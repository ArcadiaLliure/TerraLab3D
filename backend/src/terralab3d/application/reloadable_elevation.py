"""Stable elevation port with safe, atomic adapter replacement."""

from __future__ import annotations

from contextlib import contextmanager
from threading import RLock
from typing import Callable, Iterator

from terralab3d.application.ports.terrain import ElevationPort
from terralab3d.domain.elevation.models import (
    ElevationBatch,
    ElevationBatchRequest,
    ElevationGrid,
    ElevationSample,
    ElevationSourceMetadata,
)
from terralab3d.domain.observer.models import GeoLocation
from terralab3d.domain.terrain.models import TerrainTileRequest


class ReloadableElevationPort:
    """Keeps one public port stable while in-flight reads finish on old adapters."""

    def __init__(self, initial: ElevationPort) -> None:
        self._current = initial
        self._lock = RLock()
        self._readers: dict[int, int] = {}
        self._retired: dict[int, ElevationPort] = {}
        self._closed = False
        self._generation = 1

    @property
    def generation(self) -> int:
        with self._lock:
            return self._generation

    def reload(self, factory: Callable[[], ElevationPort]) -> ElevationSourceMetadata:
        candidate = factory()
        try:
            metadata = candidate.metadata()
        except Exception:
            candidate.close()
            raise
        close_now: ElevationPort | None = None
        with self._lock:
            if self._closed:
                candidate.close()
                raise RuntimeError("Elevation port is closed")
            previous = self._current
            self._current = candidate
            self._generation += 1
            previous_key = id(previous)
            if self._readers.get(previous_key, 0) == 0:
                close_now = previous
            else:
                self._retired[previous_key] = previous
        if close_now is not None:
            close_now.close()
        return metadata

    def elevation(
        self,
        location: GeoLocation,
        cancellation_check: Callable[[], bool] | None = None,
    ) -> ElevationSample:
        with self._lease() as port:
            return port.elevation(location, cancellation_check)

    def sample_points(self, request: ElevationBatchRequest) -> ElevationBatch:
        with self._lease() as port:
            return port.sample_points(request)

    def metadata(self) -> ElevationSourceMetadata:
        with self._lease() as port:
            return port.metadata()

    def terrain_grid(self, request: TerrainTileRequest) -> ElevationGrid:
        with self._lease() as port:
            return port.terrain_grid(request)

    def close(self) -> None:
        with self._lock:
            if self._closed:
                return
            self._closed = True
            ports = [self._current, *self._retired.values()]
            self._retired.clear()
        for port in dict.fromkeys(ports):
            port.close()

    @contextmanager
    def _lease(self) -> Iterator[ElevationPort]:
        with self._lock:
            if self._closed:
                raise RuntimeError("Elevation port is closed")
            port = self._current
            key = id(port)
            self._readers[key] = self._readers.get(key, 0) + 1
        try:
            yield port
        finally:
            retired: ElevationPort | None = None
            with self._lock:
                remaining = self._readers[key] - 1
                if remaining:
                    self._readers[key] = remaining
                else:
                    self._readers.pop(key, None)
                    retired = self._retired.pop(key, None)
            if retired is not None:
                retired.close()
