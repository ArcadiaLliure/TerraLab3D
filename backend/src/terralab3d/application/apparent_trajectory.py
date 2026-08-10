"""Versioned topocentric sky trajectories, distinct from planetocentric orbits."""

from __future__ import annotations

import asyncio
import logging
import struct
import threading
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Awaitable, Callable

from terralab3d.application.astronomical_events import EventSearchCancelled
from terralab3d.application.ports.astronomical_events import (
    AstronomicalEventEphemerisPort,
)
from terralab3d.domain.eclipses.models import ApparentTrajectory, GeometryQuality
from terralab3d.domain.solar_system.models import ScientificObserver

log = logging.getLogger("terralab3d.apparent_trajectory")


@dataclass(frozen=True, slots=True)
class ApparentTrajectoryResource:
    resource_id: str
    version: str
    metadata: dict[str, object]
    payload: bytes


class ApparentTrajectorySampler:
    """Sample requested bodies only and cache by scientific dependencies."""

    def __init__(self, ephemeris: AstronomicalEventEphemerisPort) -> None:
        self._ephemeris = ephemeris
        self._cache: dict[tuple[object, ...], ApparentTrajectory] = {}
        self._generation = 0
        self.compute_count = 0
        self.cache_hit_count = 0
        self.last_compute_ms = 0.0
        self.last_sample_count = 0

    def sample(
        self,
        body_id: str,
        observer: ScientificObserver,
        observer_generation: int,
        start_utc: datetime,
        end_utc: datetime,
        sample_count: int,
        *,
        cancel: threading.Event | None = None,
    ) -> ApparentTrajectory:
        start = _as_utc(start_utc)
        end = _as_utc(end_utc)
        if end <= start:
            raise ValueError("Trajectory interval must be positive")
        if sample_count < 2 or sample_count > 4096:
            raise ValueError("Trajectory sample_count must be in 2..4096")
        key = (
            body_id,
            observer.latitude_deg,
            observer.longitude_deg,
            observer.elevation_m,
            start.isoformat(),
            end.isoformat(),
            sample_count,
            self._ephemeris.kernel_generation,
        )
        cached = self._cache.get(key)
        if cached is not None:
            self.cache_hit_count += 1
            return cached

        started = time.perf_counter()
        duration = (end - start).total_seconds()
        directions = []
        offsets = []
        validity = []
        quality = GeometryQuality.SCIENTIFIC
        for index in range(sample_count):
            if cancel is not None and cancel.is_set():
                raise EventSearchCancelled()
            offset = duration * index / (sample_count - 1)
            offsets.append(offset)
            try:
                sample = self._ephemeris.event_ephemeris(
                    datetime.fromtimestamp(start.timestamp() + offset, timezone.utc),
                    observer,
                    (body_id,),
                )
                body = sample.body(body_id)
                if body is None:
                    raise RuntimeError("Body is absent from trajectory ephemeris")
                directions.append(body.direction_enu)
                validity.append(True)
                if sample.quality is not GeometryQuality.SCIENTIFIC:
                    quality = sample.quality
            except EventSearchCancelled:
                raise
            except Exception:
                directions.append((0.0, 0.0, 0.0))
                validity.append(False)
                quality = GeometryQuality.FALLBACK
        self._generation += 1
        result = ApparentTrajectory(
            body_id=body_id,
            observer_latitude_deg=observer.latitude_deg,
            observer_longitude_deg=observer.longitude_deg,
            observer_elevation_m=observer.elevation_m,
            start_utc=start,
            end_utc=end,
            directions_enu=tuple(directions),
            time_offsets_seconds=tuple(offsets),
            validity=tuple(validity),
            generation=self._generation,
            observer_generation=observer_generation,
            kernel_generation=self._ephemeris.kernel_generation,
            quality=quality,
        )
        if len(self._cache) >= 16:
            self._cache.clear()
        self._cache[key] = result
        self.compute_count += 1
        self.last_compute_ms = (time.perf_counter() - started) * 1000.0
        self.last_sample_count = sample_count
        return result

    @staticmethod
    def encode(trajectory: ApparentTrajectory) -> ApparentTrajectoryResource:
        count = len(trajectory.directions_enu)
        directions = b"".join(
            struct.pack("<fff", *direction) for direction in trajectory.directions_enu
        )
        offsets = b"".join(
            struct.pack("<f", value) for value in trajectory.time_offsets_seconds
        )
        validity = bytes(1 if value else 0 for value in trajectory.validity)
        payload = directions + offsets + validity
        version = (
            f"{trajectory.kernel_generation}:{trajectory.observer_generation}:"
            f"{trajectory.generation}"
        )
        return ApparentTrajectoryResource(
            resource_id=f"apparent-trajectory:{trajectory.body_id}",
            version=version,
            metadata={
                "resourceId": f"apparent-trajectory:{trajectory.body_id}",
                "version": version,
                "role": "apparent_trajectory",
                "bodyId": trajectory.body_id,
                "sampleCount": count,
                "startUtc": _utc_iso(trajectory.start_utc),
                "endUtc": _utc_iso(trajectory.end_utc),
                "frame": "topocentric ENU East/Up/North",
                "generation": trajectory.generation,
                "observerGeneration": trajectory.observer_generation,
                "kernelGeneration": trajectory.kernel_generation,
                "quality": trajectory.quality.value,
                "directionComponentType": "float32",
                "directionComponents": 3,
                "timeOffsetComponentType": "float32",
                "validityComponentType": "uint8",
                "directionByteOffset": 0,
                "timeOffsetByteOffset": count * 12,
                "validityByteOffset": count * 16,
            },
            payload=payload,
        )

    def metrics(self) -> dict[str, int | float]:
        return {
            "trajectory_compute_count": self.compute_count,
            "trajectory_cache_hit_count": self.cache_hit_count,
            "trajectory_compute_ms": self.last_compute_ms,
            "trajectory_sample_count": self.last_sample_count,
        }


TrajectoryPublisher = Callable[[ApparentTrajectoryResource], Awaitable[int | None]]


class ApparentTrajectoryCoordinator:
    """One latest requested trajectory with cooperative stale cancellation."""

    def __init__(
        self,
        sampler: ApparentTrajectorySampler,
        publisher: TrajectoryPublisher,
    ) -> None:
        self._sampler = sampler
        self._publisher = publisher
        self._cancel: threading.Event | None = None
        self._task: asyncio.Task[None] | None = None
        self._tasks: set[asyncio.Task[None]] = set()
        self._request_id = ""
        self.cancel_count = 0
        self.stale_count = 0
        self.last_bridge_bytes = 0

    def request(
        self,
        *,
        request_id: str,
        body_id: str,
        observer: ScientificObserver,
        observer_generation: int,
        start_utc: datetime,
        end_utc: datetime,
        sample_count: int,
    ) -> None:
        if self._cancel is not None:
            self._cancel.set()
            self.cancel_count += 1
        cancel = threading.Event()
        self._cancel = cancel
        self._request_id = request_id
        self._task = asyncio.create_task(
            self._run(
                request_id,
                body_id,
                observer,
                observer_generation,
                start_utc,
                end_utc,
                sample_count,
                cancel,
            ),
            name=f"apparent-trajectory-{request_id}",
        )
        self._tasks.add(self._task)
        self._task.add_done_callback(self._tasks.discard)

    async def close(self) -> None:
        if self._cancel is not None:
            self._cancel.set()
        if self._tasks:
            await asyncio.gather(*tuple(self._tasks), return_exceptions=True)

    def metrics(self) -> dict[str, int | float]:
        return {
            **self._sampler.metrics(),
            "trajectory_cancel_count": self.cancel_count,
            "trajectory_stale_count": self.stale_count,
            "trajectory_bridge_bytes": self.last_bridge_bytes,
        }

    async def _run(
        self,
        request_id: str,
        body_id: str,
        observer: ScientificObserver,
        observer_generation: int,
        start_utc: datetime,
        end_utc: datetime,
        sample_count: int,
        cancel: threading.Event,
    ) -> None:
        try:
            trajectory = await asyncio.to_thread(
                self._sampler.sample,
                body_id,
                observer,
                observer_generation,
                start_utc,
                end_utc,
                sample_count,
                cancel=cancel,
            )
        except EventSearchCancelled:
            return
        except Exception:
            log.exception("Apparent trajectory failed request=%s body=%s", request_id, body_id)
            return
        if cancel.is_set() or request_id != self._request_id:
            self.stale_count += 1
            return
        resource = self._sampler.encode(trajectory)
        published = await self._publisher(resource)
        self.last_bridge_bytes = len(resource.payload) if published is None else published


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        raise ValueError("Trajectory instants must be timezone-aware")
    return value.astimezone(timezone.utc)


def _utc_iso(value: datetime) -> str:
    return _as_utc(value).isoformat().replace("+00:00", "Z")
