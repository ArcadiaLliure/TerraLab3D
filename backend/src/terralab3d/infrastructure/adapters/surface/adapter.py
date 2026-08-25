"""Resolve and read TerraLab's configured surface sources.

Land-cover source selection is driven by ``data_sources.json``.  No concrete
GeoTIFF filename, source id or drive letter is embedded in TerraLab3D.

The categorical renderer introduced after Pas 16 must consume
``resolve_land_cover_source()`` (or the same configuration contract) instead
of inventing a second source-discovery path.
"""

from __future__ import annotations

import json
import logging
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable

import numpy as np
import rasterio
from pyproj import Transformer

from terralab3d.infrastructure.app_paths import application_state_root, resolve_data_root
from terralab3d.infrastructure.adapters.surface.tlst_catalog import (
    LandCoverSchemeRegistry,
    load_builtin_land_cover_registry,
)
from terralab3d.domain.surface.tlst import TlstValidationError

log = logging.getLogger("terralab3d.surface")

_CATEGORICAL_LAYER_TYPES = {
    "land_cover_categorical",
    "land_cover_rgb",
    "surface_categorical",
}
_LEGACY_SURFACE_LAYER_TYPES = _CATEGORICAL_LAYER_TYPES | {
    "surface_rgb",
}
@dataclass(frozen=True, slots=True)
class SurfaceVertexSamples:
    """Legacy Pas-16 presentation samples.

    Kept only so the known-good Pas-16 API remains source-compatible while
    Pas 17 moves categorical appearance out of DEM vertices.
    """

    rgba_linear: np.ndarray
    valid: np.ndarray
    class_ids: np.ndarray
    source_ids: np.ndarray
    source_label: str


@dataclass(frozen=True, slots=True)
class ResolvedLandCoverSource:
    """One fully resolved categorical source selected by TerraLab's library."""

    source_id: str
    display_name: str
    config_path: Path
    raster_paths: tuple[Path, ...]
    layer_type: str
    crs: str
    resolution_m: float
    nodata: float | int | None
    scheme_key: str
    scheme_version: str
    mapping_revision: str
    source_dtype: str
    payload_dtype: str
    coverage: tuple[float, float, float, float] | None
    priority: int


@dataclass(frozen=True, slots=True)
class _ConfiguredSource:
    identifier: str
    name: str
    raster_paths: tuple[Path, ...]
    layer_type: str
    priority: int
    resolution_m: float
    coverage: tuple[float, float, float, float] | None

    @property
    def path(self) -> Path:
        return self.raster_paths[0]


class ConfiguredSurfaceSampler:
    """Configuration authority for land-cover source resolution.

    ``resolve_land_cover_source`` is the Pas-17 source-selection entry point.
    ``sample`` remains for Pas-16 compatibility and must not be used as the
    final categorical rendering architecture.
    """

    def __init__(
        self,
        config_paths: tuple[Path, ...] | None = None,
        scheme_registry: LandCoverSchemeRegistry | None = None,
    ) -> None:
        self._config_paths = config_paths
        self._transformers: dict[str, Transformer] = {}
        self._scheme_registry = scheme_registry or load_builtin_land_cover_registry()

    @property
    def scheme_registry(self) -> LandCoverSchemeRegistry:
        return self._scheme_registry

    def resolve_land_cover_source(
        self,
        override_mode: str | None = None,
        override_source_id: str | None = None,
    ) -> ResolvedLandCoverSource | None:
        """Resolve the configured land-cover source to concrete raster files."""
        log.info("MGP: ConfiguredSurfaceSampler.resolve_land_cover_source [INICI]")

        payload, config_path = self._load_config_with_path()
        if config_path is None:
            log.warning("No s'ha trobat data_sources.json")
            log.info("MGP: ConfiguredSurfaceSampler.resolve_land_cover_source [FI]")
            return None

        raw_sources = payload.get("sources", []) if isinstance(payload, dict) else []
        if not isinstance(raw_sources, list):
            log.info("MGP: ConfiguredSurfaceSampler.resolve_land_cover_source [FI]")
            return None

        selections = payload.get("selections", {})
        if not isinstance(selections, dict):
            selections = {}
        land_cover = selections.get("land_cover", {})
        if not isinstance(land_cover, dict):
            land_cover = {}

        mode = override_mode if override_mode else str(land_cover.get("mode", "automatic")).strip().lower()
        selected_id = override_source_id if override_source_id is not None else str(land_cover.get("source_id") or "").strip()

        candidates = []
        for raw in raw_sources:
            if not isinstance(raw, dict) or not bool(raw.get("enabled", True)):
                continue
            layer_type = str(raw.get("layer_type", "")).strip().lower()
            if layer_type not in _CATEGORICAL_LAYER_TYPES:
                continue
            source_id = str(raw.get("id", "")).strip()
            if not source_id:
                continue
            
            if mode == "manual" and source_id != selected_id:
                continue
                
            candidates.append(raw)

        if mode == "manual" and selected_id and not candidates:
            log.error("Font manual %s no existeix a %s", selected_id, config_path)
            log.info("MGP: ConfiguredSurfaceSampler.resolve_land_cover_source [FI]")
            return None

        if not candidates:
            log.warning("Cap font categòrica disponible a %s", config_path)
            log.info("MGP: ConfiguredSurfaceSampler.resolve_land_cover_source [FI]")
            return None

        candidates.sort(key=lambda c: self._source_sort_key(c))
        selected_raw = candidates[0]
        source_id = str(selected_raw.get("id", "")).strip()
        display_name = str(selected_raw.get("display_name") or source_id)
        layer_type = str(selected_raw.get("layer_type", "")).strip().lower()
        coverage = self._coverage(selected_raw.get("coverage"))
        priority = self._int_or(selected_raw.get("priority"), 0)
        
        scheme_key, scheme_version, mapping_revision = self._scheme_metadata(selected_raw)
        legacy_legend_id = self._legend_id(selected_raw)
        try:
            scheme_reference = self._scheme_registry.resolve_reference(
                scheme_key=scheme_key,
                scheme_version=scheme_version,
                mapping_revision=mapping_revision,
                legacy_legend_id=legacy_legend_id,
            )
        except TlstValidationError as exc:
            log.error("Esquema categòric invàlid per a %s: %s", source_id, exc)
            log.info("MGP: ConfiguredSurfaceSampler.resolve_land_cover_source [FI]")
            return None
        
        raster_paths = self._raster_paths(selected_raw, config_path)
        if not raster_paths:
            log.error("Cap fitxer raster resolt per a %s", source_id)
            log.info("MGP: ConfiguredSurfaceSampler.resolve_land_cover_source [FI]")
            return None

        configured_resolution = self._positive_float(selected_raw.get("resolution_m"))
        selected_raster: Path | None = None
        openable_rasters: list[Path] = []
        selected_crs = ""
        selected_resolution = configured_resolution
        selected_nodata = None
        selected_source_dtype = ""
        selected_payload_dtype = ""

        for raster_path in raster_paths:
            try:
                with rasterio.open(raster_path) as dataset:
                    openable_rasters.append(raster_path)
                    if selected_raster is None:
                        selected_raster = raster_path
                        selected_crs = str(dataset.crs or "")
                        selected_nodata = dataset.nodata
                        selected_payload_dtype = dataset.dtypes[0]
                        selected_source_dtype = str(
                            selected_raw.get("source_dtype") or selected_payload_dtype
                        )
                        if not math.isfinite(selected_resolution):
                            selected_resolution = self._dataset_resolution_hint(dataset)
            except (OSError, rasterio.errors.RasterioError) as exc:
                log.warning("No es pot obrir %s: %s", raster_path, exc)

        if selected_raster is None:
            log.error("Cap raster s'ha pogut obrir per a %s", source_id)
            log.info("MGP: ConfiguredSurfaceSampler.resolve_land_cover_source [FI]")
            return None

        ordered_paths = (selected_raster,) + tuple(
            path for path in openable_rasters if path != selected_raster
        )

        log.debug(
            "LAND COVER RESOLT: source_id='%s', config='%s', raster='%s', crs='%s', resolution=%.6f, nodata=%s",
            source_id,
            config_path,
            selected_raster,
            selected_crs,
            selected_resolution,
            selected_nodata,
        )

        res = ResolvedLandCoverSource(
            source_id=source_id,
            display_name=display_name,
            config_path=config_path,
            raster_paths=ordered_paths,
            layer_type=layer_type,
            crs=selected_crs,
            resolution_m=selected_resolution,
            nodata=selected_nodata,
            scheme_key=scheme_reference.scheme_key,
            scheme_version=scheme_reference.scheme_version,
            mapping_revision=scheme_reference.mapping_revision,
            source_dtype=selected_source_dtype,
            payload_dtype=selected_payload_dtype,
            coverage=coverage,
            priority=priority,
        )
        log.info("MGP: ConfiguredSurfaceSampler.resolve_land_cover_source [FI]")
        return res


    def sample(
        self,
        latitude_deg: np.ndarray,
        longitude_deg: np.ndarray,
        *,
        cancellation_check: Callable[[], bool] | None = None,
    ) -> SurfaceVertexSamples:
        """Legacy Pas-16 vertex sampler.

        This method is intentionally retained only to avoid breaking the
        known-good Pas-16 baseline. Pas 17 must sample categorical rasters as
        independent grids/tiles, never at DEM vertices.
        """

        latitude = np.asarray(latitude_deg, dtype=np.float64).reshape(-1)
        longitude = np.asarray(longitude_deg, dtype=np.float64).reshape(-1)
        count = latitude.size
        rgba = np.zeros((count, 4), dtype=np.uint8)
        valid = np.zeros(count, dtype=bool)
        classes = np.zeros(count, dtype=np.uint16)
        source_ids = np.zeros(count, dtype=np.int16)
        labels: list[str] = []

        for ordinal, source in enumerate(self._legacy_sources(), start=1):
            if cancellation_check is not None and cancellation_check():
                raise InterruptedError("Surface sampling cancelled")
            unresolved = np.flatnonzero(~valid)
            if unresolved.size == 0:
                break
            candidate = unresolved[
                _within_coverage(
                    latitude[unresolved],
                    longitude[unresolved],
                    source.coverage,
                )
            ]
            if candidate.size == 0:
                continue
            try:
                sampled, sampled_valid, class_values = self._sample_source(
                    source,
                    latitude[candidate],
                    longitude[candidate],
                    cancellation_check,
                )
            except (OSError, rasterio.errors.RasterioError, ValueError) as exc:
                log.warning(
                    "MGP: [surface.adapter] [source unavailable id=%s error=%s]",
                    source.identifier,
                    exc,
                )
                continue
            accepted = candidate[sampled_valid]
            if accepted.size == 0:
                continue
            rgba[accepted] = sampled[sampled_valid]
            valid[accepted] = True
            classes[accepted] = class_values[sampled_valid]
            source_ids[accepted] = ordinal
            labels.append(source.name)

        label = (
            "; ".join(dict.fromkeys(labels))
            if labels
            else "TerraLab default terrain palette"
        )
        return SurfaceVertexSamples(rgba, valid, classes, source_ids, label)

    def _legacy_sources(self) -> tuple[_ConfiguredSource, ...]:
        payload, config_path = self._load_config_with_path()
        if config_path is None:
            return ()

        raw_sources = payload.get("sources", []) if isinstance(payload, dict) else []
        if not isinstance(raw_sources, list):
            return ()

        # Prefer the real land-cover selection. Retain the old "surface" key
        # only for Pas-16 fixtures/configurations that predate surface_model_v3.
        selection = self._selection(payload, "land_cover")
        if not selection:
            selection = self._selection(payload, "surface")
        mode = str(selection.get("mode", "automatic")).strip().lower()
        selected_id = str(selection.get("source_id") or "").strip()

        entries: list[_ConfiguredSource] = []
        for raw in raw_sources:
            if not isinstance(raw, dict) or not bool(raw.get("enabled", True)):
                continue
            layer_type = str(raw.get("layer_type", "")).strip().lower()
            if layer_type not in _LEGACY_SURFACE_LAYER_TYPES:
                continue
            identifier = str(raw.get("id", "")).strip()
            if mode == "manual" and identifier != selected_id:
                continue
            raster_paths = self._raster_paths(raw, config_path)
            if not raster_paths:
                continue
            entries.append(
                _ConfiguredSource(
                    identifier=identifier,
                    name=str(raw.get("display_name") or identifier),
                    raster_paths=raster_paths,
                    layer_type=layer_type,
                    priority=self._int_or(raw.get("priority"), 0),
                    resolution_m=self._positive_float(raw.get("resolution_m")),
                    coverage=self._coverage(raw.get("coverage")),
                )
            )
        return tuple(
            sorted(
                entries,
                key=lambda entry: (
                    -entry.priority,
                    entry.resolution_m,
                    entry.identifier,
                ),
            )
        )

    def _load_config_with_path(self) -> tuple[dict[str, object], Path | None]:
        for path in self._candidate_config_paths():
            try:
                with path.open("r", encoding="utf-8") as handle:
                    value = json.load(handle)
                if isinstance(value, dict):
                    return value, path.resolve(strict=False)
            except FileNotFoundError:
                continue
            except (OSError, json.JSONDecodeError) as exc:
                log.warning(
                    "MGP: [surface.adapter] [invalid config path=%s error=%s]",
                    path,
                    exc,
                )
        return {}, None

    def _candidate_config_paths(self) -> tuple[Path, ...]:
        if self._config_paths is not None:
            return tuple(path.resolve(strict=False) for path in self._config_paths)

        # The configured TerraLab data root is authoritative. Application state
        # is only a compatibility fallback; it must never silently override the
        # selected external library.
        candidates = (
            resolve_data_root() / "config" / "data_sources.json",
            application_state_root() / "config" / "data_sources.json",
        )
        unique: list[Path] = []
        for path in candidates:
            resolved = path.resolve(strict=False)
            if resolved not in unique:
                unique.append(resolved)
        return tuple(unique)

    @staticmethod
    def _selection(payload: dict[str, object], key: str) -> dict[str, object]:
        selections = payload.get("selections")
        if not isinstance(selections, dict):
            return {}
        value = selections.get(key)
        return value if isinstance(value, dict) else {}

    def _raster_paths(
        self,
        raw: dict[str, object],
        config_path: Path,
    ) -> tuple[Path, ...]:
        base_path = self._resolve_configured_path(raw.get("path"), config_path)
        candidates: list[Path] = []

        if base_path is not None and base_path.is_file():
            candidates.append(base_path)

        metadata = raw.get("metadata")
        if isinstance(metadata, dict):
            rasters = metadata.get("rasters")
            if isinstance(rasters, list):
                for raster in rasters:
                    if not isinstance(raster, dict):
                        continue
                    paths = raster.get("paths", raster.get("path"))
                    for raw_path in self._iter_raw_paths(paths):
                        resolved = self._resolve_configured_path(
                            raw_path,
                            config_path,
                            directory_hint=base_path if base_path and base_path.is_dir() else None,
                        )
                        if (
                            resolved is not None
                            and resolved.is_file()
                        ):
                            candidates.append(resolved)

        if base_path is not None and base_path.is_dir() and not candidates:
            candidates.extend(path for path in sorted(base_path.rglob("*")) if path.is_file())

        unique: list[Path] = []
        for path in candidates:
            resolved = path.resolve(strict=False)
            if resolved not in unique:
                unique.append(resolved)
        return tuple(unique)

    @staticmethod
    def _iter_raw_paths(value: object) -> Iterable[object]:
        if isinstance(value, (str, Path)):
            yield value
        elif isinstance(value, list):
            for item in value:
                if isinstance(item, (str, Path)):
                    yield item

    @staticmethod
    def _resolve_configured_path(
        value: object,
        config_path: Path,
        *,
        directory_hint: Path | None = None,
    ) -> Path | None:
        if not isinstance(value, (str, Path)):
            return None
        raw = str(value).strip()
        if not raw:
            return None
        path = Path(raw).expanduser()
        if path.is_absolute():
            return path.resolve(strict=False)

        candidates: list[Path] = []
        if directory_hint is not None:
            candidates.append(directory_hint / path)
        candidates.extend(
            (
                resolve_data_root() / path,
                config_path.parent / path,
                config_path.parent.parent / path,
                path,
            )
        )
        for candidate in candidates:
            resolved = candidate.expanduser().resolve(strict=False)
            if resolved.exists():
                return resolved
        return candidates[0].expanduser().resolve(strict=False)

    @staticmethod
    def _coverage(value: object) -> tuple[float, float, float, float] | None:
        if not isinstance(value, list) or len(value) != 4:
            return None
        try:
            return tuple(float(component) for component in value)  # type: ignore[return-value]
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _positive_float(value: object) -> float:
        try:
            number = float(value)  # type: ignore[arg-type]
        except (TypeError, ValueError):
            return float("inf")
        return number if math.isfinite(number) and number > 0.0 else float("inf")

    @staticmethod
    def _int_or(value: object, fallback: int) -> int:
        try:
            return int(value)  # type: ignore[arg-type]
        except (TypeError, ValueError):
            return fallback

    @staticmethod
    def _source_sort_key(raw: dict[str, object]) -> tuple[int, float, str]:
        try:
            priority = int(raw.get("priority", 0))
        except (TypeError, ValueError):
            priority = 0
        try:
            resolution = float(raw.get("resolution_m", float("inf")))
        except (TypeError, ValueError):
            resolution = float("inf")
        if not math.isfinite(resolution) or resolution <= 0:
            resolution = float("inf")
        return -priority, resolution, str(raw.get("id", ""))

    @staticmethod
    def _legend_id(raw: dict[str, object]) -> str | None:
        direct = raw.get("legend_id")
        if isinstance(direct, str) and direct.strip():
            return direct.strip()
        metadata = raw.get("metadata")
        if isinstance(metadata, dict):
            value = metadata.get("legend_id")
            if isinstance(value, str) and value.strip():
                return value.strip()
        return None

    @staticmethod
    def _scheme_metadata(
        raw: dict[str, object],
    ) -> tuple[str | None, str | None, str | None]:
        metadata = raw.get("metadata")
        metadata_mapping = metadata if isinstance(metadata, dict) else {}
        raw_key = raw.get("scheme_key", metadata_mapping.get("scheme_key"))
        raw_version = raw.get("scheme_version", metadata_mapping.get("scheme_version"))
        raw_revision = raw.get("mapping_revision", metadata_mapping.get("mapping_revision"))
        scheme_key = raw_key.strip() if isinstance(raw_key, str) and raw_key.strip() else None
        scheme_version = (
            raw_version.strip()
            if isinstance(raw_version, str) and raw_version.strip()
            else None
        )
        mapping_revision = (
            raw_revision.strip()
            if isinstance(raw_revision, str) and raw_revision.strip()
            else None
        )
        return scheme_key, scheme_version, mapping_revision

    @staticmethod
    def _dataset_resolution_hint(dataset: rasterio.io.DatasetReader) -> float:
        x = abs(float(dataset.transform.a))
        y = abs(float(dataset.transform.e))
        value = max(x, y)
        return value if math.isfinite(value) and value > 0.0 else float("inf")

    def _sample_source(
        self,
        source: _ConfiguredSource,
        latitude: np.ndarray,
        longitude: np.ndarray,
        cancellation_check: Callable[[], bool] | None,
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        if not source.raster_paths:
            raise FileNotFoundError(source.identifier)

        # Pas-16 compatibility: use the first configured raster containing the
        # requested points. Pas 17 will replace this with independent grid/tile
        # reads and nearest-neighbour reprojection.
        for raster_path in source.raster_paths:
            sampled = self._sample_one_raster(
                raster_path,
                source.layer_type,
                latitude,
                longitude,
                cancellation_check,
            )
            if sampled is None:
                continue
            rgba, valid, classes = sampled
            if np.any(valid):
                return rgba, valid, classes

        return (
            np.zeros((latitude.size, 4), dtype=np.uint8),
            np.zeros(latitude.size, dtype=bool),
            np.zeros(latitude.size, dtype=np.uint16),
        )

    def _sample_one_raster(
        self,
        raster_path: Path,
        layer_type: str,
        latitude: np.ndarray,
        longitude: np.ndarray,
        cancellation_check: Callable[[], bool] | None,
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray] | None:
        with rasterio.open(raster_path) as dataset:
            if dataset.crs is None:
                return None
            transformer = self._transformers.get(str(dataset.crs))
            if transformer is None:
                transformer = Transformer.from_crs(
                    "EPSG:4326",
                    dataset.crs,
                    always_xy=True,
                )
                self._transformers[str(dataset.crs)] = transformer

            x, y = transformer.transform(longitude.tolist(), latitude.tolist())
            x = np.asarray(x, dtype=np.float64)
            y = np.asarray(y, dtype=np.float64)
            inverse = ~dataset.transform
            columns = np.floor(inverse.a * x + inverse.b * y + inverse.c).astype(np.int64)
            rows = np.floor(inverse.d * x + inverse.e * y + inverse.f).astype(np.int64)
            inside = (
                np.isfinite(x)
                & np.isfinite(y)
                & (columns >= 0)
                & (columns < dataset.width)
                & (rows >= 0)
                & (rows < dataset.height)
            )

            rgba = np.zeros((latitude.size, 4), dtype=np.uint8)
            valid = np.zeros(latitude.size, dtype=bool)
            classes = np.zeros(latitude.size, dtype=np.uint16)
            if not np.any(inside):
                return rgba, valid, classes

            query = np.flatnonzero(inside)
            if cancellation_check is not None and cancellation_check():
                raise InterruptedError("Surface sampling cancelled")
            coordinates = list(zip(x[query].tolist(), y[query].tolist(), strict=True))

            if layer_type in {"surface_rgb", "land_cover_rgb"}:
                if dataset.count < 3:
                    return rgba, valid, classes
                values = np.asarray(
                    list(dataset.sample(coordinates, indexes=(1, 2, 3))),
                    dtype=np.float64,
                )
                rgb = _normalise_rgb(values, dataset.dtypes[:3])
                rgba[query, :3] = rgb
                rgba[query, 3] = 255
                valid[query] = True
            else:
                values = np.asarray(
                    list(dataset.sample(coordinates, indexes=1)),
                    dtype=np.int64,
                ).reshape(-1)
                nodata = dataset.nodata
                sample_valid = np.ones(values.shape, dtype=bool)
                if nodata is not None and np.isfinite(float(nodata)):
                    sample_valid &= values != int(nodata)

                clipped = np.clip(
                    values,
                    0,
                    np.iinfo(np.uint16).max,
                ).astype(np.uint16)
                classes[query] = clipped
                valid[query] = sample_valid

                try:
                    colormap = dataset.colormap(1)
                except (ValueError, rasterio.errors.RasterioError):
                    colormap = {}

                if colormap:
                    for value in np.unique(values[sample_valid]):
                        color = colormap.get(int(value))
                        if color is None:
                            continue
                        selected = query[(values == value) & sample_valid]
                        rgba[selected] = np.asarray(color[:4], dtype=np.uint8)
                    # If the raster has a palette, alpha remains authoritative.
                    valid &= rgba[:, 3] > 0
                else:
                    # The real S2GLC raster is categorical even when the file
                    # does not carry an embedded GDAL colour table. Preserve
                    # class identity; Pas 17 will colour it through its legend.
                    rgba[query[sample_valid], 3] = 255

            rgba[:, :3] = _srgb_to_linear_u8(rgba[:, :3])
            return rgba, valid, classes


def _within_coverage(
    latitude: np.ndarray,
    longitude: np.ndarray,
    coverage: tuple[float, float, float, float] | None,
) -> np.ndarray:
    if coverage is None:
        return np.ones(latitude.shape, dtype=bool)
    west, south, east, north = coverage
    return (
        (longitude >= west)
        & (longitude <= east)
        & (latitude >= south)
        & (latitude <= north)
    )


def _normalise_rgb(
    values: np.ndarray,
    dtypes: tuple[str, ...] | list[str],
) -> np.ndarray:
    result = np.zeros(values.shape, dtype=np.uint8)
    for channel in range(3):
        dtype = np.dtype(dtypes[channel])
        upper = np.iinfo(dtype).max if np.issubdtype(dtype, np.integer) else 1.0
        result[:, channel] = np.rint(
            np.clip(
                values[:, channel] / max(1.0, float(upper)),
                0.0,
                1.0,
            )
            * 255.0
        ).astype(np.uint8)
    return result


def _srgb_to_linear_u8(rgb: np.ndarray) -> np.ndarray:
    srgb = np.asarray(rgb, dtype=np.float32) / 255.0
    linear = np.where(
        srgb <= 0.04045,
        srgb / 12.92,
        ((srgb + 0.055) / 1.055) ** 2.4,
    )
    return np.rint(np.clip(linear, 0.0, 1.0) * 255.0).astype(np.uint8)
