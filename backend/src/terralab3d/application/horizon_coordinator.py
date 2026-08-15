"""Cancelable latest-wins orchestration from DEM batches to binary horizon resources."""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import math
import threading
import time
from collections import OrderedDict, deque
from dataclasses import asdict, replace
from typing import Awaitable, Callable

import numpy as np

from terralab3d.application.ports.terrain import ElevationPort, RadialCoordinateProjector
from terralab3d.application.terrain_mesh_builder import (
    TERRAIN_MESH_RESOURCE_ID,
    TERRAIN_MESH_VERSION,
    TerrainMeshBuffers,
    TerrainMeshBuilder,
)
from terralab3d.domain.elevation.models import ElevationBatchRequest
from terralab3d.domain.horizon.calculations import (
    adaptive_distances_m,
    mask_after_consecutive_misses,
    reduce_horizon_samples,
    resolve_visible_radius_m,
)
from terralab3d.domain.horizon.models import (
    EARTH_RADIUS_M,
    HORIZON_KERNEL_VERSION,
    HorizonProfile,
    HorizonQuality,
    HorizonRequest,
)
from terralab3d.domain.identifiers import ResourceId
from terralab3d.infrastructure.adapters.dem.adapter import DemSamplingCancelled

log = logging.getLogger("terralab3d.horizon.coordinator")

HORIZON_RESOURCE_ID = ResourceId("earth.horizon.profile")
ProfilePublisher = Callable[[dict[str, object], bytes], Awaitable[int | None]]
ProgressPublisher = Callable[[dict[str, object]], Awaitable[None]]


class HorizonCoordinator:
    """The sole owner of bake scheduling, active profile, cache and versions."""

    def __init__(
        self,
        elevation_port: ElevationPort,
        projector: RadialCoordinateProjector,
        profile_publisher: ProfilePublisher,
        progress_publisher: ProgressPublisher,
        *,
        cache_bytes: int = 32 * 1024 * 1024,
    ) -> None:
        self._elevation_port = elevation_port
        self._projector = projector
        self._profile_publisher = profile_publisher
        self._progress_publisher = progress_publisher
        self._terrain_mesh_builder = TerrainMeshBuilder(elevation_port, projector)
        self._cache_limit = max(1_048_576, int(cache_bytes))
        self._cache: OrderedDict[str, HorizonProfile] = OrderedDict()
        self._cache_bytes = 0
        self._terrain_cache: OrderedDict[str, TerrainMeshBuffers] = OrderedDict()
        self._terrain_cache_bytes = 0
        self._pending: HorizonRequest | None = None
        self._task: asyncio.Task[None] | None = None
        self._cancel_event: threading.Event | None = None
        self._cancel_started_at: float | None = None
        self._closed = False
        self._version = 0
        self._latest_generation = 0
        self._active_profile: HorizonProfile | None = None
        self._active_terrain: TerrainMeshBuffers | None = None
        self._active_terrain_profile: HorizonProfile | None = None
        self._bake_ms: deque[float] = deque(maxlen=128)
        self._terrain_build_ms: deque[float] = deque(maxlen=128)
        self._cancellation_ms: deque[float] = deque(maxlen=128)
        self._samples_per_second: deque[float] = deque(maxlen=128)
        self.request_count = 0
        self.stale_count = 0
        self.cancel_count = 0
        self.profile_binary_bytes = 0
        self.terrain_binary_bytes = 0
        self.peak_rss_bytes = 0
        self.ray_count = 0
        self.dem_samples = 0
        self.batch_size = 0

    @property
    def active_profile(self) -> HorizonProfile | None:
        return self._active_profile

    @property
    def has_active_terrain(self) -> bool:
        """Whether a resident DEM mesh has completed publication."""

        return self._active_terrain is not None

    @property
    def is_busy(self) -> bool:
        """Whether the latest-wins worker is still preparing a profile or mesh."""

        return self._task is not None and not self._task.done()

    def request(self, request: HorizonRequest) -> None:
        if self._closed:
            raise RuntimeError("HorizonCoordinator is closed")
        checked = request.settings.validated()
        request = HorizonRequest(
            request.request_id, request.generation, request.observer_generation,
            request.settings_generation, request.latitude_deg, request.longitude_deg,
            request.terrain_elevation_m, request.height_offset_m, checked,
            request.force_recalculate, request.build_terrain_mesh,
        )
        self.request_count += 1
        self._latest_generation = request.generation
        self._pending = request
        if self._cancel_event is not None:
            self._cancel_started_at = time.perf_counter()
            self._cancel_event.set()
        if self._task is None:
            self._task = asyncio.create_task(self._drain(), name="horizon-latest-wins")

    async def activate_observer_fallback(self, request: HorizonRequest) -> HorizonProfile:
        """Invalidate another location immediately; never display its old profile."""

        profile = self._flat_profile(request)
        self._active_profile = profile
        self._active_terrain = None
        self._active_terrain_profile = None
        await self._publish(profile)
        await self._publish_terrain(profile, None)
        await self._status(request, "fallback", 1.0, profile)
        log.info(
            "MGP: [horizon_coordinator.py] [activate_observer_fallback] "
            "[Perfil pla observer_generation=%d rays=%d]",
            request.observer_generation,
            profile.sample_count,
        )
        return profile

    def cancel(self) -> None:
        self._pending = None
        if self._cancel_event is not None:
            self._cancel_started_at = time.perf_counter()
            self._cancel_event.set()

    async def wait_idle(self) -> None:
        if self._task is not None:
            await asyncio.shield(self._task)

    async def publish_active(self) -> None:
        if self._active_profile is not None:
            profile = self._active_profile
            await self._publish(profile)
            await self._publish_terrain(
                self._active_terrain_profile or profile,
                self._active_terrain,
            )
            await self._progress_publisher({
                "type": "horizon_status",
                "requestId": "active-profile-reconnect",
                "generation": self._latest_generation,
                "observerGeneration": profile.observer_generation,
                "settingsGeneration": 0,
                "phase": (
                    "fallback"
                    if profile.quality is HorizonQuality.FLAT_FALLBACK
                    else "completed"
                ),
                "progress": 1.0,
                "message": None,
                "quality": profile.quality.value,
                "resolvedFraction": profile.resolved_fraction,
                "visibleRadiusM": profile.visible_radius_m,
                "angularStepDeg": profile.angular_step_deg,
                "sourceIds": list(profile.source_ids),
            })

    async def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        self.cancel()
        if self._task is not None:
            await self._task
        self._terrain_cache.clear()
        self._terrain_cache_bytes = 0
        self._active_terrain = None
        self._active_terrain_profile = None

    def metrics(self) -> dict[str, float | int]:
        dem_metrics = getattr(self._elevation_port, "metrics", lambda: {})()
        return {
            "horizonBakeP50Ms": _percentile(sorted(self._bake_ms), 0.50),
            "horizonBakeP95Ms": _percentile(sorted(self._bake_ms), 0.95),
            "terrainMeshBuildP50Ms": _percentile(sorted(self._terrain_build_ms), 0.50),
            "terrainMeshBuildP95Ms": _percentile(sorted(self._terrain_build_ms), 0.95),
            "samplesPerSecondP50": _percentile(sorted(self._samples_per_second), 0.50),
            "cancellationLatencyP95Ms": _percentile(sorted(self._cancellation_ms), 0.95),
            "profileBinaryBytes": self.profile_binary_bytes,
            "terrainBinaryBytes": self.terrain_binary_bytes,
            "peakRSSBytes": self.peak_rss_bytes,
            "rayCount": self.ray_count,
            "demSamples": self.dem_samples,
            "batchSize": self.batch_size,
            "horizonRequests": self.request_count,
            "horizonStale": self.stale_count,
            "horizonCancelled": self.cancel_count,
            **dem_metrics,
        }

    async def _drain(self) -> None:
        try:
            while self._pending is not None and not self._closed:
                request = self._pending
                self._pending = None
                self._cancel_event = threading.Event()
                await self._status(request, "queued", 0.0)
                try:
                    await self._status(request, "opening_source", 0.02)
                    cache_key = self._cache_key(request)
                    profile = None if request.force_recalculate else self._cache_get(cache_key)
                    if profile is None:
                        await self._status(request, "sampling", 0.05)
                        log.info(
                            "MGP: [horizon_coordinator.py] [_drain] "
                            "[Bake iniciat request=%s observer_generation=%d step_deg=%.6f radius_km=%.1f force=%s]",
                            request.request_id,
                            request.observer_generation,
                            request.settings.angular_step_deg,
                            request.settings.visible_radius_km,
                            request.force_recalculate,
                        )
                        started = time.perf_counter()
                        loop = asyncio.get_running_loop()
                        progress_tasks: set[asyncio.Task[None]] = set()
                        last_sampling_progress = 0.05

                        def report_sampling_progress(completed: int, total: int) -> None:
                            """Bridge bounded worker progress onto the event loop.

                            Raster sampling happens in ``asyncio.to_thread``.  Publishing
                            directly from that thread would violate the websocket/event-loop
                            boundary, which used to leave the UI visibly stuck at 5 %.
                            """

                            bounded_total = max(1, int(total))
                            fraction = min(1.0, max(0.0, int(completed) / bounded_total))
                            progress = 0.05 + 0.80 * fraction

                            def publish_progress() -> None:
                                nonlocal last_sampling_progress
                                if (
                                    self._closed
                                    or request.generation != self._latest_generation
                                    or (
                                        progress < last_sampling_progress + 0.01
                                        and completed < bounded_total
                                    )
                                ):
                                    return
                                last_sampling_progress = progress
                                task = asyncio.create_task(
                                    self._status(
                                        request,
                                        "sampling",
                                        progress,
                                        message=f"Rays {completed}/{bounded_total}",
                                    ),
                                    name="horizon-sampling-progress",
                                )
                                progress_tasks.add(task)

                                def consume(done: asyncio.Task[None]) -> None:
                                    progress_tasks.discard(done)
                                    if done.cancelled():
                                        return
                                    error = done.exception()
                                    if error is not None:
                                        log.warning(
                                            "MGP: [horizon_coordinator.py] "
                                            "[sampling progress publish failed: %s]",
                                            error,
                                        )

                                task.add_done_callback(consume)

                            loop.call_soon_threadsafe(publish_progress)

                        profile = await asyncio.to_thread(
                            self._bake,
                            request,
                            self._cancel_event,
                            cache_key,
                            report_sampling_progress,
                        )
                        # Let the final thread-safe callback enqueue before moving to
                        # reduction/publishing; the final status remains monotonic.
                        await asyncio.sleep(0)
                        if progress_tasks:
                            await asyncio.gather(*tuple(progress_tasks), return_exceptions=True)
                        elapsed_ms = (time.perf_counter() - started) * 1000.0
                        self._bake_ms.append(elapsed_ms)
                        metadata = self._elevation_port.metadata()
                        radius_m = resolve_visible_radius_m(
                            request.settings,
                            request.observer_eye_elevation_m or 0.0,
                        )
                        ray_samples = profile.sample_count * adaptive_distances_m(
                            radius_m,
                            metadata.resolution_m,
                            request.settings.max_samples_per_ray,
                        ).size
                        if elapsed_ms > 0:
                            self._samples_per_second.append(ray_samples / (elapsed_ms / 1000.0))
                        self._cache_put(cache_key, profile)
                        log.info(
                            "MGP: [horizon_coordinator.py] [_drain] "
                            "[Bake acabat request=%s duration_ms=%.2f rays=%d dem_samples=%d quality=%s]",
                            request.request_id,
                            elapsed_ms,
                            profile.sample_count,
                            self.dem_samples,
                            profile.quality.value,
                        )
                    else:
                        # Every publication is monotonic even when its immutable
                        # numerical payload came from the bounded cache.
                        self._version += 1
                        profile = replace(
                            profile,
                            version=self._version,
                            observer_generation=request.observer_generation,
                        )
                    if request.generation != self._latest_generation or self._closed:
                        self.stale_count += 1
                        continue
                    terrain: TerrainMeshBuffers | None = None
                    if (
                        request.build_terrain_mesh
                        and profile.quality in {HorizonQuality.REAL, HorizonQuality.PARTIAL_DEM}
                    ):
                        terrain = (
                            None
                            if request.force_recalculate
                            else self._terrain_cache_get(profile.content_key)
                        )
                        if terrain is None:
                            await self._status(
                                request,
                                "reducing",
                                0.86,
                                profile,
                                message="Building visible DEM relief",
                            )
                            loop = asyncio.get_running_loop()
                            mesh_tasks: set[asyncio.Task[None]] = set()
                            last_mesh_progress = 0.86

                            def report_mesh_progress(completed: int, total: int) -> None:
                                progress = 0.86 + 0.08 * min(
                                    1.0,
                                    max(0.0, int(completed) / max(1, int(total))),
                                )

                                def publish_progress() -> None:
                                    nonlocal last_mesh_progress
                                    if (
                                        self._closed
                                        or request.generation != self._latest_generation
                                        or (
                                            progress < last_mesh_progress + 0.005
                                            and completed < total
                                        )
                                    ):
                                        return
                                    last_mesh_progress = progress
                                    task = asyncio.create_task(
                                        self._status(
                                            request,
                                            "reducing",
                                            progress,
                                            profile,
                                            message=f"Building visible DEM relief {completed}/{total}",
                                        ),
                                        name="terrain-mesh-progress",
                                    )
                                    mesh_tasks.add(task)

                                    def consume(done: asyncio.Task[None]) -> None:
                                        mesh_tasks.discard(done)
                                        if done.cancelled():
                                            return
                                        error = done.exception()
                                        if error is not None:
                                            log.warning(
                                                "MGP: [horizon_coordinator.py] "
                                                "[mesh progress publish failed: %s]",
                                                error,
                                            )

                                    task.add_done_callback(consume)

                                loop.call_soon_threadsafe(publish_progress)

                            mesh_started_at = time.perf_counter()
                            terrain = await asyncio.to_thread(
                                self._terrain_mesh_builder.build,
                                request,
                                profile,
                                self._cancel_event,
                                report_mesh_progress,
                            )
                            self._terrain_build_ms.append(
                                (time.perf_counter() - mesh_started_at) * 1000.0,
                            )
                            await asyncio.sleep(0)
                            if mesh_tasks:
                                await asyncio.gather(*tuple(mesh_tasks), return_exceptions=True)
                            self._terrain_cache_put(profile.content_key, terrain)
                    await self._status(request, "reducing", 0.94, profile)
                    self._active_profile = profile
                    await self._status(request, "publishing", 0.97, profile)
                    await self._publish(profile)
                    if request.build_terrain_mesh:
                        self._active_terrain = terrain
                        self._active_terrain_profile = profile if terrain is not None else None
                        await self._publish_terrain(profile, terrain)
                    await self._status(
                        request,
                        "fallback" if profile.quality is HorizonQuality.FLAT_FALLBACK else "completed",
                        1.0,
                        profile,
                    )
                except (DemSamplingCancelled, InterruptedError):
                    self.cancel_count += 1
                    if self._cancel_started_at is not None:
                        self._cancellation_ms.append((time.perf_counter() - self._cancel_started_at) * 1000.0)
                    log.info(
                        "MGP: [horizon_coordinator.py] [_drain] [Bake cancel·lat request=%s]",
                        request.request_id,
                    )
                    await self._status(request, "cancelled", None)
                except Exception as exc:
                    log.exception(
                        "MGP: [horizon_coordinator.py] [_drain] [Bake fallit request=%s]",
                        request.request_id,
                    )
                    if request.generation == self._latest_generation:
                        fallback = self._flat_profile(request, quality=HorizonQuality.ERROR)
                        self._active_profile = fallback
                        self._active_terrain = None
                        self._active_terrain_profile = None
                        await self._publish(fallback)
                        await self._publish_terrain(fallback, None)
                    await self._status(request, "error", None, message=str(exc))
        finally:
            self._task = None
            self._cancel_event = None

    def _bake(
        self,
        request: HorizonRequest,
        cancel_event: threading.Event,
        cache_key: str,
        progress_callback: Callable[[int, int], None] | None = None,
    ) -> HorizonProfile:
        if request.observer_eye_elevation_m is None:
            return self._flat_profile(request)
        metadata = self._elevation_port.metadata()
        if not metadata.source_ids and metadata.format == "unavailable":
            return self._flat_profile(request)
        settings = request.settings
        radius_m = resolve_visible_radius_m(settings, request.observer_eye_elevation_m)
        distances = adaptive_distances_m(
            radius_m,
            metadata.resolution_m,
            max(1, settings.max_samples_per_ray - 2),
        )
        sample_count = int(math.ceil(360.0 / settings.angular_step_deg))
        azimuths = np.arange(sample_count, dtype=np.float64) * settings.angular_step_deg
        horizon = np.zeros(sample_count, dtype=np.float32)
        occluder_distance = np.zeros(sample_count, dtype=np.float32)
        occluder_height = np.zeros(sample_count, dtype=np.float32)
        resolved = np.zeros(sample_count, dtype=np.bool_)
        source_ids: set[str] = set()
        bytes_per_sample = 48
        fixed_bytes = sample_count * 13 + distances.nbytes
        per_ray_bytes = distances.size * bytes_per_sample
        if fixed_bytes + per_ray_bytes > settings.memory_budget_bytes:
            raise MemoryError(
                "Horizon memory budget is too small for the requested angular step and samples"
            )
        available_chunk_bytes = settings.memory_budget_bytes - fixed_bytes
        # Wide azimuth batches reuse raster windows; cancellation is still
        # checked inside every source/window read, not only between chunks.
        chunk_size = max(1, min(64, available_chunk_bytes // max(1, per_ray_bytes)))
        self.ray_count = sample_count
        self.dem_samples = sample_count * (distances.size + 2)
        self.batch_size = chunk_size * distances.size
        effective_radius = EARTH_RADIUS_M * (
            settings.effective_earth_radius_factor if settings.atmospheric_refraction_enabled else 1.0
        )
        for start in range(0, sample_count, chunk_size):
            if cancel_event.is_set():
                raise DemSamplingCancelled()
            end = min(sample_count, start + chunk_size)
            chunk_azimuths = np.broadcast_to(azimuths[start:end, None], (end - start, distances.size))
            chunk_distances = np.broadcast_to(distances[None, :], chunk_azimuths.shape)
            latitude, longitude = self._projector.project(
                request.latitude_deg, request.longitude_deg, chunk_azimuths, chunk_distances,
            )
            batch = self._elevation_port.sample_points(ElevationBatchRequest(
                latitude_deg=np.asarray(latitude, dtype=np.float64),
                longitude_deg=np.asarray(longitude, dtype=np.float64),
                cancellation_check=cancel_event.is_set,
            ))
            coverage_valid = mask_after_consecutive_misses(batch.valid_mask, threshold=8)
            reduction = reduce_horizon_samples(
                distances,
                batch.values_m,
                coverage_valid,
                request.observer_eye_elevation_m,
                effective_earth_radius_m=effective_radius,
            )
            # One bounded refinement on both sides of the winning sample.
            winner_indices = np.searchsorted(
                distances,
                reduction.occluder_distance_m.astype(np.float64),
            ).clip(0, distances.size - 1)
            left_indices = np.maximum(0, winner_indices - 1)
            right_indices = np.minimum(distances.size - 1, winner_indices + 1)
            refinement_distances = np.column_stack((
                (distances[winner_indices] + distances[left_indices]) * 0.5,
                (distances[winner_indices] + distances[right_indices]) * 0.5,
            ))
            refinement_distances = np.clip(refinement_distances, distances[0], radius_m)
            refinement_azimuths = np.broadcast_to(
                azimuths[start:end, None], refinement_distances.shape,
            )
            refine_latitude, refine_longitude = self._projector.project(
                request.latitude_deg,
                request.longitude_deg,
                refinement_azimuths,
                refinement_distances,
            )
            refined_batch = self._elevation_port.sample_points(ElevationBatchRequest(
                latitude_deg=np.asarray(refine_latitude, dtype=np.float64),
                longitude_deg=np.asarray(refine_longitude, dtype=np.float64),
                cancellation_check=cancel_event.is_set,
            ))
            refined_valid = refined_batch.valid_mask & reduction.valid_mask[:, None]
            candidate_distances = np.column_stack((
                reduction.occluder_distance_m.astype(np.float64),
                refinement_distances,
            ))
            candidate_heights = np.column_stack((
                reduction.occluder_height_m,
                refined_batch.values_m,
            ))
            candidate_valid = np.column_stack((
                reduction.valid_mask,
                refined_valid,
            ))
            reduction = reduce_horizon_samples(
                candidate_distances,
                candidate_heights,
                candidate_valid,
                request.observer_eye_elevation_m,
                effective_earth_radius_m=effective_radius,
            )
            horizon[start:end] = reduction.horizon_elevation_deg
            occluder_distance[start:end] = reduction.occluder_distance_m
            occluder_height[start:end] = reduction.occluder_height_m
            resolved[start:end] = reduction.valid_mask
            for index in np.unique(batch.source_indices[batch.valid_mask]):
                if int(index) >= 0 and int(index) < len(metadata.source_ids):
                    source_ids.add(metadata.source_ids[int(index)])
            for index in np.unique(refined_batch.source_indices[refined_batch.valid_mask]):
                if int(index) >= 0 and int(index) < len(metadata.source_ids):
                    source_ids.add(metadata.source_ids[int(index)])
            if progress_callback is not None:
                progress_callback(end, sample_count)
        fraction = float(np.count_nonzero(resolved) / sample_count)
        if fraction <= 0.0:
            return self._flat_profile(request)
        quality = HorizonQuality.REAL if fraction == 1.0 else HorizonQuality.PARTIAL_DEM
        return self._new_profile(
            request=request,
            content_key=cache_key,
            source_ids=tuple(sorted(source_ids)) or metadata.source_ids,
            source_fingerprint=metadata.fingerprint,
            visible_radius_m=radius_m,
            horizon_elevation_deg=horizon,
            occluder_distance_m=occluder_distance,
            occluder_height_m=occluder_height,
            valid_mask=resolved.astype(np.uint8),
            quality=quality,
            resolved_fraction=fraction,
        )

    def _flat_profile(
        self, request: HorizonRequest, *, quality: HorizonQuality = HorizonQuality.FLAT_FALLBACK,
    ) -> HorizonProfile:
        count = int(math.ceil(360.0 / request.settings.angular_step_deg))
        zeros = np.zeros(count, dtype=np.float32)
        return self._new_profile(
            request=request,
            content_key=self._cache_key(request, fallback=True),
            source_ids=(),
            source_fingerprint="unavailable",
            visible_radius_m=request.settings.visible_radius_km * 1000.0,
            horizon_elevation_deg=zeros,
            occluder_distance_m=zeros.copy(),
            occluder_height_m=zeros.copy(),
            valid_mask=np.ones(count, dtype=np.uint8),
            quality=quality,
            resolved_fraction=0.0,
        )

    def _new_profile(self, **values: object) -> HorizonProfile:
        self._version += 1
        request = values.pop("request")
        assert isinstance(request, HorizonRequest)
        return HorizonProfile(
            resource_id=HORIZON_RESOURCE_ID,
            version=self._version,
            observer_generation=request.observer_generation,
            latitude_deg=request.latitude_deg,
            longitude_deg=request.longitude_deg,
            terrain_elevation_m=request.terrain_elevation_m,
            eye_elevation_m=request.observer_eye_elevation_m,
            azimuth_start_deg=0.0,
            angular_step_deg=request.settings.angular_step_deg,
            **values,
        )

    async def _publish(self, profile: HorizonProfile) -> None:
        metadata, payload = pack_horizon_profile(profile)
        self.profile_binary_bytes = len(payload)
        self.peak_rss_bytes = max(self.peak_rss_bytes, _current_rss_bytes())
        await self._profile_publisher(metadata, payload)
        log.info(
            "MGP: [horizon_coordinator.py] [_publish] [Perfil swap version=%d quality=%s bytes=%d]",
            profile.version, profile.quality.value, len(payload),
        )

    async def _publish_terrain(
        self,
        profile: HorizonProfile,
        terrain: TerrainMeshBuffers | None,
    ) -> None:
        metadata, payload = pack_terrain_mesh(profile, terrain)
        self.terrain_binary_bytes = len(payload)
        self.peak_rss_bytes = max(self.peak_rss_bytes, _current_rss_bytes())
        await self._profile_publisher(metadata, payload)
        log.info(
            "MGP: [horizon_coordinator.py] [_publish_terrain] "
            "[Terrain swap version=%d vertices=%d bytes=%d]",
            profile.version,
            0 if terrain is None else terrain.vertex_count,
            len(payload),
        )

    async def _status(
        self,
        request: HorizonRequest,
        phase: str,
        progress: float | None,
        profile: HorizonProfile | None = None,
        *,
        message: str | None = None,
    ) -> None:
        payload: dict[str, object] = {
            "type": "horizon_status",
            "requestId": request.request_id,
            "generation": request.generation,
            "observerGeneration": request.observer_generation,
            "settingsGeneration": request.settings_generation,
            "phase": phase,
            "progress": progress,
            "message": message,
        }
        if profile is not None:
            payload.update({
                "quality": profile.quality.value,
                "resolvedFraction": profile.resolved_fraction,
                "visibleRadiusM": profile.visible_radius_m,
                "angularStepDeg": profile.angular_step_deg,
                "sourceIds": list(profile.source_ids),
            })
        await self._progress_publisher(payload)

    def _cache_key(self, request: HorizonRequest, *, fallback: bool = False) -> str:
        source = self._elevation_port.metadata()
        values = {
            "lat": round(request.latitude_deg, 8),
            "lon": round(request.longitude_deg, 8),
            "elevation": request.terrain_elevation_m,
            "heightOffset": request.height_offset_m,
            "demFingerprint": source.fingerprint,
            "settings": asdict(request.settings),
            "kernelVersion": HORIZON_KERNEL_VERSION,
            "fallback": fallback,
        }
        encoded = json.dumps(values, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
        return hashlib.blake2b(encoded, digest_size=24).hexdigest()

    def _cache_get(self, key: str) -> HorizonProfile | None:
        profile = self._cache.pop(key, None)
        if profile is not None:
            self._cache[key] = profile
        return profile

    def _cache_put(self, key: str, profile: HorizonProfile) -> None:
        if key in self._cache:
            old = self._cache.pop(key)
            self._cache_bytes -= old.binary_byte_length
        self._cache[key] = profile
        self._cache_bytes += profile.binary_byte_length
        while self._cache_bytes > self._cache_limit and self._cache:
            _, old = self._cache.popitem(last=False)
            self._cache_bytes -= old.binary_byte_length

    def _terrain_cache_get(self, key: str) -> TerrainMeshBuffers | None:
        terrain = self._terrain_cache.pop(key, None)
        if terrain is not None:
            self._terrain_cache[key] = terrain
        return terrain

    def _terrain_cache_put(self, key: str, terrain: TerrainMeshBuffers) -> None:
        if key in self._terrain_cache:
            old = self._terrain_cache.pop(key)
            self._terrain_cache_bytes -= old.byte_length
        self._terrain_cache[key] = terrain
        self._terrain_cache_bytes += terrain.byte_length
        while self._terrain_cache_bytes > self._cache_limit and self._terrain_cache:
            _, old = self._terrain_cache.popitem(last=False)
            self._terrain_cache_bytes -= old.byte_length


def pack_horizon_profile(profile: HorizonProfile) -> tuple[dict[str, object], bytes]:
    horizon = np.ascontiguousarray(profile.horizon_elevation_deg, dtype="<f4")
    distance = np.ascontiguousarray(profile.occluder_distance_m, dtype="<f4")
    height = np.ascontiguousarray(profile.occluder_height_m, dtype="<f4")
    valid = np.ascontiguousarray(profile.valid_mask, dtype=np.uint8)
    offsets = {
        "horizonElevationDeg": {"offset": 0, "length": horizon.nbytes, "dtype": "float32"},
        "occluderDistanceM": {"offset": horizon.nbytes, "length": distance.nbytes, "dtype": "float32"},
        "occluderHeightM": {"offset": horizon.nbytes + distance.nbytes, "length": height.nbytes, "dtype": "float32"},
        "validMask": {"offset": horizon.nbytes + distance.nbytes + height.nbytes, "length": valid.nbytes, "dtype": "uint8"},
    }
    payload = b"".join((horizon.tobytes(), distance.tobytes(), height.tobytes(), valid.tobytes()))
    metadata: dict[str, object] = {
        "role": "horizon_profile",
        "resourceId": str(profile.resource_id),
        "version": profile.version,
        "contentKey": profile.content_key,
        "sourceIds": list(profile.source_ids),
        "sourceFingerprint": profile.source_fingerprint,
        "observerGeneration": profile.observer_generation,
        "latitudeDeg": profile.latitude_deg,
        "longitudeDeg": profile.longitude_deg,
        "terrainElevationM": profile.terrain_elevation_m,
        "eyeElevationM": profile.eye_elevation_m,
        "visibleRadiusM": profile.visible_radius_m,
        "azimuthStartDeg": profile.azimuth_start_deg,
        "angularStepDeg": profile.angular_step_deg,
        "sampleCount": profile.sample_count,
        "quality": profile.quality.value,
        "resolvedFraction": profile.resolved_fraction,
        "kernelVersion": profile.kernel_version,
        "bufferLayout": offsets,
        "byteLength": len(payload),
    }
    return metadata, payload


def pack_terrain_mesh(
    profile: HorizonProfile,
    terrain: TerrainMeshBuffers | None,
    *,
    role: str = "terrain_mesh",
    resource_id: str = TERRAIN_MESH_RESOURCE_ID,
) -> tuple[dict[str, object], bytes]:
    """Serialize typed terrain attributes without JSON-sized numerical payloads."""

    metadata: dict[str, object] = {
        "role": role,
        "resourceId": resource_id,
        "version": profile.version,
        "contentKey": profile.content_key,
        "observerGeneration": profile.observer_generation,
        "visibleRadiusM": profile.visible_radius_m,
        "terrainElevationM": profile.terrain_elevation_m,
        "quality": profile.quality.value,
        "meshVersion": TERRAIN_MESH_VERSION,
        "axisConvention": "X=east,Y=up,Z=-north",
    }
    if terrain is None:
        metadata.update({"cleared": True, "byteLength": 0})
        return metadata, b""

    position = np.ascontiguousarray(terrain.positions, dtype="<f4")
    normal = np.ascontiguousarray(terrain.normals, dtype="<f4")
    color = np.ascontiguousarray(terrain.colors_linear, dtype=np.uint8)
    class_ids = np.ascontiguousarray(terrain.class_ids, dtype="<u2")
    source_ids = np.ascontiguousarray(terrain.source_ids, dtype="<i2")
    index = np.ascontiguousarray(terrain.indices, dtype="<u4")
    position_offset = 0
    normal_offset = position_offset + position.nbytes
    color_offset = normal_offset + normal.nbytes
    class_offset = color_offset + color.nbytes
    source_offset = class_offset + class_ids.nbytes
    index_offset = source_offset + source_ids.nbytes
    payload = b"".join((
        position.tobytes(), normal.tobytes(), color.tobytes(), class_ids.tobytes(),
        source_ids.tobytes(), index.tobytes(),
    ))
    metadata.update({
        "cleared": False,
        "vertexCount": terrain.vertex_count,
        "indexCount": int(index.size),
        "nearVertexCount": terrain.near_vertex_count,
        "polarVertexCount": terrain.polar_vertex_count,
        # Navigation reads the uploaded position buffer through this compact
        # topology description.  It is not a second terrain representation:
        # it avoids a CPU raycast through every rendered triangle each frame.
        "navigationSampling": {
            "nearAxisM": terrain.near_axis_m.astype(float).tolist(),
            "polarDistanceM": terrain.polar_distances_m.astype(float).tolist(),
            "polarAzimuthStepDeg": terrain.polar_azimuth_step_deg,
            "centerEastM": terrain.center_east_m,
            "centerNorthM": terrain.center_north_m,
        },
        "surfaceSource": terrain.source_label,
        "surfaceMode": "categorical" if np.any(terrain.class_ids > 0) else "terrain-fallback",
        "colorSpace": "linear-srgb",
        "bufferLayout": {
            "position": {"offset": position_offset, "length": position.nbytes, "dtype": "float32", "itemSize": 3},
            "normal": {"offset": normal_offset, "length": normal.nbytes, "dtype": "float32", "itemSize": 3},
            "color": {"offset": color_offset, "length": color.nbytes, "dtype": "uint8", "itemSize": 4, "normalized": True},
            "classId": {"offset": class_offset, "length": class_ids.nbytes, "dtype": "uint16", "itemSize": 1},
            "sourceId": {"offset": source_offset, "length": source_ids.nbytes, "dtype": "int16", "itemSize": 1},
            "index": {"offset": index_offset, "length": index.nbytes, "dtype": "uint32", "itemSize": 1},
        },
        "byteLength": len(payload),
    })
    return metadata, payload


def _percentile(samples: list[float], fraction: float) -> float:
    if not samples:
        return 0.0
    return float(samples[round((len(samples) - 1) * fraction)])


def _current_rss_bytes() -> int:
    try:
        import psutil  # type: ignore[import-not-found]

        return int(psutil.Process().memory_info().rss)
    except (ImportError, OSError):
        pass
    try:
        import ctypes

        class _MemoryCounters(ctypes.Structure):
            _fields_ = [
                ("cb", ctypes.c_ulong),
                ("page_fault_count", ctypes.c_ulong),
                ("peak_working_set_size", ctypes.c_size_t),
                ("working_set_size", ctypes.c_size_t),
                ("quota_peak_paged_pool_usage", ctypes.c_size_t),
                ("quota_paged_pool_usage", ctypes.c_size_t),
                ("quota_peak_non_paged_pool_usage", ctypes.c_size_t),
                ("quota_non_paged_pool_usage", ctypes.c_size_t),
                ("pagefile_usage", ctypes.c_size_t),
                ("peak_pagefile_usage", ctypes.c_size_t),
            ]

        counters = _MemoryCounters()
        counters.cb = ctypes.sizeof(counters)
        process = ctypes.windll.kernel32.GetCurrentProcess()
        if ctypes.windll.psapi.GetProcessMemoryInfo(
            process, ctypes.byref(counters), counters.cb,
        ):
            return int(counters.working_set_size)
    except (AttributeError, OSError):
        pass
    return 0
