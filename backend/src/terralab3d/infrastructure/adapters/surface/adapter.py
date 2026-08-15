"""Read TerraLab's configured surface sources without coupling them to DEM geometry."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import numpy as np
import rasterio
from pyproj import Transformer

from terralab3d.infrastructure.app_paths import application_state_root, resolve_data_root

log = logging.getLogger("terralab3d.surface")


@dataclass(frozen=True, slots=True)
class SurfaceVertexSamples:
    rgba_linear: np.ndarray
    valid: np.ndarray
    class_ids: np.ndarray
    source_ids: np.ndarray
    source_label: str


@dataclass(frozen=True, slots=True)
class _ConfiguredSource:
    identifier: str
    name: str
    path: Path
    layer_type: str
    priority: int
    resolution_m: float
    coverage: tuple[float, float, float, float] | None


class ConfiguredSurfaceSampler:
    """Surface appearance authority; never changes DEM heights or validity."""

    def __init__(self, config_paths: tuple[Path, ...] | None = None) -> None:
        self._config_paths = config_paths
        self._transformers: dict[str, Transformer] = {}

    def sample(
        self,
        latitude_deg: np.ndarray,
        longitude_deg: np.ndarray,
        *,
        cancellation_check: Callable[[], bool] | None = None,
    ) -> SurfaceVertexSamples:
        latitude = np.asarray(latitude_deg, dtype=np.float64).reshape(-1)
        longitude = np.asarray(longitude_deg, dtype=np.float64).reshape(-1)
        count = latitude.size
        rgba = np.zeros((count, 4), dtype=np.uint8)
        valid = np.zeros(count, dtype=bool)
        classes = np.zeros(count, dtype=np.uint16)
        source_ids = np.zeros(count, dtype=np.int16)
        labels: list[str] = []
        for ordinal, source in enumerate(self._sources(), start=1):
            if cancellation_check is not None and cancellation_check():
                raise InterruptedError("Surface sampling cancelled")
            unresolved = np.flatnonzero(~valid)
            if unresolved.size == 0:
                break
            candidate = unresolved[_within_coverage(
                latitude[unresolved], longitude[unresolved], source.coverage,
            )]
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
        label = "; ".join(dict.fromkeys(labels)) if labels else "TerraLab default terrain palette"
        return SurfaceVertexSamples(rgba, valid, classes, source_ids, label)

    def _sources(self) -> tuple[_ConfiguredSource, ...]:
        payload = self._load_config()
        raw_sources = payload.get("sources", []) if isinstance(payload, dict) else []
        selection = payload.get("selections", {}).get("surface", {}) if isinstance(payload, dict) else {}
        mode = str(selection.get("mode", "automatic")).strip().lower() if isinstance(selection, dict) else "automatic"
        selected_id = str(selection.get("source_id") or "") if isinstance(selection, dict) else ""
        entries: list[_ConfiguredSource] = []
        for raw in raw_sources if isinstance(raw_sources, list) else []:
            if not isinstance(raw, dict) or not bool(raw.get("enabled", True)):
                continue
            layer_type = str(raw.get("layer_type", "")).strip().lower()
            if layer_type not in {"surface_rgb", "orthophoto_rgb", "land_cover_rgb", "land_cover_categorical"}:
                continue
            identifier = str(raw.get("id", "")).strip()
            if mode == "manual" and identifier != selected_id:
                continue
            raw_path = str(raw.get("path", "")).strip()
            if not raw_path:
                continue
            coverage = raw.get("coverage")
            valid_coverage = (
                tuple(float(value) for value in coverage)
                if isinstance(coverage, list) and len(coverage) == 4
                else None
            )
            entries.append(_ConfiguredSource(
                identifier=identifier,
                name=str(raw.get("display_name") or identifier),
                path=Path(raw_path),
                layer_type=layer_type,
                priority=int(raw.get("priority", 0)),
                resolution_m=float(raw.get("resolution_m") or float("inf")),
                coverage=valid_coverage,
            ))
        return tuple(sorted(entries, key=lambda entry: (-entry.priority, entry.resolution_m, entry.identifier)))

    def _load_config(self) -> dict[str, object]:
        candidates = self._config_paths or (
            application_state_root() / "config" / "data_sources.json",
            resolve_data_root() / "config" / "data_sources.json",
        )
        for path in candidates:
            try:
                with path.open("r", encoding="utf-8") as handle:
                    value = json.load(handle)
                if isinstance(value, dict):
                    return value
            except FileNotFoundError:
                continue
            except (OSError, json.JSONDecodeError) as exc:
                log.warning("MGP: [surface.adapter] [invalid config path=%s error=%s]", path, exc)
        return {}

    def _sample_source(
        self,
        source: _ConfiguredSource,
        latitude: np.ndarray,
        longitude: np.ndarray,
        cancellation_check: Callable[[], bool] | None,
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        if not source.path.is_file():
            raise FileNotFoundError(source.path)
        with rasterio.open(source.path) as dataset:
            if dataset.crs is None:
                raise ValueError("surface raster has no CRS")
            transformer = self._transformers.get(str(dataset.crs))
            if transformer is None:
                transformer = Transformer.from_crs("EPSG:4326", dataset.crs, always_xy=True)
                self._transformers[str(dataset.crs)] = transformer
            x, y = transformer.transform(longitude.tolist(), latitude.tolist())
            x = np.asarray(x, dtype=np.float64)
            y = np.asarray(y, dtype=np.float64)
            inverse = ~dataset.transform
            columns = np.floor(inverse.a * x + inverse.b * y + inverse.c).astype(np.int64)
            rows = np.floor(inverse.d * x + inverse.e * y + inverse.f).astype(np.int64)
            inside = (
                np.isfinite(x) & np.isfinite(y)
                & (columns >= 0) & (columns < dataset.width)
                & (rows >= 0) & (rows < dataset.height)
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
            if dataset.count >= 3:
                sampled = np.asarray(list(dataset.sample(coordinates, indexes=(1, 2, 3))), dtype=np.float64)
                rgb = _normalise_rgb(sampled, dataset.dtypes[:3])
                rgba[query, :3] = rgb
                rgba[query, 3] = 255
                valid[query] = True
            else:
                sampled = np.asarray(list(dataset.sample(coordinates, indexes=1)), dtype=np.int64).reshape(-1)
                colormap = dataset.colormap(1)
                for value in np.unique(sampled):
                    color = colormap.get(int(value))
                    if color is None:
                        continue
                    selected = query[sampled == value]
                    rgba[selected] = np.asarray(color[:4], dtype=np.uint8)
                    valid[selected] = int(color[3]) > 0
                    classes[selected] = np.uint16(np.clip(value, 0, np.iinfo(np.uint16).max))
            rgba[:, :3] = _srgb_to_linear_u8(rgba[:, :3])
            return rgba, valid, classes


def _within_coverage(latitude: np.ndarray, longitude: np.ndarray, coverage: tuple[float, float, float, float] | None) -> np.ndarray:
    if coverage is None:
        return np.ones(latitude.shape, dtype=bool)
    west, south, east, north = coverage
    return (longitude >= west) & (longitude <= east) & (latitude >= south) & (latitude <= north)


def _normalise_rgb(values: np.ndarray, dtypes: tuple[str, ...] | list[str]) -> np.ndarray:
    result = np.zeros(values.shape, dtype=np.uint8)
    for channel in range(3):
        dtype = np.dtype(dtypes[channel])
        upper = np.iinfo(dtype).max if np.issubdtype(dtype, np.integer) else 1.0
        result[:, channel] = np.rint(np.clip(values[:, channel] / max(1.0, float(upper)), 0.0, 1.0) * 255.0).astype(np.uint8)
    return result


def _srgb_to_linear_u8(rgb: np.ndarray) -> np.ndarray:
    srgb = np.asarray(rgb, dtype=np.float32) / 255.0
    linear = np.where(srgb <= 0.04045, srgb / 12.92, ((srgb + 0.055) / 1.055) ** 2.4)
    return np.rint(np.clip(linear, 0.0, 1.0) * 255.0).astype(np.uint8)
