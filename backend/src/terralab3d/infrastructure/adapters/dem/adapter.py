"""Rasterio DEM source chain with vector batches, nodata masks and bounded I/O."""

from __future__ import annotations

import hashlib
import logging
import math
import re
import threading
from collections import OrderedDict
from dataclasses import dataclass, replace
from functools import lru_cache
from pathlib import Path
from typing import Any, Callable

import numpy as np
import rasterio
from pyproj import Transformer
from affine import Affine
from rasterio.windows import Window

from terralab3d.domain.elevation.models import (
    ElevationBatch, ElevationBatchRequest, ElevationGrid, ElevationSample,
    ElevationRasterSource, ElevationSourceMetadata, ElevationStatus, VerticalUnit,
)
from terralab3d.domain.observer.models import GeoLocation
from terralab3d.domain.raster.models import (
    RasterDatasetSelection,
    RasterMetadataOverride,
)
from terralab3d.domain.terrain.models import TerrainTileRequest
from terralab3d.infrastructure.adapters.raster.reader import (
    RasterDatasetError,
    RasterioRasterReader,
)
from terralab3d.infrastructure.app_paths import resolve_elevation_data_dir

log = logging.getLogger("terralab3d.dem")
_NPY_TILE_NAME = re.compile(
    r"^Y_\(([-+0-9.]+)_([-+0-9.]+)\)X_\(([-+0-9.]+)_([-+0-9.]+)\)$"
)
# Older local NPY conversions use -8888 for cells without elevation even
# though the originating ASCII tile declares -9999.  They are both data
# sentinels, never metres below sea level.  Keep this list narrow and
# explicit: actual negative terrain values (including bathymetry) remain
# valid whenever a source provides them.
_NPY_NODATA_SENTINELS = (-9999.0, -8888.0)


class DemSamplingCancelled(InterruptedError):
    pass


class DemDataError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class _RasterSource:
    index: int
    source_id: str
    path: Path
    uri: str
    fingerprint: str
    native_crs: str
    resolution_m: float | None
    bounds_native: tuple[float, float, float, float]
    bounds_wgs84: tuple[float, float, float, float]
    nodata: float | None
    format: str
    transform: Any
    width: int
    height: int
    band_index: int = 1
    scale: float = 1.0
    offset: float = 0.0
    unit_to_metre: float = 1.0
    chain_order: int | None = None
    use_raster_mask: bool = True


@dataclass(frozen=True, slots=True)
class _CachedWindow:
    values: np.ndarray
    valid: np.ndarray

    @property
    def bytes(self) -> int:
        return int(self.values.nbytes + self.valid.nbytes)


@dataclass(frozen=True, slots=True)
class _NpyGridIndex:
    """Spatial index for one resolution tier of local NPY DEM tiles."""

    source_indices: np.ndarray
    origin_x: float
    origin_y: float


class RasterioElevationAdapter:
    """One configurable DEM authority; high-resolution sources win per point."""

    def __init__(
        self,
        source_path: Path | str | None = None,
        *,
        sources: tuple[ElevationRasterSource, ...] | None = None,
        include_library_fallback: bool = False,
        raster_reader: RasterioRasterReader | None = None,
        local_projected_crs: str = "EPSG:25831",
        local_resolution_m: float = 5.0,
        window_cache_bytes: int = 128 * 1024 * 1024,
        max_open_datasets: int = 12,
        virtual_window_size: int = 128,
    ) -> None:
        self._source_path = Path(source_path) if source_path is not None else resolve_elevation_data_dir()
        self._source_definitions = sources
        self._include_library_fallback = bool(include_library_fallback)
        self._raster_reader = raster_reader or RasterioRasterReader(
            max_open_datasets=max_open_datasets,
        )
        self._local_projected_crs = local_projected_crs
        self._local_resolution_m = float(local_resolution_m)
        self._window_cache_limit = max(1_048_576, int(window_cache_bytes))
        self._max_open_datasets = max(1, int(max_open_datasets))
        self._virtual_window_size = max(32, min(1024, int(virtual_window_size)))
        self._sources: tuple[_RasterSource, ...] = ()
        self._source_tiers: tuple[tuple[_RasterSource, ...], ...] = ()
        self._npy_grids: dict[float, _NpyGridIndex] = {}
        self._npy_grid_span = 10_000.0
        self._datasets: OrderedDict[int, Any] = OrderedDict()
        self._windows: OrderedDict[tuple[int, int, int], _CachedWindow] = OrderedDict()
        self._window_cache_bytes = 0
        self._transformers: dict[tuple[str, str], Transformer] = {}
        self._opened = False
        self._closed = False
        self._lock = threading.RLock()
        self.cache_hits = 0
        self.cache_misses = 0
        self.raster_bytes_read = 0
        self.sampled_points = 0

    @classmethod
    def from_configured_library(cls, **kwargs: Any) -> "RasterioElevationAdapter":
        return cls(resolve_elevation_data_dir(), **kwargs)

    def open(self) -> None:
        with self._lock:
            if self._opened:
                return
            self._closed = False
            sources: list[_RasterSource] = []
            definitions = self._source_definitions
            explicit_count = len(definitions) if definitions is not None else 0
            if definitions is None:
                definitions = tuple(self._legacy_source_definition(path) for path in self._discover_paths())
            elif self._include_library_fallback:
                explicit_paths = {
                    Path(source.selection.uri).resolve(strict=False)
                    for source in definitions
                }
                definitions = (
                    *definitions,
                    *(
                        self._legacy_source_definition(path)
                        for path in self._discover_paths()
                        if path.resolve(strict=False) not in explicit_paths
                    ),
                )
            for definition_index, definition in enumerate(definitions):
                path = Path(definition.selection.uri)
                try:
                    if path.suffix.lower() == ".npy":
                        source = self._inspect_npy_source(path, len(sources))
                        if source is not None:
                            sources.append(replace(
                                source,
                                chain_order=(
                                    definition_index if definition_index < explicit_count else None
                                ),
                            ))
                        continue
                    sources.append(replace(
                        self._inspect_raster_source(definition, len(sources)),
                        chain_order=(
                            definition_index if definition_index < explicit_count else None
                        ),
                    ))
                except (OSError, rasterio.errors.RasterioError, RasterDatasetError, ValueError) as exc:
                    log.warning(
                        "MGP: [adapter.py] [open] [Font DEM invàlida source=%s error=%s]",
                        path.name, exc,
                    )
            sources.sort(key=lambda item: (
                item.chain_order is None,
                item.chain_order if item.chain_order is not None else 0,
                item.resolution_m is None,
                item.resolution_m or float("inf"),
                item.source_id,
            ))
            self._sources = tuple(replace(source, index=index) for index, source in enumerate(sources))
            self._source_tiers = _group_sources_by_resolution(self._sources)
            self._build_npy_grids()
            self._opened = True
            log.debug(
                "MGP: [adapter.py] [open] [Fonts DEM descobertes sources=%d root=%s]",
                len(self._sources), self._source_path,
            )

    def metadata(self) -> ElevationSourceMetadata:
        self.open()
        if not self._sources:
            return ElevationSourceMetadata(
                "dem-unavailable", "unavailable", "", None, None, None, "unavailable",
            )
        fingerprint = hashlib.blake2b(
            "|".join(source.fingerprint for source in self._sources).encode("utf-8"), digest_size=20,
        ).hexdigest()
        crs_values = {source.native_crs for source in self._sources}
        return ElevationSourceMetadata(
            source_id="dem-source-chain",
            fingerprint=fingerprint,
            native_crs=next(iter(crs_values)) if len(crs_values) == 1 else "mixed",
            resolution_m=min(
                (value for source in self._sources if (value := source.resolution_m) is not None),
                default=None,
            ),
            bounds=(
                min(source.bounds_wgs84[0] for source in self._sources),
                min(source.bounds_wgs84[1] for source in self._sources),
                max(source.bounds_wgs84[2] for source in self._sources),
                max(source.bounds_wgs84[3] for source in self._sources),
            ),
            nodata=None,
            format="rasterio-source-chain",
            source_ids=tuple(source.source_id for source in self._sources),
        )

    def elevation(
        self,
        location: GeoLocation,
        cancellation_check: Callable[[], bool] | None = None,
    ) -> ElevationSample:
        try:
            batch = self.sample_points(ElevationBatchRequest(
                latitude_deg=np.asarray([location.latitude_deg], dtype=np.float64),
                longitude_deg=np.asarray([location.longitude_deg], dtype=np.float64),
                cancellation_check=cancellation_check,
            ))
        except DemSamplingCancelled:
            return ElevationSample(location, None, None, ElevationStatus.CANCELLED)
        except (OSError, rasterio.errors.RasterioError, ValueError) as exc:
            raise DemDataError(f"DEM elevation lookup failed at {location}") from exc
        if bool(batch.valid_mask[0]):
            source_index = int(batch.source_indices[0])
            return ElevationSample(
                location, float(batch.values_m[0]), self._sources[source_index].source_id,
                ElevationStatus.REAL,
            )
        status = ElevationStatus.NODATA if self._sources else ElevationStatus.UNAVAILABLE
        return ElevationSample(location, None, None, status)

    def sample_points(self, request: ElevationBatchRequest) -> ElevationBatch:
        self.open()
        if request.cancellation_check is not None and request.cancellation_check():
            raise DemSamplingCancelled()
        shape = request.latitude_deg.shape
        x_input = request.longitude_deg.ravel()
        y_input = request.latitude_deg.ravel()
        values = np.zeros(x_input.shape, dtype=np.float32)
        valid = np.zeros(x_input.shape, dtype=np.bool_)
        source_indices = np.full(x_input.shape, -1, dtype=np.int16)
        self.sampled_points += int(x_input.size)
        with self._lock:
            for tier in self._source_tiers:
                if request.cancellation_check is not None and request.cancellation_check():
                    raise DemSamplingCancelled()
                resolution_key = _resolution_priority(tier[0])
                npy_grid = self._npy_grids.get(resolution_key)
                if npy_grid is not None:
                    self._sample_npy_grid(
                        npy_grid, request, x_input, y_input, values, valid, source_indices,
                    )
                for source in tier:
                    if source.format == "NPY":
                        continue
                    if request.cancellation_check is not None and request.cancellation_check():
                        raise DemSamplingCancelled()
                    input_indices = np.flatnonzero(~valid)
                    if input_indices.size == 0:
                        break
                    if request.input_crs == "EPSG:4326":
                        west, south, east, north = source.bounds_wgs84
                        covered = (
                            (x_input[input_indices] >= west) & (x_input[input_indices] <= east)
                            & (y_input[input_indices] >= south) & (y_input[input_indices] <= north)
                        )
                        input_indices = input_indices[covered]
                        if input_indices.size == 0:
                            continue
                    native_x, native_y = self._transform_xy(
                        x_input[input_indices], y_input[input_indices], request.input_crs, source.native_crs,
                    )
                    sampled_values, sampled_valid = self._sample_source(
                        source, native_x, native_y, request.cancellation_check,
                    )
                    accepted = input_indices[sampled_valid]
                    values[accepted] = sampled_values[sampled_valid]
                    valid[accepted] = True
                    source_indices[accepted] = source.index
                if np.all(valid):
                    break
        status = ElevationStatus.REAL if np.any(valid) else (
            ElevationStatus.NODATA if self._sources else ElevationStatus.UNAVAILABLE
        )
        return ElevationBatch(
            values.reshape(shape), valid.reshape(shape), source_indices.reshape(shape), status,
        )

    def _build_npy_grids(self) -> None:
        self._npy_grids.clear()
        span = self._npy_grid_span
        for tier in self._source_tiers:
            sources = [source for source in tier if source.format == "NPY"]
            if not sources:
                continue
            origin_x = min(source.bounds_native[0] for source in sources)
            origin_y = min(source.bounds_native[1] for source in sources)
            max_x = max(source.bounds_native[2] for source in sources)
            max_y = max(source.bounds_native[3] for source in sources)
            width = int(math.ceil((max_x - origin_x) / span))
            height = int(math.ceil((max_y - origin_y) / span))
            grid = np.full((height, width), -1, dtype=np.int32)
            for source in sources:
                column = int(round((source.bounds_native[0] - origin_x) / span))
                row = int(round((source.bounds_native[1] - origin_y) / span))
                if 0 <= row < height and 0 <= column < width and grid[row, column] < 0:
                    # Sources are already sorted deterministically. Preserve
                    # the first one instead of allowing discovery order to
                    # overwrite an equally precise tile.
                    grid[row, column] = source.index
            self._npy_grids[_resolution_priority(tier[0])] = _NpyGridIndex(
                source_indices=grid,
                origin_x=origin_x,
                origin_y=origin_y,
            )

    def _sample_npy_grid(
        self,
        npy_grid: _NpyGridIndex,
        request: ElevationBatchRequest,
        x_input: np.ndarray,
        y_input: np.ndarray,
        values: np.ndarray,
        valid: np.ndarray,
        source_indices: np.ndarray,
    ) -> None:
        input_indices = np.flatnonzero(~valid)
        if input_indices.size == 0:
            return
        x, y = self._transform_xy(
            x_input[input_indices], y_input[input_indices], request.input_crs, self._local_projected_crs,
        )
        grid = npy_grid.source_indices
        columns = np.floor((x - npy_grid.origin_x) / self._npy_grid_span).astype(np.int64)
        rows = np.floor((y - npy_grid.origin_y) / self._npy_grid_span).astype(np.int64)
        inside = (
            (columns >= 0) & (columns < grid.shape[1])
            & (rows >= 0) & (rows < grid.shape[0])
        )
        candidates = np.full(x.shape, -1, dtype=np.int32)
        candidates[inside] = grid[rows[inside], columns[inside]]
        for source_index in np.unique(candidates[candidates >= 0]):
            if request.cancellation_check is not None and request.cancellation_check():
                raise DemSamplingCancelled()
            point_indices = np.flatnonzero(candidates == source_index)
            source = self._sources[int(source_index)]
            sampled_values, sampled_valid = self._sample_source(
                source, x[point_indices], y[point_indices], request.cancellation_check,
            )
            accepted = input_indices[point_indices[sampled_valid]]
            values[accepted] = sampled_values[sampled_valid]
            valid[accepted] = True
            source_indices[accepted] = int(source_index)

    def terrain_grid(self, request: TerrainTileRequest) -> ElevationGrid:
        """Return a finite observer-relative DEM grid via the same source chain.

        This is an infrastructure primitive for terrain preparation; it never
        manufactures elevations and therefore shares CRS, nodata, bilinear
        sampling and cancellation semantics with horizon construction.
        """

        radius = max(0.0, float(request.radius_m))
        spacing = max(0.25, float(request.target_resolution_m))
        width = int(math.floor((2.0 * radius) / spacing)) + 1
        height = width
        if width * height > 4_000_000:
            raise MemoryError("Requested terrain grid exceeds the 4M-sample safety budget")
        eastings = (np.arange(width, dtype=np.float64) - (width - 1) * 0.5) * spacing
        northings = (np.arange(height, dtype=np.float64) - (height - 1) * 0.5) * spacing
        east, north = np.meshgrid(eastings, northings)
        aeqd = (
            f"+proj=aeqd +lat_0={float(request.center_latitude_deg):.12f} "
            f"+lon_0={float(request.center_longitude_deg):.12f} "
            "+datum=WGS84 +units=m +no_defs"
        )
        transformer = Transformer.from_crs(aeqd, "EPSG:4326", always_xy=True)
        longitude, latitude = transformer.transform(east, north)
        batch = self.sample_points(ElevationBatchRequest(
            latitude_deg=np.asarray(latitude, dtype=np.float64),
            longitude_deg=np.asarray(longitude, dtype=np.float64),
        ))
        source = self.metadata()
        key_material = (
            f"{source.fingerprint}|{request.center_latitude_deg:.9f}|"
            f"{request.center_longitude_deg:.9f}|{radius:.3f}|{spacing:.3f}"
        ).encode("utf-8")
        return ElevationGrid(
            width=width,
            height=height,
            spacing_m=spacing,
            crs=aeqd,
            elevation_buffer_key=hashlib.blake2b(key_material, digest_size=20).hexdigest(),
            values_m=batch.values_m,
            valid_mask=batch.valid_mask,
            source_indices=batch.source_indices,
        )

    def metrics(self) -> dict[str, int]:
        return {
            "rasterBytesRead": self.raster_bytes_read,
            "cacheHits": self.cache_hits,
            "cacheMisses": self.cache_misses,
            "sampledPoints": self.sampled_points,
            "windowCacheBytes": self._window_cache_bytes,
            "openDatasets": len(self._datasets),
        }

    def close(self) -> None:
        with self._lock:
            if self._closed:
                return
            for dataset in self._datasets.values():
                _close_dataset(dataset)
            self._datasets.clear()
            self._windows.clear()
            self._window_cache_bytes = 0
            self._closed = True
            self._opened = False
            self._raster_reader.close()
            log.debug("MGP: [adapter.py] [close] [Recursos DEM alliberats]")

    def _discover_paths(self) -> list[Path]:
        if self._source_path.is_file():
            return [self._source_path]
        if not self._source_path.is_dir():
            return []
        candidates = [path for path in self._source_path.rglob("*") if path.is_file()]
        npy_stems = {path.stem for path in candidates if path.suffix.lower() == ".npy"}
        candidates = [
            path for path in candidates
            if path.suffix.lower() != ".asc" or path.stem not in npy_stems
        ]
        return sorted(candidates, key=lambda path: (
            path.suffix.lower() not in {".npy", ".asc"}, str(path).casefold(),
        ))

    def _legacy_source_definition(self, path: Path) -> ElevationRasterSource:
        override = None
        if path.suffix.lower() == ".asc":
            override = RasterMetadataOverride(
                crs=self._local_projected_crs,
                provenance="legacy-asc-library",
            )
        return ElevationRasterSource(
            source_id=f"dem:{path.stem}",
            selection=RasterDatasetSelection(str(path), band_index=1, overrides=override),
            vertical_unit=VerticalUnit.METRE,
            unit_confirmed=True,
        )

    def _inspect_raster_source(
        self,
        definition: ElevationRasterSource,
        index: int,
    ) -> _RasterSource:
        descriptor = self._raster_reader.validate_selection(definition.selection)
        if descriptor.crs is None:
            raise ValueError("Elevation raster has no CRS and no confirmed override")
        band_index = definition.selection.band_index or 1
        band = descriptor.bands[band_index - 1]
        bounds_native = descriptor.bounds
        path = Path(definition.selection.uri)
        fingerprint_payload = (
            f"{_path_fingerprint(path)}|{definition.selection.selected_uri}|{band_index}|"
            f"{descriptor.crs}|{descriptor.transform}|{band.nodata}|{band.scale}|"
            f"{band.offset}|{definition.unit_to_metre}"
        ).encode("utf-8")
        return _RasterSource(
            index=index,
            source_id=definition.source_id,
            path=path,
            uri=definition.selection.selected_uri,
            fingerprint=hashlib.blake2b(fingerprint_payload, digest_size=20).hexdigest(),
            native_crs=descriptor.crs,
            resolution_m=_descriptor_resolution_metres(descriptor),
            bounds_native=bounds_native,
            bounds_wgs84=_transform_bounds(bounds_native, descriptor.crs, "EPSG:4326"),
            nodata=float(band.nodata) if band.nodata is not None else None,
            format=descriptor.driver,
            transform=Affine(*descriptor.transform),
            width=descriptor.width,
            height=descriptor.height,
            band_index=band_index,
            scale=band.scale,
            offset=band.offset,
            unit_to_metre=definition.unit_to_metre,
            use_raster_mask=not (
                definition.selection.overrides is not None
                and definition.selection.overrides.nodata_is_set
                and set(band.mask_flags) == {"nodata"}
            ),
        )

    def _inspect_npy_source(self, path: Path, index: int) -> _RasterSource | None:
        match = _NPY_TILE_NAME.match(path.stem)
        if match is None:
            return None
        y_min, y_max, x_min, x_max = (float(value) for value in match.groups())
        resolution = self._local_resolution_m
        width = int(round((x_max - x_min) / resolution))
        height = int(round((y_max - y_min) / resolution))
        if width <= 0 or height <= 0:
            return None
        x_resolution = (x_max - x_min) / width
        y_resolution = (y_max - y_min) / height
        transform = Affine(x_resolution, 0.0, x_min, 0.0, -y_resolution, y_max)
        bounds = (x_min, y_min, x_max, y_max)
        return _RasterSource(
            index=index,
            source_id=f"dem:{path.stem}",
            path=path,
            uri=str(path),
            fingerprint=_path_fingerprint(path),
            native_crs=self._local_projected_crs,
            resolution_m=min(x_resolution, y_resolution),
            bounds_native=bounds,
            bounds_wgs84=_transform_bounds(bounds, self._local_projected_crs, "EPSG:4326"),
            nodata=-9999.0,
            format="NPY",
            transform=transform,
            width=width,
            height=height,
        )

    def _dataset(self, source: _RasterSource) -> Any:
        dataset = self._datasets.pop(source.index, None)
        if dataset is None:
            dataset = (
                np.load(source.path, mmap_mode="r", allow_pickle=False)
                if source.format == "NPY"
                else rasterio.open(source.uri)
            )
        self._datasets[source.index] = dataset
        while len(self._datasets) > self._max_open_datasets:
            _, old = self._datasets.popitem(last=False)
            _close_dataset(old)
        return dataset

    def _transform_xy(
        self, x: np.ndarray, y: np.ndarray, source_crs: str, target_crs: str,
    ) -> tuple[np.ndarray, np.ndarray]:
        if source_crs == target_crs:
            return np.asarray(x, dtype=np.float64), np.asarray(y, dtype=np.float64)
        key = (source_crs, target_crs)
        transformer = self._transformers.get(key)
        if transformer is None:
            transformer = Transformer.from_crs(source_crs, target_crs, always_xy=True)
            self._transformers[key] = transformer
        if x.size == 1:
            tx_scalar, ty_scalar = transformer.transform(float(x[0]), float(y[0]))
            return np.asarray([tx_scalar], dtype=np.float64), np.asarray([ty_scalar], dtype=np.float64)
        tx, ty = transformer.transform(x, y)
        return np.asarray(tx, dtype=np.float64), np.asarray(ty, dtype=np.float64)

    def _sample_source(
        self, source: _RasterSource, x: np.ndarray, y: np.ndarray, cancellation_check: Any,
    ) -> tuple[np.ndarray, np.ndarray]:
        values = np.zeros(x.shape, dtype=np.float32)
        transform, source_width, source_height = self._source_geometry(source)
        inverse = ~transform
        # Rasterio's affine inverse addresses pixel edges. Elevation samples
        # live at pixel centres, so subtract half a pixel before bilinear
        # interpolation. This is the same continuous DEM contract as TerraLab.
        raw_columns = inverse.a * x + inverse.b * y + inverse.c
        raw_rows = inverse.d * x + inverse.e * y + inverse.f
        pixel_columns = raw_columns - 0.5
        pixel_rows = raw_rows - 0.5
        cols_left = np.floor(pixel_columns).astype(np.int64)
        rows_top = np.floor(pixel_rows).astype(np.int64)
        frac_x = pixel_columns - cols_left
        frac_y = pixel_rows - rows_top
        exact_x = np.isclose(frac_x, 0.0, rtol=0.0, atol=1e-9)
        exact_y = np.isclose(frac_y, 0.0, rtol=0.0, atol=1e-9)
        cols_right = np.where(exact_x, cols_left, cols_left + 1)
        rows_bottom = np.where(exact_y, rows_top, rows_top + 1)
        frac_x = np.where(exact_x, 0.0, frac_x)
        frac_y = np.where(exact_y, 0.0, frac_y)
        inside = (
            np.isfinite(x) & np.isfinite(y)
            & (raw_columns >= 0.0) & (raw_columns < source_width)
            & (raw_rows >= 0.0) & (raw_rows < source_height)
        )
        if not np.any(inside):
            return values, np.zeros(x.shape, dtype=np.bool_)
        # At an external raster edge there is no neighbour beyond the data.
        # Replicate the edge sample rather than fabricating a nodata seam; all
        # interior interpolation still rejects a nodata corner as required.
        cols_left = np.clip(cols_left, 0, source_width - 1)
        cols_right = np.clip(cols_right, 0, source_width - 1)
        rows_top = np.clip(rows_top, 0, source_height - 1)
        rows_bottom = np.clip(rows_bottom, 0, source_height - 1)

        upper_left, upper_left_valid = self._sample_source_pixels(
            source, cols_left, rows_top, inside, source_width, cancellation_check,
        )
        upper_right, upper_right_valid = self._sample_source_pixels(
            source, cols_right, rows_top, inside, source_width, cancellation_check,
        )
        lower_left, lower_left_valid = self._sample_source_pixels(
            source, cols_left, rows_bottom, inside, source_width, cancellation_check,
        )
        lower_right, lower_right_valid = self._sample_source_pixels(
            source, cols_right, rows_bottom, inside, source_width, cancellation_check,
        )
        weights = (
            (1.0 - frac_x) * (1.0 - frac_y),
            frac_x * (1.0 - frac_y),
            (1.0 - frac_x) * frac_y,
            frac_x * frac_y,
        )
        corner_values = (upper_left, upper_right, lower_left, lower_right)
        corner_valid = (upper_left_valid, upper_right_valid, lower_left_valid, lower_right_valid)
        valid = inside.copy()
        interpolated = np.zeros(x.shape, dtype=np.float64)
        for weight, corner, is_valid in zip(weights, corner_values, corner_valid, strict=True):
            required = weight > 1e-12
            valid &= ~required | is_valid
            interpolated += weight * corner
        values[valid] = interpolated[valid].astype(np.float32)
        return values, valid

    def _sample_source_pixels(
        self,
        source: _RasterSource,
        columns: np.ndarray,
        rows: np.ndarray,
        inside: np.ndarray,
        source_width: int,
        cancellation_check: Any,
    ) -> tuple[np.ndarray, np.ndarray]:
        values = np.zeros(columns.shape, dtype=np.float32)
        valid = np.zeros(columns.shape, dtype=np.bool_)
        inside_indices = np.flatnonzero(inside)
        if inside_indices.size == 0:
            return values, valid
        block = self._virtual_window_size
        block_x = columns[inside_indices] // block
        block_y = rows[inside_indices] // block
        keys = block_y * ((source_width + block - 1) // block) + block_x
        for key in np.unique(keys):
            if cancellation_check is not None and cancellation_check():
                raise DemSamplingCancelled()
            group = inside_indices[keys == key]
            bx = int(columns[group[0]] // block)
            by = int(rows[group[0]] // block)
            cached = self._read_window(source, bx, by)
            local_cols = columns[group] - bx * block
            local_rows = rows[group] - by * block
            point_valid = cached.valid[local_rows, local_cols]
            values[group[point_valid]] = cached.values[local_rows[point_valid], local_cols[point_valid]]
            valid[group[point_valid]] = True
        return values, valid

    def _read_window(self, source: _RasterSource, block_x: int, block_y: int) -> _CachedWindow:
        key = (source.index, block_x, block_y)
        cached = self._windows.pop(key, None)
        if cached is not None:
            self.cache_hits += 1
            self._windows[key] = cached
            return cached
        self.cache_misses += 1
        size = self._virtual_window_size
        col_off, row_off = block_x * size, block_y * size
        dataset = self._dataset(source)
        source_height, source_width = (
            (int(dataset.shape[-2]), int(dataset.shape[-1]))
            if source.format == "NPY"
            else (source.height, source.width)
        )
        width, height = min(size, source_width - col_off), min(size, source_height - row_off)
        if source.format == "NPY":
            values = np.asarray(
                dataset[row_off : row_off + height, col_off : col_off + width],
                dtype=np.float32,
            ).copy()
            valid = np.isfinite(values)
            for sentinel in _NPY_NODATA_SENTINELS:
                valid &= values != sentinel
            values = np.where(valid, values, 0.0).astype(np.float32, copy=False)
        else:
            window = Window(col_off, row_off, width, height)
            raw = dataset.read(source.band_index, window=window, masked=False)
            valid = (
                dataset.read_masks(source.band_index, window=window) != 0
                if source.use_raster_mask
                else np.ones(raw.shape, dtype=np.bool_)
            )
            if source.nodata is not None:
                if math.isnan(source.nodata):
                    valid &= ~np.isnan(raw)
                else:
                    valid &= raw != source.nodata
            converted = (raw.astype(np.float64) * source.scale + source.offset) * source.unit_to_metre
            valid &= np.isfinite(converted)
            values = np.where(valid, converted, 0.0).astype(np.float32)
        cached = _CachedWindow(values, valid)
        self.raster_bytes_read += cached.bytes
        self._windows[key] = cached
        self._window_cache_bytes += cached.bytes
        while self._window_cache_bytes > self._window_cache_limit and self._windows:
            _, evicted = self._windows.popitem(last=False)
            self._window_cache_bytes -= evicted.bytes
        return cached

    def _source_geometry(self, source: _RasterSource) -> tuple[Any, int, int]:
        if source.format != "NPY":
            return source.transform, source.width, source.height
        dataset = self._dataset(source)
        height, width = int(dataset.shape[-2]), int(dataset.shape[-1])
        if width == source.width and height == source.height:
            return source.transform, width, height
        west, south, east, north = source.bounds_native
        return (
            Affine((east - west) / width, 0.0, west, 0.0, -(north - south) / height, north),
            width,
            height,
        )


def _path_fingerprint(path: Path) -> str:
    stat = path.stat()
    payload = f"{path.resolve()}|{stat.st_size}|{stat.st_mtime_ns}".encode("utf-8")
    return hashlib.blake2b(payload, digest_size=20).hexdigest()


def _close_dataset(dataset: Any) -> None:
    close = getattr(dataset, "close", None)
    if callable(close):
        close()
        return
    mmap = getattr(dataset, "_mmap", None)
    if mmap is not None:
        mmap.close()


def _resolution_priority(source: _RasterSource) -> float:
    value = source.resolution_m
    return float(value) if value is not None and math.isfinite(value) and value > 0.0 else float("inf")


def _group_sources_by_resolution(
    sources: tuple[_RasterSource, ...],
) -> tuple[tuple[_RasterSource, ...], ...]:
    """Keep the priority chain fast without giving one raster format priority."""

    tiers: list[list[_RasterSource]] = []
    previous_key: float | None = None
    for source in sources:
        key = _resolution_priority(source)
        if previous_key is None or key != previous_key:
            tiers.append([])
            previous_key = key
        tiers[-1].append(source)
    return tuple(tuple(tier) for tier in tiers)


def _transform_bounds(
    bounds: tuple[float, float, float, float], source_crs: str, target_crs: str,
) -> tuple[float, float, float, float]:
    values = _cached_transformer(source_crs, target_crs).transform_bounds(
        *bounds, densify_pts=21,
    )
    return tuple(float(value) for value in values)  # type: ignore[return-value]


@lru_cache(maxsize=32)
def _cached_transformer(source_crs: str, target_crs: str) -> Transformer:
    return Transformer.from_crs(source_crs, target_crs, always_xy=True)


def _resolution_metres(dataset: Any, native_crs: str) -> float | None:
    x_resolution, y_resolution = abs(float(dataset.res[0])), abs(float(dataset.res[1]))
    if getattr(dataset.crs, "is_projected", False) or dataset.crs is None:
        return min(x_resolution, y_resolution)
    try:
        center_x = (float(dataset.bounds.left) + float(dataset.bounds.right)) * 0.5
        center_y = (float(dataset.bounds.bottom) + float(dataset.bounds.top)) * 0.5
        local = Transformer.from_crs(
            native_crs,
            f"+proj=aeqd +lat_0={center_y} +lon_0={center_x} +datum=WGS84 +units=m +no_defs",
            always_xy=True,
        )
        x0, y0 = local.transform(center_x, center_y)
        x1, _ = local.transform(center_x + x_resolution, center_y)
        _, y1 = local.transform(center_x, center_y + y_resolution)
        return min(abs(x1 - x0), abs(y1 - y0))
    except (ValueError, RuntimeError):
        return None


def _descriptor_resolution_metres(descriptor: Any) -> float | None:
    x_resolution, y_resolution = descriptor.resolution
    try:
        crs = rasterio.crs.CRS.from_string(descriptor.crs)
        if crs.is_projected:
            return min(float(x_resolution), float(y_resolution))
        west, south, east, north = descriptor.bounds
        center_x = (west + east) * 0.5
        center_y = (south + north) * 0.5
        local = Transformer.from_crs(
            descriptor.crs,
            f"+proj=aeqd +lat_0={center_y} +lon_0={center_x} +datum=WGS84 +units=m +no_defs",
            always_xy=True,
        )
        x0, y0 = local.transform(center_x, center_y)
        x1, _ = local.transform(center_x + x_resolution, center_y)
        _, y1 = local.transform(center_x, center_y + y_resolution)
        return min(abs(x1 - x0), abs(y1 - y0))
    except (ValueError, RuntimeError):
        return None
