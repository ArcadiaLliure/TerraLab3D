"""Progressive application coordinator for categorical land-cover tiles."""

from __future__ import annotations

import logging
import math
import threading
from collections import OrderedDict
from dataclasses import replace
from typing import Callable

from terralab3d.application.ports.land_cover import LandCoverPort
from terralab3d.domain.surface.land_cover import LandCoverLegend, LandCoverTile, LandCoverTileRequest


log = logging.getLogger("terralab3d.land_cover_coordinator")

# The requested square is represented with at most ~8192 categorical samples
# per axis. Tiles remain independent GPU-array layers, so this is a coverage
# memory budget, not a WebGL 2D texture-size workaround.
_MAX_COVERAGE_SAMPLES = 8192
_TILE_PIXELS = 1024
_CACHE_BUDGET_BYTES = 128 * 1024 * 1024


class LandCoverCoordinator:
    """Stream nearest land-cover tiles first without touching DEM geometry."""

    def __init__(self, port: LandCoverPort) -> None:
        self._port = port
        self._lock = threading.RLock()
        self._current_generation = 0
        self._active_cancel: threading.Event | None = None
        self._worker_thread: threading.Thread | None = None
        self._last_request_key: str | None = None

        self._progress_callback: Callable[[dict], None] | None = None
        self._tile_callback: Callable[[LandCoverTile], None] | None = None
        self._legend_callback: Callable[[LandCoverLegend], None] | None = None

        self._cached_tiles: OrderedDict[str, LandCoverTile] = OrderedDict()
        self._cached_bytes = 0

    def set_callbacks(
        self,
        progress_callback: Callable[[dict], None],
        tile_callback: Callable[[LandCoverTile], None],
        legend_callback: Callable[[LandCoverLegend], None],
    ) -> None:
        self._progress_callback = progress_callback
        self._tile_callback = tile_callback
        self._legend_callback = legend_callback

    def request_coverage(
        self,
        center_x: float,
        center_y: float,
        radius_m: float,
        resolution_m: float,
        crs: str,
        mode: str,
        source_id: str | None = None,
    ) -> None:
        log.info("MGP: LandCoverCoordinator.request_coverage [INICI]")
        if mode != "categorical":
            self.cancel()
            log.info("MGP: LandCoverCoordinator.request_coverage [FI]")
            return
        if not all(math.isfinite(value) for value in (center_x, center_y, radius_m, resolution_m)):
            log.info("MGP: LandCoverCoordinator.request_coverage [FI]")
            return
        if radius_m <= 0.0 or resolution_m <= 0.0 or not str(crs).strip():
            log.info("MGP: LandCoverCoordinator.request_coverage [FI]")
            return
            
        request_key = f"{mode}:{source_id}:{crs}"

        with self._lock:
            if self._last_request_key == request_key and self._active_cancel is not None:
                # Si ja s'està processant exactament aquesta mateixa petició MVP, l'ignorem
                # per evitar inundar el sistema amb fils concurrents que provoquen deadlocks
                log.info("MGP: LandCoverCoordinator.request_coverage [FI]")
                return
            
            self._last_request_key = request_key

            if self._active_cancel is not None:
                self._active_cancel.set()
            self._current_generation += 1
            generation = self._current_generation
            cancel_event = threading.Event()
            self._active_cancel = cancel_event
            worker = threading.Thread(
                target=self._stream_coverage,
                args=(
                    generation,
                    cancel_event,
                    center_x,
                    center_y,
                    radius_m,
                    resolution_m,
                    crs,
                    source_id,
                ),
                name=f"land-cover-{generation}",
                daemon=True,
            )
            self._worker_thread = worker
            worker.start()
        log.info("MGP: LandCoverCoordinator.request_coverage [FI]")

    def cancel(self) -> None:
        """Cancel the active generation; an old worker can never revive later."""
        log.info("MGP: LandCoverCoordinator.cancel [INICI]")
        with self._lock:
            self._current_generation += 1
            if self._active_cancel is not None:
                self._active_cancel.set()
            self._active_cancel = None
            self._worker_thread = None
            self._last_request_key = None
        log.info("MGP: LandCoverCoordinator.cancel [FI]")

    def close(self) -> None:
        self.cancel()
        with self._lock:
            self._cached_tiles.clear()
            self._cached_bytes = 0
        self._port.close()

    def _stream_coverage(
        self,
        generation: int,
        cancel_event: threading.Event,
        center_x: float,
        center_y: float,
        radius_m: float,
        requested_resolution: float,
        crs: str,
        source_id: str | None,
    ) -> None:
        log.info("MGP: LandCoverCoordinator._stream_coverage [INICI]")
        if not self._is_current(generation, cancel_event):
            log.info("MGP: LandCoverCoordinator._stream_coverage [FI]")
            return

        effective_resolution = 10.0
        import math
        tile_span_m = effective_resolution * float(_TILE_PIXELS)
        
        min_x = center_x - radius_m
        max_x = center_x + radius_m
        min_y = center_y - radius_m
        max_y = center_y + radius_m
        
        grid_min_x = math.floor(min_x / tile_span_m) * tile_span_m
        grid_max_x = math.ceil(max_x / tile_span_m) * tile_span_m
        grid_min_y = math.floor(min_y / tile_span_m) * tile_span_m
        grid_max_y = math.ceil(max_y / tile_span_m) * tile_span_m
        
        cols = max(1, round((grid_max_x - grid_min_x) / tile_span_m))
        rows = max(1, round((grid_max_y - grid_min_y) / tile_span_m))
        total_tiles = cols * rows

        global_bounds = [grid_min_x, grid_min_y, grid_max_x, grid_max_y]

        active_source = source_id or "Automàtica"
        source_mode = "manual" if source_id else "automatic"

        self._notify_progress(
            generation,
            cancel_event,
            phase="Calculant reixeta categòrica...",
            completed=0,
            total=total_tiles,
            active_source=active_source,
            global_bounds=global_bounds,
            resolution=effective_resolution,
            completed_state=False,
            valid_tiles=0,
            empty_tiles=0,
            failed_tiles=0,
            valid_pixels=0,
        )

        completed = 0
        failed_tiles = 0
        empty_tiles = 0
        valid_tiles = 0
        valid_pixels = 0
        
        # Iterem des del centre cap a fora per anar descobrint primer el que tenim més a prop
        # Per simplificar iterem normalment i ordenem per distància al centre
        tiles_to_fetch = []
        for r in range(rows):
            for c in range(cols):
                t_min_x = grid_min_x + c * tile_span_m
                t_min_y = grid_min_y + r * tile_span_m
                t_max_x = t_min_x + tile_span_m
                t_max_y = t_min_y + tile_span_m
                
                t_center_x = t_min_x + tile_span_m / 2.0
                t_center_y = t_min_y + tile_span_m / 2.0
                dist_sq = (t_center_x - center_x)**2 + (t_center_y - center_y)**2
                
                tiles_to_fetch.append((dist_sq, t_min_x, t_min_y, t_max_x, t_max_y))
                
        tiles_to_fetch.sort(key=lambda item: item[0])

        legend_sent = False

        for dist_sq, t_min_x, t_min_y, t_max_x, t_max_y in tiles_to_fetch:
            if not self._is_current(generation, cancel_event):
                log.info("MGP: LandCoverCoordinator._stream_coverage [FI]")
                return
                
            cache_key = self._cache_key(
                source_mode, source_id, crs, t_min_x, t_min_y, effective_resolution
            )
            
            tile = self._cache_get(cache_key)
            if tile is None:
                request = LandCoverTileRequest(
                    min_x=t_min_x,
                    min_y=t_min_y,
                    max_x=t_max_x,
                    max_y=t_max_y,
                    resolution=effective_resolution,
                    crs=crs,
                    source_mode=source_mode,
                    source_id=source_id,
                )
                try:
                    tile = self._port.read_tile(request)
                except Exception as e:
                    import logging
                    logging.getLogger("terralab3d.land_cover_coordinator").exception("Error reading categorical land-cover tile %s: %s", cache_key, e)
                    tile = None

                if tile is not None and tile.valid_pixels > 0:
                    self._cache_put(cache_key, tile)
            
            completed += 1
            if tile is None:
                failed_tiles += 1
            elif tile.valid_pixels <= 0:
                empty_tiles += 1
            else:
                valid_tiles += 1
                valid_pixels += tile.valid_pixels
                active_source = tile.provenance.source_id
                
                if not legend_sent and self._legend_callback is not None:
                    legend = self._port.legend(
                        tile.provenance.scheme_key,
                        tile.provenance.scheme_version,
                        tile.provenance.mapping_revision,
                    )
                    if legend is not None and self._is_current(generation, cancel_event):
                        self._legend_callback(legend)
                        legend_sent = True

                from dataclasses import replace
                if self._tile_callback is not None and self._is_current(generation, cancel_event):
                    publication = replace(
                        tile,
                        resource_id=f"{tile.resource_id}.{t_min_x}_{t_min_y}.g{generation}",
                        provenance=replace(tile.provenance, generation=generation),
                    )
                    self._tile_callback(publication)
            
            if completed % max(1, total_tiles // 20) == 0 or completed == total_tiles:
                self._notify_progress(
                    generation,
                    cancel_event,
                    phase=f"Descarregant ({completed}/{total_tiles})...",
                    completed=completed,
                    total=total_tiles,
                    active_source=active_source,
                    global_bounds=global_bounds,
                    resolution=effective_resolution,
                    completed_state=False,
                    valid_tiles=valid_tiles,
                    empty_tiles=empty_tiles,
                    failed_tiles=failed_tiles,
                    valid_pixels=valid_pixels,
                )

        if not self._is_current(generation, cancel_event):
            log.info("MGP: LandCoverCoordinator._stream_coverage [FI]")
            return

        if valid_tiles > 0:
            final_phase = "Cobertura carregada"
        elif failed_tiles > 0:
            final_phase = "Error carregant cobertura"
        else:
            final_phase = "Sense dades a l\'àrea"

        self._notify_progress(
            generation,
            cancel_event,
            phase=final_phase,
            completed=completed,
            total=total_tiles,
            active_source=active_source,
            global_bounds=global_bounds,
            resolution=effective_resolution,
            completed_state=True,
            valid_tiles=valid_tiles,
            empty_tiles=empty_tiles,
            failed_tiles=failed_tiles,
            valid_pixels=valid_pixels,
        )
        log.info("MGP: LandCoverCoordinator._stream_coverage [FI]")

    def _notify_progress(
        self,
        generation: int,
        cancel_event: threading.Event,
        *,
        phase: str,
        completed: int,
        total: int,
        active_source: str,
        global_bounds: list[float],
        resolution: float,
        completed_state: bool,
        valid_tiles: int,
        empty_tiles: int,
        failed_tiles: int,
        valid_pixels: int,
        cleared: bool = False,
    ) -> None:
        callback = self._progress_callback
        if callback is None or not self._is_current(generation, cancel_event):
            return
        progress = completed / max(1, total)
        callback({
            "generation": generation,
            "phase": phase,
            "completedTiles": completed,
            "totalTiles": total,
            "progress01": progress,
            "percent": round(progress * 100.0),
            "completed": completed_state,
            "mode": "categorical",
            "activeSource": active_source,
            "globalBounds": global_bounds,
            "resolution": resolution,
            "validTiles": valid_tiles,
            "emptyTiles": empty_tiles,
            "failedTiles": failed_tiles,
            "validPixels": valid_pixels,
            "cleared": cleared,
        })

    def _is_current(self, generation: int, cancel_event: threading.Event) -> bool:
        if cancel_event.is_set():
            return False
        with self._lock:
            return generation == self._current_generation and cancel_event is self._active_cancel

    @staticmethod
    def _cache_key(
        source_mode: str,
        source_id: str | None,
        crs: str,
        min_x: float,
        min_y: float,
        resolution: float,
    ) -> str:
        return (
            f"{source_mode}|{source_id or '*'}|{crs}|"
            f"{min_x:.3f}|{min_y:.3f}|{resolution:.9f}"
        )

    def _cache_get(self, key: str) -> LandCoverTile | None:
        with self._lock:
            tile = self._cached_tiles.get(key)
            if tile is not None:
                self._cached_tiles.move_to_end(key)
            return tile

    def _cache_put(self, key: str, tile: LandCoverTile) -> None:
        size = tile.byte_size
        if size > _CACHE_BUDGET_BYTES:
            return
        with self._lock:
            previous = self._cached_tiles.pop(key, None)
            if previous is not None:
                self._cached_bytes -= previous.byte_size
            self._cached_tiles[key] = tile
            self._cached_bytes += size
            while self._cached_bytes > _CACHE_BUDGET_BYTES and self._cached_tiles:
                _, evicted = self._cached_tiles.popitem(last=False)
                self._cached_bytes -= evicted.byte_size
