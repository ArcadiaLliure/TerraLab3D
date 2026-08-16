"""Orchestrates categorical land-cover sampling, byte-caching and binary resource publication.

Follows the latest-wins cancelable pattern. When DEM terrain meshes are
published, this coordinator asynchronously samples land-cover classes for
the mesh vertices and emits a companion binary surface resource.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import sys
import threading
import time
from collections import deque
from typing import Awaitable, Callable

# pyrefly: ignore [missing-import]
import numpy as np

from terralab3d.application.ports.terrain import LandCoverPort
from terralab3d.domain.identifiers import ResourceId
from terralab3d.domain.surface.calculations import build_palette_index_map
from terralab3d.domain.surface.errors import LandCoverSamplingCancelled
from terralab3d.domain.surface.models import (
    CategoricalSurfaceResource,
    LandCoverLegend,
    LandCoverSampleGrid,
    LandCoverSamplingRequest,
    SurfaceStyle,
)
from terralab3d.domain.terrain.models import TerrainChunkIdentity
from terralab3d.infrastructure.adapters.cache.adapter import ByteLRUCache

log = logging.getLogger("terralab3d.landcover.coordinator")

SURFACE_RESOURCE_ID = ResourceId("earth.terrain.surface")
SurfacePublisher = Callable[[dict[str, object], bytes], Awaitable[int | None]]
StatusPublisher = Callable[[dict[str, object]], Awaitable[None]]
LegendPublisher = Callable[[list[dict[str, object]]], Awaitable[None]]


def _sample_grid_sizer(grid: LandCoverSampleGrid) -> int:
    return (
        grid.class_ids.nbytes
        + grid.palette_indices.nbytes
        + grid.source_slots.nbytes
        + grid.valid.nbytes
        + grid.provenance.nbytes
        + 1024  # legend & descriptor overhead
    )


class LandCoverCoordinator:
    """Manages land cover sampling jobs, cache, and binary surface resources."""

    def __init__(
        self,
        land_cover_port: LandCoverPort,
        surface_publisher: SurfacePublisher,
        status_publisher: StatusPublisher,
        legend_publisher: LegendPublisher | None = None,
        *,
        cache_bytes: int = 64 * 1024 * 1024,
    ) -> None:
        self._port = land_cover_port
        self._publisher = surface_publisher
        self._status_publisher = status_publisher
        self._legend_publisher = legend_publisher
        self._cache = ByteLRUCache[LandCoverSampleGrid](
            max_bytes=cache_bytes,
            byte_sizer=_sample_grid_sizer,
            name="landcover_cache",
        )
        self._selected_source_id: str | None = None  # None = automatic
        self._active_style = SurfaceStyle.CATEGORICAL_ORIGINAL
        self._version = 0
        self._latest_generation = 0
        self._task: asyncio.Task[None] | None = None
        self._cancel_event: threading.Event | None = None
        self._pending_requests: dict[str, LandCoverSamplingRequest] = {}
        self._closed = False
        self._sample_ms: deque[float] = deque(maxlen=128)
        self.request_count = 0
        self.published_count = 0
        self.cancel_count = 0
        self.surface_binary_bytes = 0
        self._latest_status: dict[str, any] | None = None

    @property
    def active_style(self) -> SurfaceStyle:
        return self._active_style

    @property
    def selected_source_id(self) -> str | None:
        return self._selected_source_id

    def set_selected_source(self, source_id: str | None) -> None:
        """Set the active source selection (None = automatic)."""
        if self._selected_source_id != source_id:
            self._selected_source_id = source_id
            log.debug("MGP: [landcover.coordinator] [selected source changed: %s]", source_id)

    def set_style(self, style: SurfaceStyle) -> None:
        """Toggle active surface style without clearing sampled data."""
        self._active_style = style
        log.debug("MGP: [landcover.coordinator] [style changed: %s]", style.value)

    def cancel(self) -> None:
        """Cancel ongoing surface sampling."""
        if self._cancel_event is not None:
            self._cancel_event.set()
        self._pending_requests.clear()

    async def schedule_sampling(
        self,
        chunk: TerrainChunkIdentity,
        latitude_deg: np.ndarray,
        longitude_deg: np.ndarray,
        generation: int,
    ) -> None:
        """Schedule categorical sampling for a published terrain mesh chunk."""
        if self._closed:
            return

        if self._active_style == SurfaceStyle.BASE:
            await self._status_publisher({
                "type": "surface_status",
                "generation": generation,
                "mode": self._active_style.value,
                "effectiveSource": "Cap",
                "resolvedFraction": 0.0,
                "fallbackFraction": 1.0,
                "sampleCount": 0,
                "cacheBytes": 0,
                "cacheHits": 0,
            })
            return

        self._latest_generation = generation
        self.request_count += 1

        log.debug(
            "MGP: [landcover.coordinator] [schedule_sampling key=%s vertices=%d gen=%d source=%s]",
            chunk.content_key, latitude_deg.size, generation, self._selected_source_id,
        )

        request = LandCoverSamplingRequest(
            terrain_content_key=chunk.content_key,
            terrain_version=chunk.version,
            latitude_deg=latitude_deg,
            longitude_deg=longitude_deg,
            generation=generation,
            selected_source_id=self._selected_source_id,
        )

        # Check in-memory cache first
        cache_key = self._cache_key(request)
        cached_grid = self._cache.get(cache_key)
        if cached_grid is not None:
            log.debug("MGP: [landcover.coordinator] [cache hit key=%s]", chunk.content_key)
            await self._publish_grid(request, cached_grid)
            return

        # Queue request and ensure worker runs
        self._pending_requests[chunk.content_key] = request
        if self._task is None or self._task.done():
            self._task = asyncio.create_task(self._drain(), name="landcover-sampling-drain")

    async def _drain(self) -> None:
        try:
            while self._pending_requests and not self._closed:
                # Take oldest pending request
                content_key, request = self._pending_requests.popitem()
                self._cancel_event = threading.Event()
                request_with_cancel = LandCoverSamplingRequest(
                    terrain_content_key=request.terrain_content_key,
                    terrain_version=request.terrain_version,
                    latitude_deg=request.latitude_deg,
                    longitude_deg=request.longitude_deg,
                    generation=request.generation,
                    lod_tier=request.lod_tier,
                    selected_source_id=self._selected_source_id,
                    cancellation_check=self._cancel_event.is_set,
                )

                cache_key = self._cache_key(request_with_cancel)
                grid = self._cache.get(cache_key)

                if grid is None:
                    started = time.perf_counter()
                    log.info(
                        "INTERN: Backend (land_cover_coordinator.py:%d: _drain -> [START] Inici de mostreig de cobertura del sòl per a vèrtexs=%d)",
                        sys._getframe().f_lineno, request.latitude_deg.size,
                    )
                    try:
                        grid = await asyncio.to_thread(
                            self._port.sample_classes,
                            request_with_cancel,
                        )
                        elapsed_ms = (time.perf_counter() - started) * 1000.0
                        self._sample_ms.append(elapsed_ms)
                        self._cache.put(cache_key, grid)
                        log.debug(
                            "MGP: [landcover.coordinator] [sampling completed key=%s elapsed_ms=%.1f resolved=%.1f%%]",
                            request.terrain_content_key, elapsed_ms, grid.resolved_fraction * 100.0,
                        )
                    except (LandCoverSamplingCancelled, InterruptedError):
                        self.cancel_count += 1
                        log.debug("MGP: [landcover.coordinator] [sampling cancelled key=%s]", request.terrain_content_key)
                        continue
                    except Exception as exc:
                        log.warning(
                            "MGP: [landcover.coordinator] [sampling failed key=%s error=%s]",
                            request.terrain_content_key, exc, exc_info=True
                        )
                        await self._status_publisher(self.status())
                        continue

                if self._closed or request.generation != self._latest_generation:
                    continue

                await self._publish_grid(request, grid)
        finally:
            self._task = None
            self._cancel_event = None

    async def _publish_grid(
        self,
        request: LandCoverSamplingRequest,
        grid: LandCoverSampleGrid,
    ) -> None:
        self._version += 1
        resource = CategoricalSurfaceResource(
            resource_id=SURFACE_RESOURCE_ID,
            version=self._version,
            generation=request.generation,
            terrain_content_key=request.terrain_content_key,
            compatible_terrain_version=request.terrain_version,
            sample_count=grid.sample_count,
            resolved_fraction=grid.resolved_fraction,
            fallback_fraction=grid.fallback_fraction,
            legend=grid.legend,
            source_descriptors=grid.source_descriptors,
        )
        metadata, payload = pack_surface_resource(resource, grid)
        self.surface_binary_bytes = len(payload)
        self.published_count += 1
        await self._publisher(metadata, payload)

        active_source = grid.source_descriptors[0].name if grid.source_descriptors else "None"
        log.info(
            "INTERN: Backend (land_cover_coordinator.py:%d: _publish_grid -> [END] Bake i mostreig de cobertura completats vèrtexs=%d bytes=%d font=%s)",
            sys._getframe().f_lineno, grid.sample_count, len(payload), active_source,
        )
        log.debug(
            "MGP: [landcover.coordinator] [_publish_grid key=%s v=%d vertices=%d bytes=%d resolved=%.1f%% source=%s]",
            request.terrain_content_key, self._version, grid.sample_count, len(payload), grid.resolved_fraction * 100.0, active_source,
        )
        status_payload = {
            "type": "surface_status",
            "generation": request.generation,
            "mode": self._active_style.value,
            "effectiveSource": active_source,
            "resolvedFraction": grid.resolved_fraction,
            "fallbackFraction": grid.fallback_fraction,
            "sampleCount": grid.sample_count,
            "cacheHits": self._cache.metrics()["landcover_cache_hits"],
            "cacheBytes": self._cache.current_bytes,
        }
        self._latest_status = status_payload
        await self._status_publisher(status_payload)

        # Enviar la llegenda perquè el frontend pugui poblar el tooltip i la UI
        if self._legend_publisher and grid.legend:
            legend_entries = [
                {
                    "classId": entry.class_id,
                    "name": entry.name,
                    "rgba": list(entry.rgba),
                    "isNodata": entry.is_nodata,
                }
                for entry in grid.legend.entries
                if not entry.is_nodata and not entry.is_transparent
            ]
            await self._legend_publisher(legend_entries)


    def status(self) -> dict[str, any]:
        """Return the current surface status snapshot for UI and bridge."""
        if self._latest_status is not None:
            res = dict(self._latest_status)
            res["mode"] = self._active_style.value
            return res
        cache_m = self._cache.metrics()
        descriptors = self._port.metadata()
        active_source = descriptors[0].name if descriptors else "Sense dades"
        return {
            "type": "surface_status",
            "generation": self._latest_generation,
            "mode": self._active_style.value,
            "effectiveSource": active_source,
            "resolvedFraction": 1.0 if descriptors else 0.0,
            "fallbackFraction": 0.0,
            "sampleCount": 0,
            "cacheHits": cache_m.get("landcover_cache_hits", 0),
            "cacheBytes": self._cache.current_bytes,
        }

    def _cache_key(self, request: LandCoverSamplingRequest) -> str:
        # Key includes coordinates hash, selected source, and source fingerprints
        descriptors = self._port.metadata()
        fps = [f"{d.id}:{d.fingerprint}" for d in descriptors]
        coords_hash = hashlib.blake2b(
            request.latitude_deg.tobytes() + request.longitude_deg.tobytes(),
            digest_size=12,
        ).hexdigest()
        raw = f"{coords_hash}:{request.selected_source_id}:{request.lod_tier}:{':'.join(fps)}"
        return hashlib.blake2b(raw.encode(), digest_size=20).hexdigest()

    async def close(self) -> None:
        self._closed = True
        self.cancel()
        if self._task is not None:
            await self._task
        self._cache.clear()
        self._port.close()

    def metrics(self) -> dict[str, float | int]:
        cache_m = self._cache.metrics()
        p50 = float(np.percentile(list(self._sample_ms), 50)) if self._sample_ms else 0.0
        p95 = float(np.percentile(list(self._sample_ms), 95)) if self._sample_ms else 0.0
        return {
            "surfaceSamplingP50Ms": p50,
            "surfaceSamplingP95Ms": p95,
            "surfaceRequests": self.request_count,
            "surfacePublished": self.published_count,
            "surfaceCancelled": self.cancel_count,
            "surfaceBinaryBytes": self.surface_binary_bytes,
            **cache_m,
        }


def pack_surface_resource(
    resource: CategoricalSurfaceResource,
    grid: LandCoverSampleGrid,
) -> tuple[dict[str, object], bytes]:
    """Serialize categorical surface attributes and palette for Three.js."""
    class_ids = np.ascontiguousarray(grid.class_ids, dtype="<u2")
    source_slots = np.ascontiguousarray(grid.source_slots, dtype="<i2")
    colors_rgba = np.ascontiguousarray(grid.colors_rgba, dtype=np.uint8) if grid.colors_rgba is not None else np.zeros(0, dtype=np.uint8)

    class_offset = 0
    source_offset = class_offset + class_ids.nbytes
    colors_offset = source_offset + source_slots.nbytes

    payload = b"".join((
        class_ids.tobytes(),
        source_slots.tobytes(),
        colors_rgba.tobytes(),
    ))

    # Serialize legend entries
    legend_entries: list[dict[str, object]] = []
    if grid.legend:
        for entry in grid.legend.entries:
            legend_entries.append({
                "classId": entry.class_id,
                "name": entry.name,
                "rgba": list(entry.rgba),
                "isNodata": entry.is_nodata,
            })

    source_names = [d.name for d in grid.source_descriptors]

    metadata: dict[str, object] = {
        "role": "surface_resource",
        "resourceId": str(resource.resource_id),
        "version": resource.version,
        "generation": resource.generation,
        "terrainContentKey": resource.terrain_content_key,
        "compatibleTerrainVersion": resource.compatible_terrain_version,
        "vertexCount": grid.sample_count,
        "resolvedFraction": resource.resolved_fraction,
        "fallbackFraction": resource.fallback_fraction,
        "sourceLabel": "; ".join(source_names) if source_names else "Default",
        "legend": legend_entries,
        "bufferLayout": {
            "classId": {"offset": class_offset, "length": class_ids.nbytes, "dtype": "uint16", "itemSize": 1},
            "sourceId": {"offset": source_offset, "length": source_slots.nbytes, "dtype": "int16", "itemSize": 1},
            "colorRgba": {"offset": colors_offset, "length": colors_rgba.nbytes, "dtype": "uint8", "itemSize": 4},
        },
        "byteLength": len(payload),
    }
    return metadata, payload

