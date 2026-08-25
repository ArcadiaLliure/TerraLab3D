from __future__ import annotations

from datetime import date
from pathlib import Path

import numpy as np
import pytest
import rasterio
from rasterio.transform import from_origin
from shapely.geometry import shape

from terralab3d.application.ports.refinement import ManualRefinementImportRequest
from terralab3d.application.refinement.service import RefinementService
from terralab3d.domain.refinement.errors import LicenseRejectedError
from terralab3d.domain.refinement.installations import TechnicalResourceState
from terralab3d.domain.refinement.licensing import LicenseMetadata
from terralab3d.domain.refinement.states import SpatialCoverageState
from terralab3d.infrastructure.adapters.refinement.catalog import (
    StaticRefinementProductCatalog,
)
from terralab3d.infrastructure.adapters.refinement.manual_import import (
    ManualRefinementImportRegistrar,
    verified_mask_geometry,
)
from terralab3d.infrastructure.adapters.refinement.repository import (
    JsonRefinementInstallationRepository,
)
from terralab3d.infrastructure.adapters.surface.tlst_catalog import (
    load_builtin_land_cover_registry,
)
from terralab3d.domain.refinement.licensing import CommercialLicensePolicy


def _raster(path: Path) -> Path:
    with rasterio.open(
        path,
        "w",
        driver="GTiff",
        width=3,
        height=3,
        count=1,
        dtype="uint16",
        crs="EPSG:3035",
        transform=from_origin(4_000_000, 3_000_000, 10, 10),
    ) as dataset:
        dataset.write(np.ones((3, 3), dtype=np.uint16), 1)
        mask = np.full((3, 3), 255, dtype=np.uint8)
        mask[1, 1] = 0
        dataset.write_mask(mask)
    return path


def _license(*, license_id: str = "CC-BY-4.0") -> LicenseMetadata:
    return LicenseMetadata(
        license_id=license_id,
        official_url="https://creativecommons.org/licenses/by/4.0/",
        attribution_text="Institut de prova, cobertura 2026",
        citation="Institut de prova (2026)",
        provider="Institut de prova",
        product="Cobertura local",
        version="2026.1",
        checked_at=date(2026, 8, 25),
        provenance_url="https://example.test/coverage",
        asset_fingerprints=("blake2b-160:fixture",),
        commercial_use=True,
    )


def _request(path: Path, *, license_id: str = "CC-BY-4.0") -> ManualRefinementImportRequest:
    return ManualRefinementImportRequest(
        category_key="wetland",
        category_codes=(("wetland.inland.herbaceous_wetland", (1,)),),
        resource_id="earth.land_cover.imported.fixture",
        variant_id="local",
        source_id="land_cover.imported.fixture",
        name="Aiguamoll local",
        indexed_path=path,
        original_crs="EPSG:3035",
        fingerprint="fixture",
        license=_license(license_id=license_id),
    )


def test_verified_manual_geometry_uses_the_real_dataset_mask(tmp_path: Path) -> None:
    geometry = verified_mask_geometry(_raster(tmp_path / "masked.tif"))
    assert geometry.crs == "EPSG:3035"
    assert shape(dict(geometry.geojson)).area == 800


def test_manual_import_is_persisted_ready_with_provenance(tmp_path: Path) -> None:
    path = _raster(tmp_path / "manual.tif")
    repository = JsonRefinementInstallationRepository(tmp_path / "refinements.json")
    service = RefinementService(
        load_builtin_land_cover_registry().taxonomy,
        repository,
        StaticRefinementProductCatalog(),
        CommercialLicensePolicy(),
        tmp_path,
        id_factory=lambda: "manual-installation",
    )
    installation = ManualRefinementImportRegistrar(service).register(_request(path))[0]
    assert installation.technical_state is TechnicalResourceState.READY
    assert installation.spatial_state is SpatialCoverageState.COMPLETE
    assert installation.verification_method.value == "raster_valid_mask"
    assert installation.file_fingerprints == ("blake2b-160:fixture",)
    assert repository.get("manual-installation") == installation


def test_manual_import_license_gate_is_fail_closed(tmp_path: Path) -> None:
    path = _raster(tmp_path / "blocked.tif")
    repository = JsonRefinementInstallationRepository(tmp_path / "refinements.json")
    service = RefinementService(
        load_builtin_land_cover_registry().taxonomy,
        repository,
        StaticRefinementProductCatalog(),
        CommercialLicensePolicy(),
        tmp_path,
    )
    with pytest.raises(LicenseRejectedError):
        ManualRefinementImportRegistrar(service).register(
            _request(path, license_id="unknown")
        )
    assert not repository.list_installations()
