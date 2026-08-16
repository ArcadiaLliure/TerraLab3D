"""Raster Land-Cover Adapter implementing LandCoverPort.

Separation of concerns:
  - Exclusively reads categorical and semantic land-cover sources.
  - Pure RGB orthophotos are completely excluded.
  - Respects CRS transforms via pyproj (always_xy=True).
  - Uses nearest-neighbor sampling for discrete category boundaries.
  - Decodes native colormaps and explicit legends.
  - Never mutates DEM height or geometry.
"""

from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Sequence

import numpy as np
import rasterio
from pyproj import Transformer

from terralab3d.domain.surface.calculations import (
    build_palette_index_map,
    decode_rgb_to_class,
)
from terralab3d.domain.surface.errors import (
    LandCoverInvalidCrs,
    LandCoverSamplingCancelled,
    LandCoverUnavailable,
)
from terralab3d.domain.surface.models import (
    LandCoverLegend,
    LandCoverLegendEntry,
    LandCoverProvenance,
    LandCoverSampleGrid,
    LandCoverSamplingRequest,
    LandCoverSourceDescriptor,
    LandCoverSourceType,
)
from terralab3d.domain.surface.services import (
    select_sources_automatic,
    select_sources_manual,
)
from terralab3d.infrastructure.app_paths import application_state_root, resolve_data_root

log = logging.getLogger("terralab3d.landcover")


# ─── Built-in standard legends ────────────────────────────────────────

# S2GLC standard classes (Original palette)
S2GLC_ENTRIES = (
    LandCoverLegendEntry(0, "Clouds", (255, 255, 255, 255), is_nodata=True, is_transparent=True),
    LandCoverLegendEntry(62, "Artificial surfaces and constructions", (210, 0, 0, 255)),
    LandCoverLegendEntry(73, "Cultivated areas", (253, 211, 39, 255)),
    LandCoverLegendEntry(75, "Vineyards", (176, 91, 16, 255)),
    LandCoverLegendEntry(82, "Broadleaf tree cover", (35, 152, 0, 255)),
    LandCoverLegendEntry(83, "Coniferous tree cover", (8, 98, 0, 255)),
    LandCoverLegendEntry(102, "Herbaceous vegetation", (249, 150, 39, 255)),
    LandCoverLegendEntry(103, "Moors and Heathland", (141, 139, 0, 255)),
    LandCoverLegendEntry(104, "Sclerophyllous vegetation", (95, 53, 6, 255)),
    LandCoverLegendEntry(105, "Marshes", (149, 107, 196, 255)),
    LandCoverLegendEntry(106, "Peatbogs", (77, 37, 106, 255)),
    LandCoverLegendEntry(121, "Natural material surfaces", (154, 154, 154, 255)),
    LandCoverLegendEntry(123, "Permanent snow covered surfaces", (106, 255, 255, 255)),
    LandCoverLegendEntry(162, "Water bodies", (20, 69, 249, 255)),
    LandCoverLegendEntry(255, "No data", (255, 255, 255, 255), is_nodata=True, is_transparent=True),
)

# CLC (CORINE Land Cover) level 2/3 summary entries
CLC_ENTRIES = (
    LandCoverLegendEntry(0, "No data", (0, 0, 0, 0), is_nodata=True, is_transparent=True),
    LandCoverLegendEntry(1, "Continuous urban fabric", (230, 0, 77, 255)),
    LandCoverLegendEntry(2, "Discontinuous urban fabric", (255, 0, 0, 255)),
    LandCoverLegendEntry(3, "Industrial or commercial units", (204, 77, 242, 255)),
    LandCoverLegendEntry(12, "Non-irrigated arable land", (255, 255, 168, 255)),
    LandCoverLegendEntry(18, "Pastures", (230, 230, 77, 255)),
    LandCoverLegendEntry(23, "Broad-leaved forest", (128, 255, 0, 255)),
    LandCoverLegendEntry(24, "Coniferous forest", (0, 166, 0, 255)),
    LandCoverLegendEntry(25, "Mixed forest", (77, 255, 0, 255)),
    LandCoverLegendEntry(26, "Natural grasslands", (204, 242, 77, 255)),
    LandCoverLegendEntry(27, "Moors and heathland", (166, 255, 128, 255)),
    LandCoverLegendEntry(29, "Transitional woodland-shrub", (166, 242, 0, 255)),
    LandCoverLegendEntry(30, "Beaches, dunes, sands", (230, 230, 230, 255)),
    LandCoverLegendEntry(31, "Bare rocks", (204, 204, 204, 255)),
    LandCoverLegendEntry(32, "Sparsely vegetated areas", (204, 255, 204, 255)),
    LandCoverLegendEntry(35, "Inland marshes", (166, 166, 255, 255)),
    LandCoverLegendEntry(36, "Peat bogs", (77, 77, 255, 255)),
    LandCoverLegendEntry(40, "Water courses", (0, 204, 242, 255)),
    LandCoverLegendEntry(41, "Water bodies", (128, 242, 230, 255)),
    LandCoverLegendEntry(42, "Coastal lagoons", (0, 255, 166, 255)),
    LandCoverLegendEntry(44, "Sea and ocean", (230, 242, 255, 255)),
)

STANDARD_LEGENDS: dict[str, LandCoverLegend] = {
    "s2glc": LandCoverLegend("s2glc", "s2glc-global", S2GLC_ENTRIES),
    "clc": LandCoverLegend("clc", "corine-land-cover", CLC_ENTRIES),
}


@dataclass(frozen=True, slots=True)
class _SourceInternal:
    descriptor: LandCoverSourceDescriptor
    path: Path
    dataset_legend: LandCoverLegend | None = None


class RasterLandCoverAdapter:
    """Production LandCoverPort implementation for raster land cover datasets."""

    def __init__(self, config_paths: tuple[Path, ...] | None = None) -> None:
        self._config_paths = config_paths
        self._transformers: dict[str, Transformer] = {}
        self._cached_sources: list[_SourceInternal] | None = None
        self._custom_legends: dict[str, LandCoverLegend] = {}

    def metadata(self) -> list[LandCoverSourceDescriptor]:
        sources = self._get_sources()
        return [s.descriptor for s in sources]

    def legend(self, legend_id: str) -> LandCoverLegend:
        key = legend_id.strip().lower()
        if key in self._custom_legends:
            return self._custom_legends[key]
        if key in STANDARD_LEGENDS:
            return STANDARD_LEGENDS[key]
        for src in self._get_sources():
            if src.dataset_legend and (src.dataset_legend.legend_id.lower() == key or src.descriptor.id.lower() == key):
                return src.dataset_legend
        # Default fallback to S2GLC legend
        return STANDARD_LEGENDS["s2glc"]

    def sample_classes(
        self,
        request: LandCoverSamplingRequest,
    ) -> LandCoverSampleGrid:
        latitude = np.asarray(request.latitude_deg, dtype=np.float64).reshape(-1)
        longitude = np.asarray(request.longitude_deg, dtype=np.float64).reshape(-1)
        count = latitude.size

        class_ids = np.zeros(count, dtype=np.uint16)
        colors_rgba = np.zeros((count, 4), dtype=np.uint8)
        valid = np.zeros(count, dtype=bool)
        source_slots = np.zeros(count, dtype=np.int16)
        provenance = np.full(count, LandCoverProvenance.NODATA.value, dtype=np.uint8)

        sources = self._get_sources()
        descriptors = [s.descriptor for s in sources]
        if request.selected_source_id:
            ordered_descriptors = select_sources_manual(descriptors, request.selected_source_id)
        else:
            ordered_descriptors = select_sources_automatic(descriptors)

        source_by_id = {s.descriptor.id: s for s in sources}
        primary_legend: LandCoverLegend | None = None

        cancel_fn: Callable[[], bool] | None = None
        if callable(request.cancellation_check):
            cancel_fn = request.cancellation_check

        for slot_idx, desc in enumerate(ordered_descriptors, start=1):
            if cancel_fn and cancel_fn():
                raise LandCoverSamplingCancelled("Sampling cancelled")

            if np.all(valid):
                break

            internal = source_by_id.get(desc.id)
            if internal is None or not internal.path.is_file():
                continue

            try:
                with rasterio.open(internal.path) as dataset:
                    if dataset.crs is None:
                        continue
                    crs_key = str(dataset.crs)
                    transformer = self._transformers.get(crs_key)
                    if transformer is None:
                        transformer = Transformer.from_crs("EPSG:4326", dataset.crs, always_xy=True)
                        self._transformers[crs_key] = transformer

                    dataset_bounds = dataset.bounds
                    
                    unresolved_idx = np.where(~valid)[0]
                    if unresolved_idx.size == 0:
                        break
                        
                    xs, ys = transformer.transform(
                        longitude[unresolved_idx],
                        latitude[unresolved_idx]
                    )
                    xs = np.asarray(xs)
                    ys = np.asarray(ys)
                    
                    in_bounds_mask = (
                        (xs >= dataset_bounds.left) & (xs <= dataset_bounds.right) &
                        (ys >= dataset_bounds.bottom) & (ys <= dataset_bounds.top)
                    )
                    
                    in_bounds_local_idx = np.where(in_bounds_mask)[0]
                    if in_bounds_local_idx.size == 0:
                        continue
                        
                    xs_in = xs[in_bounds_local_idx]
                    ys_in = ys[in_bounds_local_idx]
                    pts = list(zip(xs_in, ys_in))

                    src_legend = internal.dataset_legend or self.legend(internal.descriptor.legend_id or "s2glc")
                    if primary_legend is None and src_legend is not None:
                        primary_legend = src_legend
                        
                    sampled_gen = dataset.sample(pts)
                    sampled = np.fromiter((val[0] for val in sampled_gen), dtype=np.float32, count=len(pts))
                    
                    nodata = dataset.nodata
                    valid_sample_mask = np.ones(len(pts), dtype=bool)
                    if nodata is not None:
                         valid_sample_mask = (sampled != nodata)
                         
                    if not np.any(valid_sample_mask):
                        continue

                    # Crea el mapeig RGBA
                    max_val = int(np.max(sampled[valid_sample_mask])) if len(sampled[valid_sample_mask]) > 0 else 0
                    lut_rgba = np.zeros((max_val + 1, 4), dtype=np.uint8)
                    for entry in src_legend.entries:
                        if entry.class_id <= max_val:
                            lut_rgba[entry.class_id] = entry.rgba

                    valid_indices = in_bounds_local_idx[valid_sample_mask]
                    global_indices = unresolved_idx[valid_indices]
                    sampled_valid = sampled[valid_sample_mask].astype(np.int64)

                    class_ids[global_indices] = sampled_valid.astype(np.uint16)
                    colors_rgba[global_indices] = lut_rgba[sampled_valid]
                    source_slots[global_indices] = slot_idx
                    valid[global_indices] = True
                    provenance[global_indices] = LandCoverProvenance.EXACT.value
            except Exception as exc:
                log.warning("MGP: [landcover.adapter] [Vertex sampling failed id=%s path=%s error=%s]", desc.id, internal.path, exc)
                continue

        if primary_legend is None:
            primary_legend = STANDARD_LEGENDS["s2glc"]

        resolved_fraction = float(np.count_nonzero(valid) / valid.size)
        fallback_fraction = 0.0

        return LandCoverSampleGrid(
            class_ids=class_ids,
            palette_indices=np.zeros(count, dtype=np.uint16),
            source_slots=source_slots,
            valid=valid,
            provenance=provenance,
            resolved_fraction=resolved_fraction,
            fallback_fraction=fallback_fraction,
            source_descriptors=tuple(ordered_descriptors),
            legend=primary_legend,
            colors_rgba=colors_rgba,
        )

    def close(self) -> None:
        self._transformers.clear()
        self._cached_sources = None

    # ─── Internal helpers ─────────────────────────────────────────────

    def _get_sources(self) -> list[_SourceInternal]:
        if self._cached_sources is not None:
            return self._cached_sources

        payload = self._load_config()
        raw_sources = payload.get("sources", []) if isinstance(payload, dict) else []
        results: list[_SourceInternal] = []

        for raw in raw_sources if isinstance(raw_sources, list) else []:
            if not isinstance(raw, dict) or not bool(raw.get("enabled", True)):
                continue
            layer_type = str(raw.get("layer_type", "")).strip().lower()
            # ONLY categorical land cover sources; exclude pure orthophoto / surface_rgb
            if layer_type not in {"land_cover_categorical", "land_cover_rgb", "categorical"}:
                continue

            identifier = str(raw.get("id", "")).strip()
            raw_path = str(raw.get("path", "")).strip()
            if not raw_path:
                continue

            path = Path(raw_path)
            # Try to resolve relative path against config directory
            if not path.is_file():
                for root in (application_state_root(), resolve_data_root()):
                    candidate = root / raw_path
                    if candidate.is_file():
                        path = candidate
                        break

            coverage = raw.get("coverage")
            valid_coverage = (
                tuple(float(v) for v in coverage)
                if isinstance(coverage, list) and len(coverage) == 4
                else None
            )

            is_rgb = layer_type == "land_cover_rgb"
            source_type = (
                LandCoverSourceType.CATEGORICAL_RGB
                if is_rgb
                else LandCoverSourceType.CATEGORICAL_NATIVE
            )

            legend_id = str(raw.get("legend_id") or ("s2glc" if not is_rgb else "custom")).strip()

            # Inspect raster if available
            crs_str = None
            resolution_m = float(raw.get("resolution_m") or 10.0)
            bounds = None
            dataset_legend: LandCoverLegend | None = None
            fingerprint = f"{identifier}:{raw_path}"

            if path.is_file():
                try:
                    stat = path.stat()
                    fingerprint = hashlib.blake2b(
                        f"{path}:{stat.st_size}:{stat.st_mtime_ns}".encode(),
                        digest_size=12,
                    ).hexdigest()
                    with rasterio.open(path) as ds:
                        crs_str = str(ds.crs) if ds.crs else None
                        bounds = (ds.bounds.left, ds.bounds.bottom, ds.bounds.right, ds.bounds.top)
                        if valid_coverage is None and crs_str and "4326" not in crs_str:
                            try:
                                tf = Transformer.from_crs(crs_str, "EPSG:4326", always_xy=True)
                                lons, lats = tf.transform(
                                    [bounds[0], bounds[2], bounds[2], bounds[0]],
                                    [bounds[1], bounds[1], bounds[3], bounds[3]]
                                )
                                valid_coverage = (float(min(lons)), float(min(lats)), float(max(lons)), float(max(lats)))
                            except Exception as e:
                                log.warning("MGP: [landcover.adapter] [could not reproject bounds %s: %s]", crs_str, e)
                        
                        # Check for embedded colormap
                        if ds.count == 1:
                            try:
                                cmap = ds.colormap(1)
                            except (ValueError, Exception):
                                cmap = None
                            if cmap:
                                entries = [
                                    LandCoverLegendEntry(
                                        class_id=k,
                                        name=f"Class {k}",
                                        rgba=(v[0], v[1], v[2], v[3]),
                                        is_nodata=(v[3] == 0),
                                        is_transparent=(v[3] == 0),
                                    )
                                    for k, v in cmap.items()
                                ]
                                dataset_legend = LandCoverLegend(
                                    legend_id=f"cmap-{identifier}",
                                    source_id=identifier,
                                    entries=tuple(entries),
                                )
                except Exception as exc:
                    log.debug("MGP: [landcover.adapter] [could not inspect dataset: %s]", exc)

            descriptor = LandCoverSourceDescriptor(
                id=identifier,
                name=str(raw.get("display_name") or identifier),
                source_type=source_type,
                crs=crs_str,
                resolution_m=resolution_m,
                bounds=bounds,
                coverage=valid_coverage,
                priority=int(raw.get("priority", 1)),
                legend_id=legend_id,
                fingerprint=fingerprint,
                provenance=str(raw.get("provenance") or ""),
                attribution=str(raw.get("attribution") or ""),
                enabled=True,
            )
            results.append(_SourceInternal(descriptor, path, dataset_legend))

        # Auto-discover unconfigured surface rasters in data root if not explicit config
        known_paths = {s.path.resolve() for s in results if s.path.exists()}
        for base_dir in (
            resolve_data_root() / "data" / "earth" / "surface",
            resolve_data_root() / "earth" / "surface",
        ):
            if not base_dir.is_dir():
                continue
            for tif_path in base_dir.rglob("*.tif"):
                if not tif_path.is_file() or tif_path.resolve() in known_paths:
                    continue
                name_lower = tif_path.name.lower()
                is_rgb = "rgb" in name_lower
                source_type = (
                    LandCoverSourceType.CATEGORICAL_RGB
                    if is_rgb
                    else LandCoverSourceType.CATEGORICAL_NATIVE
                )
                legend_id = "s2glc" if "s2glc" in name_lower else ("clc" if "clc" in name_lower or "corine" in name_lower else "s2glc")
                identifier = tif_path.stem

                crs_str = None
                bounds = None
                dataset_legend: LandCoverLegend | None = None
                fingerprint = f"{identifier}:{tif_path}"
                valid_coverage = None
                try:
                    stat = tif_path.stat()
                    fingerprint = hashlib.blake2b(
                        f"{tif_path}:{stat.st_size}:{stat.st_mtime_ns}".encode(),
                        digest_size=12,
                    ).hexdigest()
                    with rasterio.open(tif_path) as ds:
                        crs_str = str(ds.crs) if ds.crs else None
                        bounds = (ds.bounds.left, ds.bounds.bottom, ds.bounds.right, ds.bounds.top)
                        if crs_str and "4326" not in crs_str:
                            try:
                                tf = Transformer.from_crs(crs_str, "EPSG:4326", always_xy=True)
                                lons, lats = tf.transform(
                                    [bounds[0], bounds[2], bounds[2], bounds[0]],
                                    [bounds[1], bounds[1], bounds[3], bounds[3]]
                                )
                                valid_coverage = (float(min(lons)), float(min(lats)), float(max(lons)), float(max(lats)))
                            except Exception as e:
                                log.warning("MGP: [landcover.adapter] [could not reproject discovered bounds %s: %s]", crs_str, e)
                        if ds.count == 1:
                            try:
                                cmap = ds.colormap(1)
                            except (ValueError, Exception):
                                cmap = None
                            if cmap:
                                entries = [
                                    LandCoverLegendEntry(
                                        class_id=k,
                                        name=f"Class {k}",
                                        rgba=(v[0], v[1], v[2], v[3]),
                                        is_nodata=(v[3] == 0),
                                        is_transparent=(v[3] == 0),
                                    )
                                    for k, v in cmap.items()
                                ]
                                dataset_legend = LandCoverLegend(
                                    legend_id=f"cmap-{identifier}",
                                    source_id=identifier,
                                    entries=tuple(entries),
                                )
                except Exception as exc:
                    log.debug("MGP: [landcover.adapter] [could not inspect discovered dataset: %s]", exc)

                disp_name = (
                    "S2GLC Europe 2017 (10 m)"
                    if "s2glc" in name_lower and not is_rgb
                    else (
                        "S2GLC Europe RGB (10 m)"
                        if "s2glc" in name_lower and is_rgb
                        else identifier.replace("_", " ")
                    )
                )
                priority = 100 if "s2glc" in name_lower and not is_rgb else (50 if is_rgb else 80)

                desc = LandCoverSourceDescriptor(
                    id=identifier,
                    name=disp_name,
                    source_type=source_type,
                    crs=crs_str,
                    resolution_m=10.0 if "s2glc" in name_lower else 20.0,
                    bounds=bounds,
                    coverage=valid_coverage,
                    priority=priority,
                    legend_id=legend_id,
                    fingerprint=fingerprint,
                    provenance="Discovered in local surface library",
                    attribution="ESA / CBK PAN" if "s2glc" in name_lower else "",
                    enabled=True,
                )
                results.append(_SourceInternal(desc, tif_path, dataset_legend))
                known_paths.add(tif_path.resolve())

        self._cached_sources = results
        return results

    def _load_config(self) -> dict[str, object]:
        candidates = self._config_paths or (
            application_state_root() / "config" / "data_sources.json",
            resolve_data_root() / "config" / "data_sources.json",
        )
        for path in candidates:
            try:
                with path.open("r", encoding="utf-8") as handle:
                    val = json.load(handle)
                if isinstance(val, dict):
                    return val
            except FileNotFoundError:
                continue
            except (OSError, json.JSONDecodeError) as exc:
                log.warning("MGP: [landcover.adapter] [invalid config path=%s error=%s]", path, exc)
        return {}

    def _sample_raster(
        self,
        internal: _SourceInternal,
        latitude: np.ndarray,
        longitude: np.ndarray,
        cancel_fn: Callable[[], bool] | None,
    ) -> tuple[np.ndarray, np.ndarray, LandCoverLegend | None]:
        with rasterio.open(internal.path) as dataset:
            if dataset.crs is None:
                raise LandCoverInvalidCrs(f"Raster {internal.path} has no CRS")

            crs_key = str(dataset.crs)
            transformer = self._transformers.get(crs_key)
            if transformer is None:
                transformer = Transformer.from_crs("EPSG:4326", dataset.crs, always_xy=True)
                self._transformers[crs_key] = transformer

            x, y = transformer.transform(longitude.tolist(), latitude.tolist())
            x = np.asarray(x, dtype=np.float64)
            y = np.asarray(y, dtype=np.float64)

            rows, columns = rasterio.transform.rowcol(dataset.transform, x, y)
            rows = np.asarray(rows, dtype=np.int64)
            columns = np.asarray(columns, dtype=np.int64)

            inside = (
                np.isfinite(x) & np.isfinite(y)
                & (columns >= 0) & (columns < dataset.width)
                & (rows >= 0) & (rows < dataset.height)
            )

            count = latitude.size
            class_ids = np.zeros(count, dtype=np.uint16)
            valid = np.zeros(count, dtype=bool)

            if not np.any(inside):
                return class_ids, valid, internal.dataset_legend

            query = np.flatnonzero(inside)
            if cancel_fn and cancel_fn():
                raise LandCoverSamplingCancelled("Sampling cancelled")

            coords = list(zip(x[query].tolist(), y[query].tolist(), strict=True))

            legend = internal.dataset_legend or self.legend(internal.descriptor.legend_id or "s2glc")

            if internal.descriptor.source_type == LandCoverSourceType.CATEGORICAL_RGB and dataset.count >= 3:
                # RGB-categorical raster: exact color match decode
                sampled = np.asarray(list(dataset.sample(coords, indexes=(1, 2, 3))), dtype=np.uint8)
                decoded_ids, decoded_valid = decode_rgb_to_class(sampled, legend)
                class_ids[query] = decoded_ids
                valid[query] = decoded_valid
            else:
                # Native single-band categorical raster (nearest neighbor)
                nodata = dataset.nodata
                sampled = np.asarray(list(dataset.sample(coords, indexes=1)), dtype=np.int64).reshape(-1)
                
                # Check dataset mask / nodata
                mask_valid = np.ones(sampled.shape, dtype=bool)
                if nodata is not None:
                    mask_valid &= (sampled != nodata)
                mask_valid &= (sampled >= 0) & (sampled <= np.iinfo(np.uint16).max)

                # If colormap exists, check if alpha > 0
                try:
                    cmap = dataset.colormap(1)
                except Exception:
                    cmap = None
                if cmap:
                    for val in np.unique(sampled[mask_valid]):
                        c = cmap.get(int(val))
                        if c is not None and c[3] == 0:
                            mask_valid[sampled == val] = False

                class_ids[query] = np.where(mask_valid, sampled.astype(np.uint16), 0)
                valid[query] = mask_valid

            return class_ids, valid, legend


def _within_coverage(
    latitude: np.ndarray,
    longitude: np.ndarray,
    coverage: tuple[float, float, float, float] | None,
) -> np.ndarray:
    if coverage is None:
        return np.ones(latitude.shape, dtype=bool)
    west, south, east, north = coverage
    return (longitude >= west) & (longitude <= east) & (latitude >= south) & (latitude <= north)
