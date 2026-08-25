from __future__ import annotations

import asyncio
import hashlib
import json
from dataclasses import replace
from datetime import date
from pathlib import Path

import numpy as np
import pytest
import rasterio
from aiohttp import web
from rasterio.transform import from_origin

from terralab3d.application.refinement.downloads import (
    freeze_parametric_plan,
    resource_descriptor_from_plan,
)
from terralab3d.application.refinement.service import RefinementService
from terralab3d.domain.refinement.discovery import (
    DiscoveredRefinementProduct,
    DiscoveryRequest,
    RemoteAsset,
)
from terralab3d.domain.refinement.downloads import ParametricDownloadPlan
from terralab3d.domain.refinement.installations import (
    GeometryRecord,
    RefinementDataKind,
    RefinementProduct,
    TechnicalResourceState,
)
from terralab3d.domain.refinement.licensing import CommercialLicensePolicy, LicenseMetadata
from terralab3d.domain.refinement.mosaic import SourcePriority
from terralab3d.domain.resources.models import ResourceInstallState
from terralab3d.infrastructure.adapters.refinement.catalog import (
    StaticRefinementProductCatalog,
)
from terralab3d.infrastructure.adapters.refinement.geometry import ShapelyGeometryAdapter
from terralab3d.infrastructure.adapters.refinement.post_processor import (
    RefinementPlanPostProcessorFactory,
    _source_priority,
)
from terralab3d.infrastructure.adapters.refinement.repository import (
    JsonRefinementInstallationRepository,
)
from terralab3d.infrastructure.adapters.surface.tlst_catalog import (
    load_builtin_land_cover_registry,
)
from terralab3d.infrastructure.resources.download_manager import DownloadJobManager
from terralab3d.infrastructure.resources.installation_repository import (
    ResourceInstallationRepository,
)
from terralab3d.infrastructure.resources.layer_database import LayerDatabase
from terralab3d.infrastructure.websocket_bridge import WebSocketBridge


_AOI = {
    "type": "Polygon",
    "coordinates": (((2.0, 41.0), (2.04, 41.0), (2.04, 41.04), (2.0, 41.04), (2.0, 41.0)),),
}


def _write_fixture(path: Path) -> bytes:
    with rasterio.open(
        path,
        "w",
        driver="GTiff",
        width=4,
        height=4,
        count=1,
        dtype="uint16",
        crs="EPSG:4326",
        transform=from_origin(2.0, 41.04, 0.01, 0.01),
        nodata=0,
    ) as dataset:
        dataset.write(np.full((4, 4), 1140, dtype=np.uint16), 1)
    return path.read_bytes()


async def _serve(payload: bytes) -> tuple[web.AppRunner, str]:
    async def handler(request: web.Request) -> web.Response:
        return web.Response(body=payload, content_type="image/tiff")

    app = web.Application()
    app.router.add_get("/crop-types.tif", handler)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "127.0.0.1", 0)
    await site.start()
    port = site._server.sockets[0].getsockname()[1]
    return runner, f"http://127.0.0.1:{port}/crop-types.tif"


async def _serve_vector(payload: bytes) -> tuple[web.AppRunner, str]:
    async def handler(request: web.Request) -> web.Response:
        return web.Response(body=payload, content_type="application/geo+json")

    app = web.Application()
    app.router.add_get("/corine.geojson", handler)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "127.0.0.1", 0)
    await site.start()
    port = site._server.sockets[0].getsockname()[1]
    return runner, f"http://127.0.0.1:{port}/corine.geojson"


def _candidate(url: str, payload: bytes) -> DiscoveredRefinementProduct:
    license_metadata = LicenseMetadata(
        license_id="copernicus-clms",
        official_url="https://land.copernicus.eu/en/faq/data-use-terms-and-conditions",
        attribution_text="Contains modified Copernicus Service information (2026)",
        citation="Copernicus Land Monitoring Service",
        provider="Copernicus Land Monitoring Service",
        product="High Resolution Layer Crop Types",
        version="v1",
        checked_at=date(2026, 8, 25),
        provenance_url="https://documentation.dataspace.copernicus.eu/Data/CopernicusServices/CLMS.html",
        asset_fingerprints=("fixture-crop-types",),
        commercial_use=True,
    )
    asset = RemoteAsset(
        asset_id="fixture-crop-types",
        download_url=url,
        s3_path="/eodata/crop-types.tif",
        footprint=_AOI,
        order=0,
        estimated_bytes=len(payload),
        checksum_algorithm="sha256",
        checksum_value=hashlib.sha256(payload).hexdigest(),
        requires_authentication=False,
    )
    return DiscoveredRefinementProduct(
        candidate_id="fixture-crop-types",
        provider_id="copernicus-clms",
        provider="Copernicus Land Monitoring Service",
        product="High Resolution Layer Crop Types",
        version="v1",
        dataset_identifier="fixture-crop-types",
        compatible_tlst_nodes=("agriculture.cropland",),
        footprint=_AOI,
        resolution_m=10,
        temporal_start="2024-01-01",
        temporal_end="2024-12-31",
        format="GeoTIFF",
        estimated_bytes=len(payload),
        license=license_metadata,
        assets=(asset,),
        endpoint_verified=True,
        class_translation={1140: "agriculture.cropland.arable.rice"},
        nodata_values=(0,),
    )


def test_provider_priority_distinguishes_local_thematic_european_and_global_sources() -> None:
    candidate = _candidate("https://example.test/crop.tif", b"fixture")
    assert _source_priority(candidate) is SourcePriority.THEMATIC_REFINEMENT
    assert _source_priority(
        replace(candidate, provider_id="icgc-mcsc")
    ) is SourcePriority.LOCAL_OFFICIAL
    assert _source_priority(
        replace(candidate, provider_id="copernicus-corine")
    ) is SourcePriority.EUROPEAN_HIGH_RESOLUTION
    assert _source_priority(
        replace(candidate, dataset_identifier="lcm_global_10m_yearly_v1")
    ) is SourcePriority.GENERAL_LAND_COVER


def test_download_job_harmonizes_fixture_and_commits_verified_coverage(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def scenario() -> None:
        payload = _write_fixture(tmp_path / "source.tif")
        runner, url = await _serve(payload)
        try:
            candidate = _candidate(url, payload)
            request = DiscoveryRequest("pipeline", 1, "agriculture.cropland", _AOI)
            policy = CommercialLicensePolicy()
            plan = freeze_parametric_plan(
                request,
                (candidate,),
                (candidate.candidate_id,),
                policy,
                plan_id="pipeline-fixture",
            )
            descriptor = resource_descriptor_from_plan(plan)
            variant = descriptor.variants[0]
            catalog = LayerDatabase(tmp_path / "layers.json")
            catalog.upsert(descriptor)
            resource_repository = ResourceInstallationRepository(
                tmp_path / "resource-state.json"
            )
            bridge = WebSocketBridge()
            manager = DownloadJobManager(catalog, resource_repository, bridge)

            registry = load_builtin_land_cover_registry()
            refinement_repository = JsonRefinementInstallationRepository(
                tmp_path / "refinements.json"
            )
            service = RefinementService(
                registry.taxonomy,
                refinement_repository,
                StaticRefinementProductCatalog(),
                policy,
                tmp_path,
            )
            expected_job_id = f"{descriptor.id}_{variant.id}"
            installation = service.confirm_product(
                product=RefinementProduct(
                    product_id=candidate.candidate_id,
                    resource_id=str(descriptor.id),
                    variant_id=str(variant.id),
                    provider=candidate.provider,
                    product=candidate.product,
                    version=candidate.version,
                    tlst_nodes=candidate.compatible_tlst_nodes,
                    data_kind=RefinementDataKind.RASTER,
                    original_crs="EPSG:4326",
                    planned_geometry=GeometryRecord("EPSG:4326", _AOI),
                    license=candidate.license,
                    provenance_url=candidate.license.provenance_url,
                ),
                category_key="agriculture.cropland",
                aoi_id="pipeline-fixture",
                job_id=expected_job_id,
            )
            processor = RefinementPlanPostProcessorFactory(
                taxonomy=registry.taxonomy,
                service=service,
                geometry=ShapelyGeometryAdapter(),
                data_root=tmp_path / "library",
            ).build(plan, (candidate,), (installation.installation_id,))
            manager.register_post_processor(descriptor.id, processor)

            job_id = manager.start_download(descriptor.id, variant.id)
            await manager._active_tasks[job_id]
        finally:
            await runner.cleanup()

        resource_state = resource_repository.get_resource_state(
            descriptor.id, variant.id
        )
        verified = refinement_repository.get(installation.installation_id)
        assert resource_state is not None
        assert resource_state["status"] == ResourceInstallState.READY.value
        assert verified is not None
        assert verified.technical_state is TechnicalResourceState.READY
        assert verified.verified_geometry is not None
        manifest = Path(resource_state["manifestData"]["refinementManifest"])
        assert manifest.exists()
        assert Path(resource_state["manifestData"]["refinementMosaic"]).exists()
        assert Path(resource_state["manifestData"]["refinementSource"]).exists()
        assert Path(resource_state["manifestData"]["refinementQuality"]).exists()

    monkeypatch.setenv("TERRALAB_DATA_ROOT", str(tmp_path / "library"))
    asyncio.run(scenario())


def test_download_job_rasterizes_vector_fixture_and_commits_vector_coverage(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def scenario() -> None:
        payload = json.dumps(
            {
                "type": "FeatureCollection",
                "features": [
                    {
                        "type": "Feature",
                        "properties": {"Code_18": "211"},
                        "geometry": _AOI,
                    }
                ],
            }
        ).encode()
        runner, url = await _serve_vector(payload)
        try:
            license_metadata = LicenseMetadata(
                license_id="copernicus-clms",
                official_url="https://land.copernicus.eu/en/faq/data-use-terms-and-conditions",
                attribution_text="Contains modified Copernicus Service information (2026)",
                citation="CORINE Land Cover 2018",
                provider="Copernicus Land Monitoring Service",
                product="CORINE Land Cover 2018",
                version="v2020_20u1",
                checked_at=date(2026, 8, 25),
                provenance_url="https://land.copernicus.eu/en/products/corine-land-cover/clc2018",
                asset_fingerprints=("fixture-corine",),
                commercial_use=True,
            )
            asset = RemoteAsset(
                asset_id="fixture-corine",
                download_url=url,
                s3_path=None,
                footprint=_AOI,
                order=0,
                estimated_bytes=len(payload),
                checksum_algorithm="sha256",
                checksum_value=hashlib.sha256(payload).hexdigest(),
                requires_authentication=False,
                class_attribute="Code_18",
            )
            candidate = DiscoveredRefinementProduct(
                candidate_id="fixture-corine",
                provider_id="copernicus-corine",
                provider="Copernicus Land Monitoring Service",
                product="CORINE Land Cover 2018",
                version="v2020_20u1",
                dataset_identifier="corine-land-cover-2018",
                compatible_tlst_nodes=("agriculture.cropland.arable",),
                footprint=_AOI,
                resolution_m=100,
                temporal_start="2018-01-01",
                temporal_end="2018-12-31",
                format="GeoJSON",
                estimated_bytes=len(payload),
                license=license_metadata,
                assets=(asset,),
                endpoint_verified=True,
                class_translation={211: "agriculture.cropland.arable.unspecified"},
            )
            request = DiscoveryRequest(
                "vector-pipeline", 1, "agriculture.cropland.arable", _AOI
            )
            policy = CommercialLicensePolicy()
            plan = freeze_parametric_plan(
                request,
                (candidate,),
                (candidate.candidate_id,),
                policy,
                plan_id="vector-pipeline-fixture",
            )
            assert plan.assets[0].class_attribute == "Code_18"
            assert ParametricDownloadPlan.from_json(plan.to_json()) == plan
            descriptor = resource_descriptor_from_plan(plan)
            variant = descriptor.variants[0]
            catalog = LayerDatabase(tmp_path / "vector-layers.json")
            catalog.upsert(descriptor)
            resource_repository = ResourceInstallationRepository(
                tmp_path / "vector-resource-state.json"
            )
            manager = DownloadJobManager(
                catalog,
                resource_repository,
                WebSocketBridge(),
            )
            registry = load_builtin_land_cover_registry()
            refinement_repository = JsonRefinementInstallationRepository(
                tmp_path / "vector-refinements.json"
            )
            service = RefinementService(
                registry.taxonomy,
                refinement_repository,
                StaticRefinementProductCatalog(),
                policy,
                tmp_path,
            )
            expected_job_id = f"{descriptor.id}_{variant.id}"
            installation = service.confirm_product(
                product=RefinementProduct(
                    product_id=candidate.candidate_id,
                    resource_id=str(descriptor.id),
                    variant_id=str(variant.id),
                    provider=candidate.provider,
                    product=candidate.product,
                    version=candidate.version,
                    tlst_nodes=candidate.compatible_tlst_nodes,
                    data_kind=RefinementDataKind.VECTOR,
                    original_crs="EPSG:4326",
                    planned_geometry=GeometryRecord("EPSG:4326", _AOI),
                    license=candidate.license,
                    provenance_url=candidate.license.provenance_url,
                ),
                category_key="agriculture.cropland.arable",
                aoi_id="vector-pipeline-fixture",
                job_id=expected_job_id,
            )
            processor = RefinementPlanPostProcessorFactory(
                taxonomy=registry.taxonomy,
                service=service,
                geometry=ShapelyGeometryAdapter(),
                data_root=tmp_path / "vector-library",
            ).build(plan, (candidate,), (installation.installation_id,))
            manager.register_post_processor(descriptor.id, processor)
            job_id = manager.start_download(descriptor.id, variant.id)
            await manager._active_tasks[job_id]
        finally:
            await runner.cleanup()

        resource_state = resource_repository.get_resource_state(
            descriptor.id, variant.id
        )
        verified = refinement_repository.get(installation.installation_id)
        assert resource_state is not None
        assert resource_state["status"] == ResourceInstallState.READY.value
        assert verified is not None
        assert verified.verified_geometry is not None
        assert verified.verification_method.value == "vector_geometry"
        assert Path(resource_state["manifestData"]["refinementMosaic"]).exists()

    monkeypatch.setenv("TERRALAB_DATA_ROOT", str(tmp_path / "vector-library"))
    asyncio.run(scenario())
