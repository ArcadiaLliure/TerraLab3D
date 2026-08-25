from __future__ import annotations

import json
from dataclasses import replace
from datetime import UTC, date, datetime

import pytest

from terralab3d.application.refinement.service import RefinementService
from terralab3d.domain.refinement.errors import (
    LicenseRejectedError,
    RefinementPersistenceError,
)
from terralab3d.domain.refinement.installations import (
    CoverageVerificationMethod,
    GeometryRecord,
    RefinementDataKind,
    RefinementProduct,
    TechnicalResourceState,
)
from terralab3d.domain.refinement.licensing import CommercialLicensePolicy, LicenseMetadata
from terralab3d.domain.refinement.states import SpatialCoverageState
from terralab3d.infrastructure.adapters.refinement.catalog import (
    StaticRefinementProductCatalog,
)
from terralab3d.infrastructure.adapters.refinement.repository import (
    JsonRefinementInstallationRepository,
)
from terralab3d.infrastructure.adapters.surface.tlst_catalog import (
    load_builtin_land_cover_registry,
)


NOW = datetime(2026, 8, 25, 12, tzinfo=UTC)


def _geometry() -> GeometryRecord:
    return GeometryRecord(
        "EPSG:25831",
        {
            "type": "Polygon",
            "coordinates": (((0, 0), (100, 0), (100, 100), (0, 100), (0, 0)),),
        },
    )


def _license(**overrides: object) -> LicenseMetadata:
    base = LicenseMetadata(
        license_id="CC-BY-4.0",
        official_url="https://creativecommons.org/licenses/by/4.0/",
        attribution_text="Fixture attribution",
        citation="Fixture citation",
        provider="Fixture provider",
        product="Fixture vineyard",
        version="1.0",
        checked_at=date(2026, 8, 25),
        provenance_url="https://example.test/product",
        asset_fingerprints=("sha256:catalog-asset",),
        commercial_use=True,
    )
    return replace(base, **overrides)


def _product(**overrides: object) -> RefinementProduct:
    base = RefinementProduct(
        product_id="fixture-vineyard",
        resource_id="earth.refinement.fixture.vineyard",
        variant_id="2026",
        provider="Fixture provider",
        product="Fixture vineyard",
        version="1.0",
        tlst_nodes=("agriculture.cropland.permanent_crop.vineyard",),
        data_kind=RefinementDataKind.RASTER,
        original_crs="EPSG:3035",
        planned_geometry=_geometry(),
        license=_license(),
        provenance_url="https://example.test/product",
    )
    return replace(base, **overrides)


def _service(
    tmp_path: object,
    products: tuple[RefinementProduct, ...],
) -> tuple[RefinementService, JsonRefinementInstallationRepository]:
    registry = load_builtin_land_cover_registry()
    repository = JsonRefinementInstallationRepository(tmp_path / "refinements.json")
    labels = {
        key: registry.category_presentation(key).label
        for key in registry.taxonomy.category_keys
    }
    service = RefinementService(
        registry.taxonomy,
        repository,
        StaticRefinementProductCatalog(products),
        CommercialLicensePolicy(),
        tmp_path,
        labels=labels,
        clock=lambda: NOW,
        id_factory=lambda: "installation-1",
    )
    return service, repository


def test_workspace_loads_all_103_categories_from_the_canonical_source(tmp_path) -> None:
    service, _ = _service(tmp_path, (_product(),))

    workspace = service.workspace()

    assert workspace.virtual_root == "surface"
    assert workspace.taxonomy_version == "1.0"
    assert len(workspace.nodes) == 103
    vineyard = next(
        node
        for node in workspace.nodes
        if node.category_key == "agriculture.cropland.permanent_crop.vineyard"
    )
    assert vineyard.label == "Vinya"
    assert vineyard.state is SpatialCoverageState.ABSENT


def test_catalog_gate_hides_blocked_products(tmp_path) -> None:
    blocked = _product(
        product_id="blocked-osm",
        license=_license(
            license_id="ODbL-1.0",
            odbl=True,
            upstream_sources=("OpenStreetMap",),
        ),
    )
    service, _ = _service(tmp_path, (_product(), blocked))

    visible = service.selectable_products("agriculture")

    assert tuple(product.product_id for product in visible) == ("fixture-vineyard",)
    with pytest.raises(LicenseRejectedError):
        service.confirm_operation(
            product_id="blocked-osm",
            category_key="agriculture",
            aoi_id="cat-test",
            job_id="job-blocked",
        )


def test_confirm_verify_and_cancel_are_persisted_with_separate_states(tmp_path) -> None:
    service, repository = _service(tmp_path, (_product(),))

    queued = service.confirm_operation(
        product_id="fixture-vineyard",
        category_key="agriculture",
        aoi_id="cat-test",
        job_id="job-1",
    )

    assert queued.technical_state is TechnicalResourceState.QUEUED
    assert queued.spatial_state is SpatialCoverageState.PARTIAL
    assert queued.verified_geometry is None
    assert queued.license.provenance_url == "https://example.test/product"
    assert "data\\earth\\refinement\\agriculture" in queued.local_path
    assert repository.get("installation-1") == queued

    verified = service.register_verified_coverage(
        "installation-1",
        verified_geometry=_geometry(),
        verified_ratio=0.995,
        file_fingerprints=("sha256:downloaded-file",),
        method=CoverageVerificationMethod.RASTER_VALID_MASK,
    )
    assert verified.technical_state is TechnicalResourceState.READY
    assert verified.spatial_state is SpatialCoverageState.COMPLETE
    assert verified.verification_method is CoverageVerificationMethod.RASTER_VALID_MASK

    cancelled = service.cancel_operation("installation-1")
    assert cancelled.technical_state is TechnicalResourceState.CANCELLED
    assert cancelled.spatial_state is SpatialCoverageState.ABSENT


def test_ready_installation_round_trip_preserves_full_provenance(tmp_path) -> None:
    service, repository = _service(tmp_path, (_product(),))
    service.confirm_operation(
        product_id="fixture-vineyard",
        category_key="agriculture",
        aoi_id="cat-test",
        job_id="job-1",
    )
    expected = service.register_verified_coverage(
        "installation-1",
        verified_geometry=_geometry(),
        verified_ratio=0.8,
        file_fingerprints=("sha256:downloaded-file",),
        method=CoverageVerificationMethod.RASTER_VALID_MASK,
    )

    reloaded = JsonRefinementInstallationRepository(repository.path).get("installation-1")

    assert reloaded == expected
    assert reloaded is not None
    assert reloaded.license.asset_fingerprints == ("sha256:catalog-asset",)
    assert reloaded.file_fingerprints == ("sha256:downloaded-file",)


def test_atomic_failure_keeps_previous_file_and_in_memory_state(tmp_path, monkeypatch) -> None:
    service, repository = _service(tmp_path, (_product(),))
    first = service.confirm_operation(
        product_id="fixture-vineyard",
        category_key="agriculture",
        aoi_id="cat-test",
        job_id="job-1",
    )
    previous_bytes = repository.path.read_bytes()
    second = replace(first, installation_id="installation-2", job_id="job-2")

    def fail_replace(source, destination) -> None:
        raise OSError("simulated interruption")

    monkeypatch.setattr(repository, "_replace_atomic", fail_replace)
    with pytest.raises(RefinementPersistenceError, match="Cannot persist"):
        repository.upsert(second)

    assert repository.path.read_bytes() == previous_bytes
    assert repository.get("installation-1") == first
    assert repository.get("installation-2") is None


def test_schema_zero_is_migrated_to_current_document(tmp_path) -> None:
    service, repository = _service(tmp_path, (_product(),))
    service.confirm_operation(
        product_id="fixture-vineyard",
        category_key="agriculture",
        aoi_id="cat-test",
        job_id="job-1",
    )
    current = json.loads(repository.path.read_text(encoding="utf-8"))
    repository.path.write_text(
        json.dumps({"schemaVersion": 0, "records": current["installations"]}),
        encoding="utf-8",
    )

    migrated = JsonRefinementInstallationRepository(repository.path)

    assert migrated.get("installation-1") is not None
    document = json.loads(repository.path.read_text(encoding="utf-8"))
    assert document["schemaVersion"] == 1
    assert "installations" in document


def test_workspace_propagates_verified_state_through_applicable_ancestors(tmp_path) -> None:
    service, _ = _service(tmp_path, (_product(),))
    service.confirm_operation(
        product_id="fixture-vineyard",
        category_key="agriculture",
        aoi_id="cat-test",
        job_id="job-1",
    )
    service.register_verified_coverage(
        "installation-1",
        verified_geometry=_geometry(),
        verified_ratio=1,
        file_fingerprints=("sha256:file",),
        method=CoverageVerificationMethod.RASTER_VALID_MASK,
    )

    states = {node.category_key: node.state for node in service.workspace().nodes}

    assert states["agriculture.cropland.permanent_crop.vineyard"] is SpatialCoverageState.COMPLETE
    assert states["agriculture.cropland.permanent_crop"] is SpatialCoverageState.COMPLETE
    assert states["agriculture.cropland"] is SpatialCoverageState.COMPLETE
    assert states["agriculture"] is SpatialCoverageState.COMPLETE
    assert states["water"] is SpatialCoverageState.NOT_APPLICABLE
