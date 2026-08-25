"""Windowed Rasterio harmonization into a persistent TLST mosaic."""

from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path
from typing import Any, Iterable

import numpy as np
import rasterio
from rasterio.enums import Resampling
from rasterio.features import shapes
from rasterio.transform import Affine
from rasterio.vrt import WarpedVRT
from rasterio.windows import Window, bounds as window_bounds
from rasterio.warp import transform_bounds
from shapely.geometry import mapping, shape
from shapely.ops import unary_union

from terralab3d.domain.refinement.errors import RefinementValidationError
from terralab3d.domain.refinement.grid import ResamplingPolicy, TargetGridSpec
from terralab3d.domain.refinement.installations import GeometryRecord
from terralab3d.domain.refinement.mosaic import (
    MosaicUpdateResult,
    RasterRefinementSource,
)
from terralab3d.domain.surface.tlst import TaxonomyCatalog


class RasterRefinementMosaicProcessor:
    """Translate, align and merge only affected target-grid windows."""

    _OUTPUT_NAMES = {
        "mosaic": "refinement_mosaic.tif",
        "source": "refinement_source.tif",
        "quality": "refinement_quality.tif",
        "conflict": "refinement_conflict.tif",
    }

    def __init__(self, taxonomy: TaxonomyCatalog) -> None:
        self._taxonomy = taxonomy
        self._category_codes = {
            category.key: index + 1
            for index, category in enumerate(taxonomy.categories)
        }
        self._semantic_depth = {
            key: len(taxonomy.category_lineage(key))
            for key in taxonomy.category_keys
        }

    def update(
        self,
        output_dir: Path,
        grid: TargetGridSpec,
        sources: tuple[RasterRefinementSource, ...],
    ) -> MosaicUpdateResult:
        if not sources:
            raise RefinementValidationError("At least one refinement source is required")
        if grid.resampling is not ResamplingPolicy.NEAREST:
            raise RefinementValidationError("Categorical TLST mosaics require nearest resampling")
        for source in sources:
            for category_key in source.translations.values():
                self._taxonomy.canonical_category_key(category_key)

        output_dir.mkdir(parents=True, exist_ok=True)
        transform = _grid_transform(grid)
        final_paths = {
            key: output_dir / filename
            for key, filename in self._OUTPUT_NAMES.items()
        }
        manifest_path = output_dir / "refinement_manifest.json"
        previous_manifest = _read_manifest(manifest_path)
        existing = all(path.exists() for path in final_paths.values())
        source_codes = _source_code_registry(previous_manifest, sources)
        target_paths = self._prepare_targets(final_paths, grid, transform, existing)
        updated_windows = self._affected_windows(
            target_paths["mosaic"],
            grid,
            transform,
            sources,
            process_all=not existing,
        )
        conflict_pixels = self._process_windows(
            target_paths,
            grid,
            transform,
            sources,
            source_codes,
            updated_windows,
        )
        self._build_overviews(target_paths)
        for key, target in target_paths.items():
            target.replace(final_paths[key])

        verified = self._verified_geometry(final_paths["mosaic"], grid.crs)
        manifest = self._build_manifest(
            grid,
            sources,
            source_codes,
            previous_manifest,
            updated_windows,
            conflict_pixels,
        )
        _write_json_atomic(manifest_path, manifest)
        return MosaicUpdateResult(
            mosaic_path=final_paths["mosaic"],
            source_path=final_paths["source"],
            quality_path=final_paths["quality"],
            conflict_path=final_paths["conflict"],
            manifest_path=manifest_path,
            verified_geometry=verified,
            updated_windows=tuple(_window_tuple(window) for window in updated_windows),
            conflict_pixels=conflict_pixels,
        )

    @staticmethod
    def _prepare_targets(
        final_paths: dict[str, Path],
        grid: TargetGridSpec,
        transform: Affine,
        existing: bool,
    ) -> dict[str, Path]:
        target_paths = {
            key: path.with_suffix(path.suffix + ".next")
            for key, path in final_paths.items()
        }
        for path in target_paths.values():
            path.unlink(missing_ok=True)
        if existing:
            for key, final in final_paths.items():
                shutil.copy2(final, target_paths[key])
            return target_paths

        block_x = 16 if grid.width <= 256 else 256
        block_y = 16 if grid.height <= 256 else 256
        base_profile: dict[str, Any] = {
            "driver": "GTiff",
            "width": grid.width,
            "height": grid.height,
            "count": 1,
            "crs": grid.crs,
            "transform": transform,
            "tiled": True,
            "blockxsize": block_x,
            "blockysize": block_y,
            "compress": "DEFLATE",
            "bigtiff": "IF_SAFER",
        }
        for key, path in target_paths.items():
            dtype = "uint8" if key in {"quality", "conflict"} else "uint16"
            with rasterio.open(path, "w", **base_profile, dtype=dtype, nodata=0) as dataset:
                dataset.write(np.zeros((grid.height, grid.width), dtype=dtype), 1)
        return target_paths

    @staticmethod
    def _affected_windows(
        mosaic_path: Path,
        grid: TargetGridSpec,
        transform: Affine,
        sources: tuple[RasterRefinementSource, ...],
        *,
        process_all: bool,
    ) -> tuple[Window, ...]:
        with rasterio.open(mosaic_path) as destination:
            blocks = tuple(window for _, window in destination.block_windows(1))
        if process_all:
            return blocks
        source_bounds: list[tuple[float, float, float, float]] = []
        for source in sources:
            with rasterio.open(source.path) as dataset:
                source_bounds.append(
                    transform_bounds(dataset.crs, grid.crs, *dataset.bounds, densify_pts=21)
                )
        affected = []
        for window in blocks:
            bounds = window_bounds(window, transform)
            if any(_bounds_intersect(bounds, candidate) for candidate in source_bounds):
                affected.append(window)
        return tuple(affected)

    def _process_windows(
        self,
        paths: dict[str, Path],
        grid: TargetGridSpec,
        transform: Affine,
        sources: tuple[RasterRefinementSource, ...],
        source_codes: dict[str, int],
        windows: tuple[Window, ...],
    ) -> int:
        ordered_sources = tuple(sorted(sources, key=lambda item: (item.priority, item.source_id)))
        conflict_pixels = 0
        with (
            rasterio.open(paths["mosaic"], "r+") as mosaic_ds,
            rasterio.open(paths["source"], "r+") as source_ds,
            rasterio.open(paths["quality"], "r+") as quality_ds,
            rasterio.open(paths["conflict"], "r+") as conflict_ds,
        ):
            for window in windows:
                mosaic = mosaic_ds.read(1, window=window)
                winner_source = source_ds.read(1, window=window)
                quality = quality_ds.read(1, window=window)
                conflict = conflict_ds.read(1, window=window)
                for source in ordered_sources:
                    translated, candidate_quality = self._read_translated_window(
                        source,
                        grid,
                        transform,
                        window,
                    )
                    valid = translated > 0
                    disagreements = valid & (mosaic > 0) & (mosaic != translated)
                    conflict[disagreements] = 1
                    wins = valid & (candidate_quality > quality)
                    mosaic[wins] = translated[wins]
                    winner_source[wins] = source_codes[source.source_id]
                    quality[wins] = candidate_quality[wins]
                mosaic_ds.write(mosaic, 1, window=window)
                source_ds.write(winner_source, 1, window=window)
                quality_ds.write(quality, 1, window=window)
                conflict_ds.write(conflict, 1, window=window)
                conflict_pixels += int(np.count_nonzero(conflict))
        return conflict_pixels

    def _read_translated_window(
        self,
        source: RasterRefinementSource,
        grid: TargetGridSpec,
        transform: Affine,
        window: Window,
    ) -> tuple[np.ndarray, np.ndarray]:
        with rasterio.open(source.path) as dataset:
            if source.band > dataset.count:
                raise RefinementValidationError(
                    f"Band {source.band} does not exist in {source.path}"
                )
            with WarpedVRT(
                dataset,
                crs=grid.crs,
                transform=transform,
                width=grid.width,
                height=grid.height,
                resampling=Resampling.nearest,
                src_nodata=dataset.nodata,
                nodata=dataset.nodata,
            ) as aligned:
                values = aligned.read(source.band, window=window, masked=True)
        raw = np.asarray(values.data)
        source_valid = ~np.ma.getmaskarray(values)
        translated = np.zeros(raw.shape, dtype=np.uint16)
        candidate_quality = np.zeros(raw.shape, dtype=np.uint8)
        for source_value, category_key in source.translations.items():
            selected = source_valid & (raw == source_value)
            code = self._category_codes[category_key]
            translated[selected] = code
            candidate_quality[selected] = self._quality_score(source, category_key)
        return translated, candidate_quality

    def _quality_score(self, source: RasterRefinementSource, category_key: str) -> int:
        priority_base = 240 - int(source.priority) * 40
        semantic = min(31, self._semantic_depth[category_key])
        confidence_penalty = round((100 - source.confidence) * 0.2)
        return max(1, min(255, priority_base + semantic - confidence_penalty))

    @staticmethod
    def _build_overviews(paths: dict[str, Path]) -> None:
        for key, path in paths.items():
            with rasterio.open(path, "r+") as dataset:
                factors = [factor for factor in (2, 4, 8, 16) if min(dataset.width, dataset.height) // factor >= 1]
                if factors:
                    resampling = Resampling.nearest
                    dataset.build_overviews(factors, resampling)
                    dataset.update_tags(ns="rio_overview", resampling="nearest")

    @staticmethod
    def _verified_geometry(mosaic_path: Path, crs: str) -> GeometryRecord:
        with rasterio.open(mosaic_path) as dataset:
            valid = dataset.read(1) != 0
            polygons = [
                shape(geometry)
                for geometry, value in shapes(
                    valid.astype(np.uint8),
                    mask=valid,
                    transform=dataset.transform,
                )
                if value == 1
            ]
        geometry = unary_union(polygons)
        if geometry.is_empty:
            raise RefinementValidationError("Derived mosaic contains no verified valid pixels")
        return GeometryRecord(crs, dict(mapping(geometry)))

    def _build_manifest(
        self,
        grid: TargetGridSpec,
        sources: tuple[RasterRefinementSource, ...],
        source_codes: dict[str, int],
        previous: dict[str, Any],
        windows: tuple[Window, ...],
        conflict_pixels: int,
    ) -> dict[str, Any]:
        previous_sources = {
            str(item["sourceId"]): item
            for item in previous.get("sources", [])
            if isinstance(item, dict) and item.get("sourceId")
        }
        for source in sources:
            previous_sources[source.source_id] = {
                "sourceId": source.source_id,
                "sourceCode": source_codes[source.source_id],
                "product": source.product,
                "version": source.version,
                "asset": str(source.path),
                "assetChecksum": source.asset_checksum,
                "licenseId": source.license.license_id,
                "licenseUrl": source.license.official_url,
                "attribution": source.license.attribution_text,
                "originalCrs": _source_crs(source.path),
                "band": source.band,
                "resampling": "nearest",
                "priority": source.priority.name,
                "translations": {
                    str(value): category
                    for value, category in source.translations.items()
                },
            }
        return {
            "schemaVersion": 1,
            "taxonomy": {
                "key": self._taxonomy.taxonomy_key,
                "version": self._taxonomy.taxonomy_version,
                "categoryCodes": self._category_codes,
            },
            "targetGrid": _grid_json(grid),
            "outputs": dict(self._OUTPUT_NAMES),
            "sources": [previous_sources[key] for key in sorted(previous_sources)],
            "updatedWindows": [_window_tuple(window) for window in windows],
            "conflictPixelsInUpdatedWindows": conflict_pixels,
            "conflictPolicy": [
                "LOCAL_OFFICIAL",
                "THEMATIC_REFINEMENT",
                "EUROPEAN_HIGH_RESOLUTION",
                "GENERAL_LAND_COVER",
                "NODATA",
            ],
        }


def _grid_transform(grid: TargetGridSpec) -> Affine:
    return Affine(grid.resolution_x, 0, grid.min_x, 0, -grid.resolution_y, grid.max_y)


def _bounds_intersect(
    first: tuple[float, float, float, float],
    second: tuple[float, float, float, float],
) -> bool:
    return not (
        first[2] <= second[0]
        or first[0] >= second[2]
        or first[3] <= second[1]
        or first[1] >= second[3]
    )


def _window_tuple(window: Window) -> tuple[int, int, int, int]:
    return (
        int(window.col_off),
        int(window.row_off),
        int(window.width),
        int(window.height),
    )


def _read_manifest(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {}


def _source_code_registry(
    previous: dict[str, Any],
    sources: Iterable[RasterRefinementSource],
) -> dict[str, int]:
    result = {
        str(item["sourceId"]): int(item["sourceCode"])
        for item in previous.get("sources", [])
        if isinstance(item, dict) and item.get("sourceId") and item.get("sourceCode")
    }
    next_code = max(result.values(), default=0) + 1
    for source in sorted(sources, key=lambda item: item.source_id):
        if source.source_id not in result:
            result[source.source_id] = next_code
            next_code += 1
    return result


def _grid_json(grid: TargetGridSpec) -> dict[str, object]:
    return {
        "crs": grid.crs,
        "resolution": [grid.resolution_x, grid.resolution_y],
        "origin": [grid.origin_x, grid.origin_y],
        "extent": [grid.min_x, grid.min_y, grid.max_x, grid.max_y],
        "width": grid.width,
        "height": grid.height,
        "dtype": grid.dtype,
        "nodata": grid.nodata,
        "resampling": grid.resampling.value,
        "tlstVersion": grid.tlst_version,
        "temporalPolicy": {
            "strategy": grid.temporal_policy.strategy,
            "windowDays": grid.temporal_policy.window_days,
        },
    }


def _source_crs(path: Path) -> str:
    with rasterio.open(path) as dataset:
        return dataset.crs.to_string() if dataset.crs else "unknown"


def _write_json_atomic(path: Path, payload: dict[str, Any]) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(path)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
