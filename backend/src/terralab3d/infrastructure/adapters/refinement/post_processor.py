"""Turn one frozen provider plan into persistent, verified TLST outputs."""

from __future__ import annotations

import math
from pathlib import Path

import rasterio
from pyproj import Transformer
from rasterio.errors import RasterioError
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

    def process(self, source_path: Path, _output_dir: Path) -> ProcessedResource:
        sources = self._raster_sources(source_path)
        grid = self._target_grid()
        category_segment = self._plan.category_keys[0].replace(".", "-")
        derived_dir = (
            self._data_root
            / "cache"
            / "refinements"
            / self._taxonomy.taxonomy_version
            / category_segment
        )
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
                method=CoverageVerificationMethod.RASTER_VALID_MASK,
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
                sources.append(
                    RasterRefinementSource(
                        source_id=f"{asset.asset_id}:{index}",
                        product=asset.product,
                        version=asset.version,
                        path=path,
                        band=1,
                        translations=asset.class_translation,
                        priority=SourcePriority.EUROPEAN_HIGH_RESOLUTION,
                        license=candidate.license,
                        asset_checksum=sha256_file(path),
                        qualifier_key=asset.qualifier_key,
                        invalid_values=asset.nodata_values,
                    )
                )
        if not sources:
            raise RefinementValidationError(
                "The frozen plan contains no readable categorical raster asset"
            )
        return tuple(sources)

    def _paths_for_asset(
        self,
        source_path: Path,
        asset: FrozenDownloadAsset,
    ) -> tuple[Path, ...]:
        if source_path.is_file() and len(self._plan.assets) == 1:
            if _is_readable_raster(source_path):
                return (source_path,)
        root = source_path if source_path.is_dir() else source_path.parent
        direct = root / asset.file_name
        if direct.is_file() and _is_readable_raster(direct):
            return (direct,)
        extracted = root / Path(asset.file_name).stem
        if not extracted.is_dir():
            return ()
        readable = tuple(
            path
            for path in sorted(extracted.rglob("*"))
            if path.is_file()
            and _is_readable_raster(path)
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
