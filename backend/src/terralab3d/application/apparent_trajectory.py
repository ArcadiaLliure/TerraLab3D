"""Versioned apparent trajectories classified against the active horizon."""

from __future__ import annotations

import asyncio
import logging
import math
import struct
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Awaitable

from terralab3d.application.astronomical_events import EventSearchCancelled
from terralab3d.application.observable_positions import ObservablePositionService
from terralab3d.application.ports.astronomical_events import (
    AstronomicalEventEphemerisPort,
)
from terralab3d.application.ports.observable_positions import ObservablePositionPort
from terralab3d.domain.eclipses.models import ApparentTrajectory, GeometryQuality
from terralab3d.domain.geometry import CartesianDirection
from terralab3d.domain.horizon.models import HorizonProfile, HorizonQuality
from terralab3d.domain.solar_system.models import ScientificObserver
from terralab3d.domain.visibility.calculations import (
    build_segments,
    classify_visibility,
    interval_classification,
    is_astronomically_circumpolar,
)
from terralab3d.domain.visibility.models import (
    ApparentPosition,
    HorizonProvenance,
    HorizonReading,
    ObservableFamily,
    ObservableObject,
    TrajectoryEvent,
    TrajectoryEventKind,
    TrajectoryResolution,
    TrajectorySample,
    VisibleTrajectory,
)

log = logging.getLogger("terralab3d.apparent_trajectory")


@dataclass(frozen=True, slots=True)
class ApparentTrajectoryResource:
    resource_id: str
    version: str
    metadata: dict[str, object]
    payload: bytes


@dataclass(frozen=True, slots=True)
class _SamplingPolicy:
    resolution: TrajectoryResolution
    probe_depth: int
    adaptive_depth: int
    temporal_tolerance_seconds: float
    angular_tolerance_deg: float
    maximum_angular_step_deg: float
    near_horizon_deg: float

    @classmethod
    def for_resolution(cls, resolution: TrajectoryResolution) -> "_SamplingPolicy":
        if resolution is TrajectoryResolution.DETAILED:
            return cls(resolution, 2, 6, 0.25, 0.01, 1.0, 1.0)
        return cls(resolution, 2, 4, 1.0, 0.05, 2.5, 2.0)


class ApparentTrajectorySampler:
    """Sample one observable, reuse scientific adapters and classify visibility."""

    def __init__(
        self,
        ephemeris: AstronomicalEventEphemerisPort | None,
        *,
        position_port: ObservablePositionPort | None = None,
        horizon_profile: Callable[[], HorizonProfile | None] | None = None,
    ) -> None:
        self._ephemeris = ephemeris
        self._positions = position_port or ObservablePositionService(ephemeris)
        self._horizon_profile = horizon_profile or (lambda: None)
        self._cache: dict[tuple[object, ...], ApparentTrajectory | VisibleTrajectory] = {}
        self._generation = 0
        self._generation_lock = threading.Lock()
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
        """Preserve the Pas-9 body trajectory and byte-for-byte wire contract."""

        if self._ephemeris is None:
            raise ValueError("Solar-system trajectories require an ephemeris adapter")
        start, end = _validated_interval(start_utc, end_utc, sample_count)
        key = (
            "legacy",
            body_id,
            observer.latitude_deg,
            observer.longitude_deg,
            observer.elevation_m,
            observer_generation,
            start.isoformat(),
            end.isoformat(),
            sample_count,
            self._ephemeris.kernel_generation,
        )
        cached = self._cache.get(key)
        if isinstance(cached, ApparentTrajectory):
            self.cache_hit_count += 1
            return cached

        started = time.perf_counter()
        duration = (end - start).total_seconds()
        directions: list[tuple[float, float, float]] = []
        offsets: list[float] = []
        validity: list[bool] = []
        quality = GeometryQuality.SCIENTIFIC
        for index in range(sample_count):
            _raise_if_cancelled(cancel)
            offset = duration * index / (sample_count - 1)
            offsets.append(offset)
            try:
                snapshot = self._ephemeris.event_ephemeris(
                    start + timedelta(seconds=offset),
                    observer,
                    (body_id,),
                )
                body = snapshot.body(body_id)
                if body is None:
                    raise RuntimeError("Body is absent from trajectory ephemeris")
                directions.append(body.direction_enu)
                validity.append(True)
                if snapshot.quality is not GeometryQuality.SCIENTIFIC:
                    quality = snapshot.quality
            except EventSearchCancelled:
                raise
            except Exception:
                directions.append((0.0, 0.0, 0.0))
                validity.append(False)
                quality = GeometryQuality.FALLBACK
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
            generation=self._next_generation(),
            observer_generation=observer_generation,
            kernel_generation=self._ephemeris.kernel_generation,
            quality=quality,
        )
        self._remember(key, result)
        self._record_compute(started, sample_count)
        return result

    def sample_visibility(
        self,
        observable: ObservableObject,
        observer: ScientificObserver,
        observer_generation: int,
        start_utc: datetime,
        end_utc: datetime,
        sample_count: int,
        *,
        resolution: TrajectoryResolution = TrajectoryResolution.AUTOMATIC,
        use_terrain_horizon: bool = True,
        cancel: threading.Event | None = None,
    ) -> VisibleTrajectory:
        """Build an adaptive, versioned local-visibility trajectory."""

        start, end = _validated_interval(start_utc, end_utc, sample_count)
        if not observable.has_apparent_position:
            raise ValueError(f"Observable {observable.object_id!r} has no position capability")
        policy = _SamplingPolicy.for_resolution(resolution)
        profile = self._horizon_profile() if use_terrain_horizon else None
        if profile is not None:
            location_matches = (
                abs(profile.latitude_deg - observer.latitude_deg) < 0.002
                and abs(profile.longitude_deg - observer.longitude_deg) < 0.002
            )
            if not location_matches and profile.observer_generation != observer_generation:
                # Never compare a new distant observer against a resident profile belonging
                # to the previous location. The flat fallback remains explicit.
                profile = None
        horizon_version = profile.version if profile is not None else 0
        horizon_quality = (
            profile.quality.value if profile is not None else HorizonQuality.FLAT_FALLBACK.value
        )
        key = (
            "visibility-v1",
            observable,
            observer.latitude_deg,
            observer.longitude_deg,
            observer.elevation_m,
            observer_generation,
            start.isoformat(),
            end.isoformat(),
            sample_count,
            resolution.value,
            use_terrain_horizon,
            horizon_version,
            self._positions.generation,
        )
        cached = self._cache.get(key)
        if isinstance(cached, VisibleTrajectory):
            self.cache_hit_count += 1
            return cached

        started = time.perf_counter()
        duration = (end - start).total_seconds()
        maximum_samples = min(4096, max(sample_count * 8, sample_count + 1))
        sampled: dict[float, TrajectorySample] = {}

        def evaluate(offset_seconds: float) -> TrajectorySample:
            rounded = max(0.0, min(duration, float(offset_seconds)))
            cache_key = round(rounded, 9)
            existing = sampled.get(cache_key)
            if existing is not None:
                return existing
            _raise_if_cancelled(cancel)
            instant = start + timedelta(seconds=rounded)
            try:
                apparent = self._positions.position_at(observable, instant, observer)
            except EventSearchCancelled:
                raise
            except Exception:
                apparent = ApparentPosition(
                    instant_utc=instant,
                    direction_enu=CartesianDirection(0.0, 0.0, 0.0),
                    azimuth_deg=0.0,
                    altitude_deg=-90.0,
                    valid=False,
                    quality="unavailable",
                )
            horizon = _horizon_reading(profile, apparent.azimuth_deg, use_terrain_horizon)
            visibility = classify_visibility(
                apparent.altitude_deg,
                horizon.elevation_deg,
                horizon.provenance,
                valid=apparent.valid,
            )
            sample = TrajectorySample(
                instant_utc=instant,
                offset_seconds=rounded,
                apparent=apparent,
                horizon_elevation_deg=horizon.elevation_deg,
                horizon_provenance=horizon.provenance,
                visibility=visibility,
                # Visibility cannot start below the astronomical horizon even
                # when a descending terrain profile has a negative elevation.
                margin_deg=apparent.altitude_deg - max(0.0, horizon.elevation_deg),
            )
            sampled[cache_key] = sample
            return sample

        base_offsets = [duration * index / (sample_count - 1) for index in range(sample_count)]
        for offset in base_offsets:
            evaluate(offset)

        # Always probe to depth two so a short crossing can be found even when
        # both coarse endpoints have the same sign.
        for left, right in zip(base_offsets, base_offsets[1:]):
            _probe_interval(evaluate, left, right, policy.probe_depth, maximum_samples, sampled)

        changed = True
        depth = 0
        while changed and depth < policy.adaptive_depth and len(sampled) < maximum_samples:
            changed = False
            ordered = sorted(sampled.values(), key=lambda value: value.offset_seconds)
            for left, right in zip(ordered, ordered[1:]):
                if len(sampled) >= maximum_samples:
                    break
                if _needs_refinement(left, right, policy):
                    before = len(sampled)
                    evaluate((left.offset_seconds + right.offset_seconds) * 0.5)
                    changed = changed or len(sampled) > before
            depth += 1

        ordered = sorted(sampled.values(), key=lambda value: value.offset_seconds)
        events: list[TrajectoryEvent] = []
        refined: list[TrajectorySample] = list(ordered)
        for left, right in zip(ordered, ordered[1:]):
            if not _crossing_is_valid(left, right):
                continue
            crossing = _refine_crossing(evaluate, left, right, policy, cancel)
            refined.append(crossing)
            kind = (
                TrajectoryEventKind.RISE
                if left.margin_deg < right.margin_deg
                else TrajectoryEventKind.SET
            )
            events.append(_event(kind, crossing))

        refined = _unique_sorted_samples(refined)
        events.extend(_tangent_events(refined, policy.angular_tolerance_deg))
        events.sort(key=lambda value: value.instant_utc)
        result = VisibleTrajectory(
            observable=observable,
            observer_latitude_deg=observer.latitude_deg,
            observer_longitude_deg=observer.longitude_deg,
            observer_elevation_m=observer.elevation_m,
            start_utc=start,
            end_utc=end,
            samples=tuple(refined),
            segments=build_segments(refined),
            events=tuple(events),
            interval_classification=interval_classification(refined),
            astronomically_circumpolar=is_astronomically_circumpolar(
                observable.family,
                refined,
                duration,
                angular_tolerance_deg=policy.angular_tolerance_deg,
            ),
            generation=self._next_generation(),
            observer_generation=observer_generation,
            kernel_generation=self._positions.generation,
            horizon_version=horizon_version,
            horizon_quality=horizon_quality,
            resolution=resolution,
            temporal_tolerance_seconds=policy.temporal_tolerance_seconds,
            angular_tolerance_deg=policy.angular_tolerance_deg,
            compute_ms=(time.perf_counter() - started) * 1000.0,
        )
        self._remember(key, result)
        self._record_compute(started, len(refined))
        return result

    @staticmethod
    def encode(trajectory: ApparentTrajectory) -> ApparentTrajectoryResource:
        """Encode the original Pas-9 layout without appending new arrays."""

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

    @staticmethod
    def encode_visibility(
        trajectory: VisibleTrajectory,
        request_id: str,
    ) -> ApparentTrajectoryResource:
        """Append visibility arrays while retaining every Pas-9 offset."""

        count = len(trajectory.samples)
        directions = b"".join(
            struct.pack(
                "<fff",
                sample.apparent.direction_enu.x,
                sample.apparent.direction_enu.y,
                sample.apparent.direction_enu.z,
            )
            for sample in trajectory.samples
        )
        offsets = b"".join(struct.pack("<f", sample.offset_seconds) for sample in trajectory.samples)
        validity = bytes(1 if sample.apparent.valid else 0 for sample in trajectory.samples)
        visibility = bytes(_visibility_code(sample.visibility.value) for sample in trajectory.samples)
        provenance = bytes(
            _provenance_code(sample.horizon_provenance.value) for sample in trajectory.samples
        )
        payload = directions + offsets + validity + visibility + provenance
        object_id = trajectory.observable.object_id
        version = (
            f"visibility-v1:{trajectory.kernel_generation}:{trajectory.observer_generation}:"
            f"{trajectory.horizon_version}:{trajectory.generation}"
        )
        visibility_offset = count * 17
        provenance_offset = visibility_offset + count
        qualities = {sample.apparent.quality for sample in trajectory.samples if sample.apparent.valid}
        quality = "scientific" if qualities == {"scientific"} else "fallback"
        return ApparentTrajectoryResource(
            resource_id=f"apparent-trajectory:{object_id}",
            version=version,
            metadata={
                "resourceId": f"apparent-trajectory:{object_id}",
                "version": version,
                "role": "apparent_trajectory",
                "contractVersion": 2,
                "requestId": request_id,
                "bodyId": trajectory.observable.body_id or object_id,
                "objectId": object_id,
                "objectFamily": trajectory.observable.family.value,
                "displayName": trajectory.observable.display_name,
                "sampleCount": count,
                "startUtc": _utc_iso(trajectory.start_utc),
                "endUtc": _utc_iso(trajectory.end_utc),
                "frame": "topocentric ENU East/Up/North",
                "generation": trajectory.generation,
                "observerGeneration": trajectory.observer_generation,
                "kernelGeneration": trajectory.kernel_generation,
                "quality": quality,
                "horizonVersion": trajectory.horizon_version,
                "horizonQuality": trajectory.horizon_quality,
                "resolution": trajectory.resolution.value,
                "intervalClassification": trajectory.interval_classification.value,
                "astronomicallyCircumpolar": trajectory.astronomically_circumpolar,
                "temporalToleranceSeconds": trajectory.temporal_tolerance_seconds,
                "angularToleranceDeg": trajectory.angular_tolerance_deg,
                "computeMs": trajectory.compute_ms,
                "directionComponentType": "float32",
                "directionComponents": 3,
                "timeOffsetComponentType": "float32",
                "validityComponentType": "uint8",
                "visibilityComponentType": "uint8",
                "horizonProvenanceComponentType": "uint8",
                "directionByteOffset": 0,
                "timeOffsetByteOffset": count * 12,
                "validityByteOffset": count * 16,
                "visibilityByteOffset": visibility_offset,
                "horizonProvenanceByteOffset": provenance_offset,
                "segments": [
                    {
                        "startIndex": segment.start_index,
                        "endIndex": segment.end_index,
                        "visibility": segment.visibility.value,
                        "horizonProvenance": segment.horizon_provenance.value,
                    }
                    for segment in trajectory.segments
                ],
                "events": [
                    {
                        "kind": event.kind.value,
                        "instantUtc": _utc_iso(event.instant_utc),
                        "directionENU": [
                            event.direction_enu.x,
                            event.direction_enu.y,
                            event.direction_enu.z,
                        ],
                        "azimuthDeg": event.azimuth_deg,
                        "altitudeDeg": event.altitude_deg,
                        "horizonElevationDeg": event.horizon_elevation_deg,
                        "horizonProvenance": event.horizon_provenance.value,
                    }
                    for event in trajectory.events
                ],
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

    def _next_generation(self) -> int:
        with self._generation_lock:
            self._generation += 1
            return self._generation

    def _remember(
        self,
        key: tuple[object, ...],
        trajectory: ApparentTrajectory | VisibleTrajectory,
    ) -> None:
        if len(self._cache) >= 16:
            self._cache.clear()
        self._cache[key] = trajectory

    def _record_compute(self, started: float, sample_count: int) -> None:
        self.compute_count += 1
        self.last_compute_ms = (time.perf_counter() - started) * 1000.0
        self.last_sample_count = sample_count


TrajectoryPublisher = Callable[[ApparentTrajectoryResource], Awaitable[int | None]]


class ApparentTrajectoryCoordinator:
    """One latest requested trajectory with cooperative stale cancellation."""

    def __init__(self, sampler: ApparentTrajectorySampler, publisher: TrajectoryPublisher) -> None:
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
        observer: ScientificObserver,
        observer_generation: int,
        start_utc: datetime,
        end_utc: datetime,
        sample_count: int,
        observable: ObservableObject | None = None,
        body_id: str | None = None,
        resolution: TrajectoryResolution = TrajectoryResolution.AUTOMATIC,
        use_terrain_horizon: bool = True,
    ) -> None:
        if observable is None:
            if not body_id:
                raise ValueError("Trajectory request requires observable or body_id")
            observable = ObservableObject(
                object_id=body_id,
                family=(
                    ObservableFamily.SATELLITE
                    if body_id.startswith("naif-")
                    else ObservableFamily.SOLAR_SYSTEM
                ),
                display_name=body_id,
                body_id=body_id,
            )
        if self._cancel is not None:
            self._cancel.set()
            self.cancel_count += 1
        cancel = threading.Event()
        self._cancel = cancel
        self._request_id = request_id
        self._task = asyncio.create_task(
            self._run(
                request_id,
                observable,
                observer,
                observer_generation,
                start_utc,
                end_utc,
                sample_count,
                resolution,
                use_terrain_horizon,
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
        observable: ObservableObject,
        observer: ScientificObserver,
        observer_generation: int,
        start_utc: datetime,
        end_utc: datetime,
        sample_count: int,
        resolution: TrajectoryResolution,
        use_terrain_horizon: bool,
        cancel: threading.Event,
    ) -> None:
        try:
            trajectory = await asyncio.to_thread(
                self._sampler.sample_visibility,
                observable,
                observer,
                observer_generation,
                start_utc,
                end_utc,
                sample_count,
                resolution=resolution,
                use_terrain_horizon=use_terrain_horizon,
                cancel=cancel,
            )
        except EventSearchCancelled:
            return
        except Exception:
            log.exception(
                "Apparent trajectory failed request=%s object=%s",
                request_id,
                observable.object_id,
            )
            return
        if cancel.is_set() or request_id != self._request_id:
            self.stale_count += 1
            return
        resource = self._sampler.encode_visibility(trajectory, request_id)
        published = await self._publisher(resource)
        self.last_bridge_bytes = len(resource.payload) if published is None else published
        log.info(
            "MGP: [trajectory] [published] [request=%s object=%s samples=%d bytes=%d ms=%.1f]",
            request_id,
            observable.object_id,
            len(trajectory.samples),
            self.last_bridge_bytes,
            trajectory.compute_ms,
        )


def observable_from_message(data: dict[str, object]) -> ObservableObject:
    """Validate the bridge DTO without leaking UI models into the domain."""

    payload = data.get("observable")
    if not isinstance(payload, dict):
        body_id = str(data.get("bodyId") or "").strip()
        if not body_id:
            raise ValueError("Trajectory observable is missing")
        return ObservableObject(
            object_id=body_id,
            family=(
                ObservableFamily.SATELLITE
                if body_id.startswith("naif-")
                else ObservableFamily.SOLAR_SYSTEM
            ),
            display_name=body_id,
            body_id=body_id,
        )
    family = ObservableFamily(str(payload.get("family") or ""))
    object_id = str(payload.get("objectId") or payload.get("bodyId") or "").strip()
    if not object_id:
        raise ValueError("Observable objectId is required")
    body_id = payload.get("bodyId")
    ra = payload.get("rightAscensionDeg")
    dec = payload.get("declinationDeg")
    observable = ObservableObject(
        object_id=object_id,
        family=family,
        display_name=str(payload.get("displayName") or object_id),
        body_id=str(body_id) if body_id is not None else None,
        right_ascension_deg=float(ra) if ra is not None else None,
        declination_deg=float(dec) if dec is not None else None,
        frame=str(payload.get("frame") or "ICRS/J2000"),
    )
    if observable.right_ascension_deg is not None and not math.isfinite(observable.right_ascension_deg):
        raise ValueError("rightAscensionDeg must be finite")
    if observable.declination_deg is not None and not math.isfinite(observable.declination_deg):
        raise ValueError("declinationDeg must be finite")
    if observable.right_ascension_deg is not None and not 0.0 <= observable.right_ascension_deg < 360.0:
        raise ValueError("rightAscensionDeg must be in [0, 360)")
    if observable.declination_deg is not None and not -90.0 <= observable.declination_deg <= 90.0:
        raise ValueError("declinationDeg must be in [-90, 90]")
    if not observable.has_apparent_position:
        raise ValueError(f"Observable family {family.value} has no available position")
    return observable


def _probe_interval(
    evaluate: Callable[[float], TrajectorySample],
    left: float,
    right: float,
    depth: int,
    maximum_samples: int,
    sampled: dict[float, TrajectorySample],
) -> None:
    if depth <= 0 or len(sampled) >= maximum_samples:
        return
    midpoint = (left + right) * 0.5
    evaluate(midpoint)
    _probe_interval(evaluate, left, midpoint, depth - 1, maximum_samples, sampled)
    _probe_interval(evaluate, midpoint, right, depth - 1, maximum_samples, sampled)


def _needs_refinement(
    left: TrajectorySample,
    right: TrajectorySample,
    policy: _SamplingPolicy,
) -> bool:
    duration = right.offset_seconds - left.offset_seconds
    if duration <= policy.temporal_tolerance_seconds * 2.0:
        return False
    if left.visibility is not right.visibility:
        return True
    if left.horizon_provenance is not right.horizon_provenance:
        return True
    if min(abs(left.margin_deg), abs(right.margin_deg)) <= policy.near_horizon_deg:
        return True
    return _angular_separation_deg(left.apparent, right.apparent) > policy.maximum_angular_step_deg


def _crossing_is_valid(left: TrajectorySample, right: TrajectorySample) -> bool:
    if not left.apparent.valid or not right.apparent.valid:
        return False
    if (
        left.horizon_provenance is HorizonProvenance.INSUFFICIENT
        or right.horizon_provenance is HorizonProvenance.INSUFFICIENT
    ):
        return False
    return (left.margin_deg < 0.0 <= right.margin_deg) or (
        right.margin_deg < 0.0 <= left.margin_deg
    )


def _refine_crossing(
    evaluate: Callable[[float], TrajectorySample],
    left: TrajectorySample,
    right: TrajectorySample,
    policy: _SamplingPolicy,
    cancel: threading.Event | None,
) -> TrajectorySample:
    low = left
    high = right
    for _ in range(48):
        _raise_if_cancelled(cancel)
        if high.offset_seconds - low.offset_seconds <= policy.temporal_tolerance_seconds:
            break
        midpoint = evaluate((low.offset_seconds + high.offset_seconds) * 0.5)
        if abs(midpoint.margin_deg) <= 1.0e-12:
            return midpoint
        if (low.margin_deg < 0.0) == (midpoint.margin_deg < 0.0):
            low = midpoint
        else:
            high = midpoint
    return evaluate((low.offset_seconds + high.offset_seconds) * 0.5)


def _tangent_events(
    samples: list[TrajectorySample],
    angular_tolerance_deg: float,
) -> list[TrajectoryEvent]:
    events: list[TrajectoryEvent] = []
    for left, middle, right in zip(samples, samples[1:], samples[2:]):
        if any(
            sample.horizon_provenance is HorizonProvenance.INSUFFICIENT
            or not sample.apparent.valid
            for sample in (left, middle, right)
        ):
            continue
        same_side = (left.margin_deg < 0.0) == (right.margin_deg < 0.0)
        local_minimum = abs(middle.margin_deg) < min(abs(left.margin_deg), abs(right.margin_deg))
        if same_side and local_minimum and abs(middle.margin_deg) <= angular_tolerance_deg:
            events.append(_event(TrajectoryEventKind.TANGENT, middle))
    return events


def _event(kind: TrajectoryEventKind, sample: TrajectorySample) -> TrajectoryEvent:
    return TrajectoryEvent(
        kind=kind,
        instant_utc=sample.instant_utc,
        direction_enu=sample.apparent.direction_enu,
        azimuth_deg=sample.apparent.azimuth_deg,
        altitude_deg=sample.apparent.altitude_deg,
        horizon_elevation_deg=sample.horizon_elevation_deg,
        horizon_provenance=sample.horizon_provenance,
    )


def _horizon_reading(
    profile: HorizonProfile | None,
    azimuth_deg: float,
    use_terrain_horizon: bool,
) -> HorizonReading:
    if not use_terrain_horizon or profile is None or profile.quality is HorizonQuality.FLAT_FALLBACK:
        return HorizonReading(0.0, HorizonProvenance.FALLBACK_ASTRONOMICAL)
    if profile.quality in (HorizonQuality.UNAVAILABLE, HorizonQuality.ERROR) or profile.sample_count == 0:
        return HorizonReading(0.0, HorizonProvenance.INSUFFICIENT)
    position = ((float(azimuth_deg) - profile.azimuth_start_deg) % 360.0) / profile.angular_step_deg
    left_floor = math.floor(position)
    left = left_floor % profile.sample_count
    right = (left + 1) % profile.sample_count
    if not profile.valid_mask[left] or not profile.valid_mask[right]:
        return HorizonReading(0.0, HorizonProvenance.INSUFFICIENT)
    fraction = position - left_floor
    elevation = float(profile.horizon_elevation_deg[left]) + (
        float(profile.horizon_elevation_deg[right]) - float(profile.horizon_elevation_deg[left])
    ) * fraction
    return HorizonReading(elevation, HorizonProvenance.REAL)


def _angular_separation_deg(left: ApparentPosition, right: ApparentPosition) -> float:
    if not left.valid or not right.valid:
        return 0.0
    a = left.direction_enu
    b = right.direction_enu
    dot = a.x * b.x + a.y * b.y + a.z * b.z
    length_a = math.sqrt(a.x * a.x + a.y * a.y + a.z * a.z)
    length_b = math.sqrt(b.x * b.x + b.y * b.y + b.z * b.z)
    if length_a <= 0.0 or length_b <= 0.0:
        return 0.0
    return math.degrees(math.acos(max(-1.0, min(1.0, dot / (length_a * length_b)))))


def _unique_sorted_samples(samples: list[TrajectorySample]) -> list[TrajectorySample]:
    unique = {round(sample.offset_seconds, 9): sample for sample in samples}
    return sorted(unique.values(), key=lambda value: value.offset_seconds)


def _validated_interval(
    start_utc: datetime,
    end_utc: datetime,
    sample_count: int,
) -> tuple[datetime, datetime]:
    start = _as_utc(start_utc)
    end = _as_utc(end_utc)
    if end <= start:
        raise ValueError("Trajectory interval must be positive")
    if sample_count < 2 or sample_count > 4096:
        raise ValueError("Trajectory sample_count must be in 2..4096")
    return start, end


def _raise_if_cancelled(cancel: threading.Event | None) -> None:
    if cancel is not None and cancel.is_set():
        raise EventSearchCancelled()


def _visibility_code(value: str) -> int:
    return {
        "visible": 0,
        "terrain_occluded": 1,
        "below_astronomical_horizon": 2,
        "insufficient_data": 3,
    }[value]


def _provenance_code(value: str) -> int:
    return {"real": 0, "fallback_astronomical": 1, "insufficient": 2}[value]


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        raise ValueError("Trajectory instants must be timezone-aware")
    return value.astimezone(timezone.utc)


def _utc_iso(value: datetime) -> str:
    return _as_utc(value).isoformat().replace("+00:00", "Z")
