"""Turn one frozen provider plan into persistent, verified TLST outputs."""

from __future__ import annotations

import json
import math
from pathlib import Path

import rasterio
from pyproj import Transformer
from rasterio.errors import RasterioError
from rasterio.features import rasterize
from rasterio.transform import Affine
from shapely.geometry import shape
from shapely.ops import transform

from terralab3d.application.ports.refinement import GeometryPort
from terralab3d.application.ports.resource_processing import ProcessedResource
from terralab3d.application.refinement.service import RefinementService
from terralab3d.domain.refinement.discovery import DiscoveredRefinementProduct
from terralab3d.domain.refinement.downloads import FrozenDownloadAsset, ParametricDownloadPlan
from terralab3d.domain.refinement.errors import RefinementValidationError
from terralab3d.domain.refinement.grid import (
    ResamplingPolicy,
    TargetGridSpec,
    TemporalPolicy,
)
from terralab3d.domain.refinement.installations import CoverageVerificationMethod
from terralab3d.domain.refinement.mosaic import RasterRefinementSource, SourcePriority
from terralab3d.domain.surface.tlst import TaxonomyCatalog
from terralab3d.infrastructure.adapters.refinement.mosaic import (
    RasterRefinementMosaicProcessor,
    sha256_file,
)


class RefinementPlanPostProcessorFactory:
    def __init__(
        self,
        *,
        taxonomy: TaxonomyCatalog,
        service: RefinementService,
        geometry: GeometryPort,
        data_root: Path,
    ) -> None:
        self._taxonomy = taxonomy
        self._service = service
        self._geometry = geometry
        self._data_root = data_root

    def build(
        self,
        plan: ParametricDownloadPlan,
        candidates: tuple[DiscoveredRefinementProduct, ...],
        installation_ids: tuple[str, ...],
    ) -> RefinementPlanPostProcessor:
        return RefinementPlanPostProcessor(
            taxonomy=self._taxonomy,
            service=self._service,
            geometry=self._geometry,
            data_root=self._data_root,
            plan=plan,
            candidates=candidates,
            installation_ids=installation_ids,
        )


class RefinementPlanPostProcessor:
    """Adapter used by DownloadJobManager after source verification."""

    def __init__(
        self,
        *,
        taxonomy: TaxonomyCatalog,
        service: RefinementService,
        geometry: GeometryPort,
        data_root: Path,
        plan: ParametricDownloadPlan,
        candidates: tuple[DiscoveredRefinementProduct, ...],
        installation_ids: tuple[str, ...],
    ) -> None:
        self._taxonomy = taxonomy
        self._service = service
        self._geometry = geometry
        self._data_root = data_root
        self._plan = plan
        self._candidates = candidates
        self._installation_ids = installation_ids

    def process(self, source_path: Path, output_dir: Path) -> ProcessedResource:
        del output_dir
        grid = self._target_grid()
        category_segment = self._plan.category_keys[0].replace(".", "-")
        derived_dir = (
            self._data_root
            / "cache"
            / "refinements"
            / self._taxonomy.taxonomy_version
            / category_segment
        )
        sources = self._raster_sources(source_path, grid, derived_dir)
        result = RasterRefinementMosaicProcessor(self._taxonomy).update(
            derived_dir,
            grid,
            sources,
        )
        aoi = self._geometry.from_geojson(
            self._plan.aoi_geojson,
            source_crs="EPSG:4326",
            target_crs=grid.crs,
        )
        verified = self._geometry.from_geojson(
            result.verified_geometry.geojson,
            source_crs=result.verified_geometry.crs,
            target_crs=grid.crs,
        )
        verified_inside = self._geometry.intersection(aoi, verified)
        verified_ratio = min(
            1.0,
            self._geometry.area(verified_inside) / self._geometry.area(aoi),
        )
        fingerprints = tuple(
            f"sha256:{source.asset_checksum}" for source in sources
        )
        for installation_id in self._installation_ids:
            self._service.register_verified_coverage(
                installation_id,
                verified_geometry=result.verified_geometry,
                verified_ratio=verified_ratio,
                file_fingerprints=fingerprints,
                method=(
                    CoverageVerificationMethod.VECTOR_GEOMETRY
                    if any(asset.class_attribute for asset in self._plan.assets)
                    else CoverageVerificationMethod.RASTER_VALID_MASK
                ),
            )
        qualifier_metadata = ",".join(
            f"{key}={path}" for key, path in sorted(result.qualifier_paths.items())
        )
        return ProcessedResource(
            render_path=result.mosaic_path,
            metadata={
                "refinementManifest": str(result.manifest_path),
                "refinementMosaic": str(result.mosaic_path),
                "refinementSource": str(result.source_path),
                "refinementQuality": str(result.quality_path),
                "refinementConflict": str(result.conflict_path),
                "refinementQualifiers": qualifier_metadata,
                "verifiedCoverageRatio": verified_ratio,
                "updatedWindowCount": len(result.updated_windows),
                "conflictPixels": result.conflict_pixels,
            },
        )

    def _raster_sources(
        self,
        source_path: Path,
        grid: TargetGridSpec,
        derived_dir: Path,
    ) -> tuple[RasterRefinementSource, ...]:
        candidate_by_asset = {
            asset.asset_id: candidate
            for candidate in self._candidates
            for asset in candidate.assets
        }
        sources: list[RasterRefinementSource] = []
        used_paths: set[Path] = set()
        for asset in self._plan.assets:
            candidate = candidate_by_asset.get(asset.asset_id)
            if candidate is None or not asset.class_translation:
                continue
            for index, path in enumerate(self._paths_for_asset(source_path, asset)):
                resolved = path.resolve(strict=False)
                if resolved in used_paths:
                    continue
                used_paths.add(resolved)
                source_checksum = sha256_file(path)
                raster_path = path
                if asset.class_attribute is not None:
                    raster_path = self._rasterize_vector_asset(
                        path,
                        asset,
                        grid,
                        derived_dir / "vector-cache",
                    )
                sources.append(
                    RasterRefinementSource(
                        source_id=f"{asset.asset_id}:{index}",
                        product=asset.product,
                        version=asset.version,
                        path=raster_path,
                        band=1,
                        translations=asset.class_translation,
                        priority=_source_priority(candidate.provider_id),
                        license=candidate.license,
                        asset_checksum=source_checksum,
                        qualifier_key=asset.qualifier_key,
                        invalid_values=asset.nodata_values,
                    )
                )
        if not sources:
            raise RefinementValidationError(
                "The frozen plan contains no readable categorical raster asset"
            )
        return tuple(sources)

    def _rasterize_vector_asset(
        self,
        path: Path,
        asset: FrozenDownloadAsset,
        grid: TargetGridSpec,
        cache_dir: Path,
    ) -> Path:
        try:
            document = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise RefinementValidationError(
                f"Vector asset {asset.asset_id} is not readable GeoJSON"
            ) from exc
        if not isinstance(document, dict) or document.get("type") != "FeatureCollection":
            raise RefinementValidationError(
                f"Vector asset {asset.asset_id} must be a GeoJSON FeatureCollection"
            )
        features = document.get("features")
        if not isinstance(features, list):
            raise RefinementValidationError(
                f"Vector asset {asset.asset_id} has no feature array"
            )
        source_crs = _geojson_crs(document)
        transformer = Transformer.from_crs(source_crs, grid.crs, always_xy=True)
        burn_shapes: list[tuple[object, int]] = []
        bounds: list[tuple[float, float, float, float]] = []
        for feature in features:
            if not isinstance(feature, dict):
                continue
            properties = feature.get("properties")
            geometry = feature.get("geometry")
            if not isinstance(properties, dict) or not isinstance(geometry, dict):
                continue
            raw_class = properties.get(asset.class_attribute or "")
            try:
                source_value = int(str(raw_class).strip())
            except (TypeError, ValueError):
                continue
            if source_value not in asset.class_translation:
                continue
            projected = transform(transformer.transform, shape(geometry))
            if projected.is_empty:
                continue
            burn_shapes.append((projected, source_value))
            bounds.append(projected.bounds)
        if not burn_shapes:
            raise RefinementValidationError(
                f"Vector asset {asset.asset_id} contains no mapped features"
            )
        min_x = max(grid.min_x, math.floor(min(item[0] for item in bounds) / grid.resolution_x) * grid.resolution_x)
        min_y = max(grid.min_y, math.floor(min(item[1] for item in bounds) / grid.resolution_y) * grid.resolution_y)
        max_x = min(grid.max_x, math.ceil(max(item[2] for item in bounds) / grid.resolution_x) * grid.resolution_x)
        max_y = min(grid.max_y, math.ceil(max(item[3] for item in bounds) / grid.resolution_y) * grid.resolution_y)
        width = max(1, round((max_x - min_x) / grid.resolution_x))
        height = max(1, round((max_y - min_y) / grid.resolution_y))
        target_transform = Affine(
            grid.resolution_x,
            0,
            min_x,
            0,
            -grid.resolution_y,
            max_y,
        )
        values = rasterize(
            burn_shapes,
            out_shape=(height, width),
            transform=target_transform,
            fill=0,
            dtype="uint16",
        )
        cache_dir.mkdir(parents=True, exist_ok=True)
        safe_asset_id = "".join(
            character if character.isalnum() or character in {"-", "_"} else "_"
            for character in asset.asset_id
        )
        destination = cache_dir / f"{safe_asset_id}.tif"
        with rasterio.open(
            destination,
            "w",
            driver="GTiff",
            width=width,
            height=height,
            count=1,
            dtype="uint16",
            crs=grid.crs,
            transform=target_transform,
            nodata=0,
            compress="deflate",
            tiled=width >= 16 and height >= 16,
        ) as dataset:
            dataset.write(values, 1)
        return destination

    def _paths_for_asset(
        self,
        source_path: Path,
        asset: FrozenDownloadAsset,
    ) -> tuple[Path, ...]:
        if source_path.is_file() and len(self._plan.assets) == 1:
            if _is_supported_source(source_path, asset):
                return (source_path,)
        root = source_path if source_path.is_dir() else source_path.parent
        direct = root / asset.file_name
        if direct.is_file() and _is_supported_source(direct, asset):
            return (direct,)
        extracted = root / Path(asset.file_name).stem
        if not extracted.is_dir():
            return ()
        readable = tuple(
            path
            for path in sorted(extracted.rglob("*"))
            if path.is_file()
            and _is_supported_source(path, asset)
            and _matches_product(path.name, asset.product)
        )
        return readable

    def _target_grid(self) -> TargetGridSpec:
        transformer = Transformer.from_crs("EPSG:4326", "EPSG:3035", always_xy=True)
        projected = transform(
            transformer.transform,
            shape(dict(self._plan.aoi_geojson)),
        )
        resolution = min(candidate.resolution_m for candidate in self._candidates)
        min_x = math.floor(projected.bounds[0] / resolution) * resolution
        min_y = math.floor(projected.bounds[1] / resolution) * resolution
        max_x = math.ceil(projected.bounds[2] / resolution) * resolution
        max_y = math.ceil(projected.bounds[3] / resolution) * resolution
        width = round((max_x - min_x) / resolution)
        height = round((max_y - min_y) / resolution)
        return TargetGridSpec(
            crs="EPSG:3035",
            resolution_x=resolution,
            resolution_y=resolution,
            origin_x=0,
            origin_y=0,
            min_x=min_x,
            min_y=min_y,
            max_x=max_x,
            max_y=max_y,
            width=width,
            height=height,
            dtype="uint16",
            nodata=0,
            resampling=ResamplingPolicy.NEAREST,
            tlst_version=self._taxonomy.taxonomy_version,
            temporal_policy=TemporalPolicy("latest_available"),
        )


def _is_readable_raster(path: Path) -> bool:
    try:
        with rasterio.open(path) as dataset:
            return dataset.count > 0 and dataset.crs is not None
    except (OSError, RasterioError):
        return False


def _is_supported_source(path: Path, asset: FrozenDownloadAsset) -> bool:
    if asset.class_attribute is not None:
        return path.suffix.lower() in {".geojson", ".json"}
    return _is_readable_raster(path)


def _geojson_crs(document: dict[str, object]) -> str:
    crs = document.get("crs")
    if isinstance(crs, dict):
        properties = crs.get("properties")
        if isinstance(properties, dict):
            name = properties.get("name")
            if isinstance(name, str) and name.strip():
                return name
    return "EPSG:4326"


def _matches_product(file_name: str, product: str) -> bool:
    lowered = file_name.lower()
    normalized_product = product.lower()
    if "crop type" in normalized_product:
        return "cty" in lowered or "crop" in lowered
    if "dominant leaf" in normalized_product:
        return "dlt" in lowered and "dltc" not in lowered
    if "forest type" in normalized_product:
        return "fty" in lowered or "forest" in lowered
    if "tree cover density" in normalized_product:
        return "tcd" in lowered or "density" in lowered
    if "water and wetness" in normalized_product:
        return "waw" in lowered or "water" in lowered or "wet" in lowered
    return True


def _source_priority(provider_id: str) -> SourcePriority:
    if provider_id.startswith("icgc-"):
        return SourcePriority.LOCAL_OFFICIAL
    if provider_id == "copernicus-clms":
        return SourcePriority.EUROPEAN_HIGH_RESOLUTION
    return SourcePriority.GENERAL_LAND_COVER
