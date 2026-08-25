"""Register a committed local categorical raster as verified TLST coverage."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import rasterio
from rasterio.features import shapes
from shapely.geometry import mapping, shape
from shapely.ops import unary_union

from terralab3d.application.ports.refinement import ManualRefinementImportRequest
from terralab3d.application.refinement.service import RefinementService
from terralab3d.domain.refinement.errors import RefinementValidationError
from terralab3d.domain.refinement.installations import (
    CoverageVerificationMethod,
    GeometryRecord,
    RefinementDataKind,
    RefinementInstallation,
    RefinementProduct,
)


class ManualRefinementImportRegistrar:
    def __init__(self, service: RefinementService) -> None:
        self._service = service

    def register(
        self,
        request: ManualRefinementImportRequest,
    ) -> tuple[RefinementInstallation, ...]:
        incompatible = tuple(
            category_key
            for category_key, _ in request.category_codes
            if category_key != request.category_key
            and not category_key.startswith(f"{request.category_key}.")
        )
        if incompatible:
            raise RefinementValidationError(
                "Manual refinement mappings must remain inside the selected TLST branch: "
                f"{', '.join(incompatible)}"
            )
        completed: list[RefinementInstallation] = []
        created_ids: list[str] = []
        try:
            for category_key, category_codes in request.category_codes:
                verified_geometry = verified_mask_geometry(
                    request.indexed_path,
                    valid_codes=category_codes,
                )
                safe_category = category_key.replace(".", "-")
                product = RefinementProduct(
                    product_id=f"manual-{request.source_id}-{safe_category}",
                    resource_id=request.resource_id,
                    variant_id=request.variant_id,
                    provider=request.license.provider,
                    product=request.name,
                    version=request.license.version,
                    tlst_nodes=(category_key,),
                    data_kind=RefinementDataKind.RASTER,
                    original_crs=request.original_crs,
                    planned_geometry=verified_geometry,
                    license=request.license,
                    provenance_url=request.license.provenance_url,
                    priority=0,
                )
                queued = self._service.confirm_product(
                    product=product,
                    category_key=request.category_key,
                    aoi_id=f"{request.fingerprint[:12]}-{safe_category}",
                    job_id=f"manual-import:{request.source_id}",
                    local_path=request.indexed_path,
                )
                created_ids.append(queued.installation_id)
                completed.append(
                    self._service.register_verified_coverage(
                        queued.installation_id,
                        verified_geometry=verified_geometry,
                        verified_ratio=1.0,
                        file_fingerprints=(f"blake2b-160:{request.fingerprint}",),
                        method=CoverageVerificationMethod.RASTER_VALID_MASK,
                    )
                )
        except Exception:
            for installation_id in created_ids:
                self._service.remove_installation(installation_id)
            raise
        return tuple(completed)


def verified_mask_geometry(
    path: Path,
    *,
    valid_codes: tuple[int, ...] | None = None,
) -> GeometryRecord:
    try:
        with rasterio.open(path) as dataset:
            if dataset.crs is None:
                raise RefinementValidationError(
                    "A manual refinement raster requires a declared CRS"
                )
            valid = dataset.dataset_mask() > 0
            if valid_codes is not None:
                valid &= np.isin(dataset.read(1), valid_codes)
            polygons = [
                shape(geometry)
                for geometry, value in shapes(
                    valid.astype(np.uint8),
                    mask=valid,
                    transform=dataset.transform,
                )
                if value == 1
            ]
            crs = dataset.crs.to_string()
    except (OSError, rasterio.errors.RasterioError) as exc:
        raise RefinementValidationError(
            "The committed manual refinement raster cannot be verified"
        ) from exc
    geometry = unary_union(polygons)
    if geometry.is_empty:
        raise RefinementValidationError(
            "The committed manual refinement contains no valid pixels"
        )
    return GeometryRecord(crs, dict(mapping(geometry)))
