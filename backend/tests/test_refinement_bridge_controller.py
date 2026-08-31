from __future__ import annotations

import asyncio
import hashlib
from datetime import date
from pathlib import Path
from typing import Any

from terralab3d.application.refinement.bridge_controller import (
    RefinementBridgeController,
)
from terralab3d.application.refinement.discovery import RefinementDiscoveryCoordinator
from terralab3d.application.refinement.service import RefinementService
from terralab3d.domain.refinement.discovery import (
    DiscoveredRefinementProduct,
    RemoteAsset,
)
from terralab3d.domain.refinement.licensing import CommercialLicensePolicy, LicenseMetadata
from terralab3d.domain.refinement.installations import TechnicalResourceState
from terralab3d.infrastructure.adapters.refinement.catalog import (
    StaticRefinementProductCatalog,
)
from terralab3d.infrastructure.adapters.refinement.geometry import ShapelyGeometryAdapter
from terralab3d.infrastructure.adapters.refinement.providers.clms import (
    clms_refinement_products,
)
from terralab3d.infrastructure.adapters.refinement.repository import (
    JsonRefinementInstallationRepository,
)
from terralab3d.infrastructure.adapters.surface.tlst_catalog import (
    load_builtin_land_cover_registry,
)


_AOI = {
    "type": "Polygon",
    "coordinates": (((2.0, 41.0), (2.2, 41.0), (2.2, 41.2), (2.0, 41.2), (2.0, 41.0)),),
}


class _Publisher:
    def __init__(self) -> None:
        self.messages: list[dict[str, Any]] = []

    async def send(self, msg: dict[str, Any]) -> None:
        self.messages.append(msg)


class _Provider:
    provider_id = "fixture"

    def __init__(self, *candidates: DiscoveredRefinementProduct) -> None:
        self.candidates = candidates

    async def discover(self, request):
        return self.candidates


class _Catalog:
    def __init__(self) -> None:
        self.descriptors = []

    def upsert(self, descriptor) -> None:
        self.descriptors.append(descriptor)


class _Jobs:
    def __init__(self, publisher: _Publisher | None = None) -> None:
        self.publisher = publisher
        self.started = []
        self.deleted = []
        self.processors = []
        self.cancelled = []
        self.queued_before_start = False

    def start_download(self, resource_id, variant_id) -> str:
        self.queued_before_start = self.publisher is not None and any(
            message.get("type") == "refinement_download_progress"
            and message.get("state") == TechnicalResourceState.QUEUED.value
            for message in self.publisher.messages
        )
        self.started.append((resource_id, variant_id))
        return f"{resource_id}_{variant_id}"

    def delete_resource(self, resource_id, variant_id) -> None:
        self.deleted.append((resource_id, variant_id))

    def cancel_download(self, resource_id, variant_id) -> None:
        self.cancelled.append((resource_id, variant_id))

    def register_post_processor(self, resource_id, processor) -> None:
        self.processors.append((resource_id, processor))


def _candidate(suffix: str = "") -> DiscoveredRefinementProduct:
    payload = b"fixture"
    license_metadata = LicenseMetadata(
        license_id="CC-BY-4.0",
        official_url="https://creativecommons.org/licenses/by/4.0/",
        attribution_text="Fixture attribution",
        citation="Fixture citation",
        provider="Fixture provider",
        product="Fixture crops",
        version="1",
        checked_at=date(2026, 8, 25),
        provenance_url="https://example.test/product",
        asset_fingerprints=("fixture-asset",),
        commercial_use=True,
    )
    asset = RemoteAsset(
        asset_id=f"fixture-asset{suffix}",
        download_url=f"https://example.test/fixture{suffix}.tif",
        s3_path=f"/eodata/fixture{suffix}.tif",
        footprint=_AOI,
        order=0,
        estimated_bytes=len(payload),
        checksum_algorithm="sha256",
        checksum_value=hashlib.sha256(payload).hexdigest(),
        requires_authentication=False,
    )
    return DiscoveredRefinementProduct(
        candidate_id=f"fixture-candidate{suffix}",
        provider_id="fixture",
        provider="Fixture provider",
        product="Fixture crops",
        version="1",
        dataset_identifier="fixture-crops-v1",
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
    )


def test_exhaustive_mosaic_recommendation_has_a_bounded_catalogue_size() -> None:
    limit = RefinementBridgeController._MAX_EXHAUSTIVE_RECOMMENDATION_CANDIDATES

    assert RefinementBridgeController._should_calculate_exhaustive_recommendation(limit)
    assert not RefinementBridgeController._should_calculate_exhaustive_recommendation(limit + 1)


async def _wait_for(publisher: _Publisher, message_type: str) -> dict[str, Any]:
    for _ in range(100):
        match = next(
            (item for item in publisher.messages if item.get("type") == message_type),
            None,
        )
        if match is not None:
            return match
        await asyncio.sleep(0.01)
    raise AssertionError(f"Message {message_type!r} was not published")


def test_bridge_flow_workspace_discovery_plan_confirmation_and_removal(
    tmp_path: Path,
) -> None:
    async def scenario() -> None:
        registry = load_builtin_land_cover_registry()
        repository = JsonRefinementInstallationRepository(tmp_path / "refinements.json")
        policy = CommercialLicensePolicy()
        service = RefinementService(
            registry.taxonomy,
            repository,
            StaticRefinementProductCatalog(clms_refinement_products()),
            policy,
            tmp_path,
            labels={
                key: registry.category_presentation(key).label
                for key in registry.taxonomy.category_keys
            },
        )
        publisher = _Publisher()
        catalog = _Catalog()
        jobs = _Jobs(publisher)
        controller = RefinementBridgeController(
            publisher=publisher,
            discovery=RefinementDiscoveryCoordinator(
                (_Provider(_candidate(), _candidate("-tile-2")),),
                policy,
            ),
            service=service,
            geometry=ShapelyGeometryAdapter(),
            license_policy=policy,
            resource_catalog=catalog,
            download_jobs=jobs,
            data_root=tmp_path,
        )

        controller.request_workspace(
            {"requestId": "workspace", "revision": 1, "aoi": _AOI}
        )
        workspace = await _wait_for(publisher, "refinement_workspace_snapshot")
        nodes = workspace["workspace"]["nodes"]
        assert len(nodes) == 114
        agriculture = next(
            item for item in nodes if item["categoryKey"] == "agriculture.cropland"
        )
        assert agriculture["state"] == "absent"

        controller.query_products(
            {
                "requestId": "query-1",
                "revision": 3,
                "categoryKey": "agriculture.cropland",
                "aoi": _AOI,
            }
        )
        candidates = await _wait_for(publisher, "refinement_candidates")
        assert candidates["candidates"][0]["candidateId"] == "fixture-candidate"
        assert candidates["candidates"][0]["newEffectivePercent"] == 100.0

        controller.calculate_plan(
            {
                "requestId": "query-1",
                "revision": 3,
                "categoryKey": "agriculture.cropland",
                "aoi": _AOI,
                "productIds": ["fixture-candidate", "fixture-candidate-tile-2"],
            }
        )
        summary = await _wait_for(publisher, "refinement_plan_summary")
        plan = summary["plan"]
        assert summary["coverage"]["plannedPercent"] == 100.0
        assert plan["assets"][0]["fileName"] == "fixture.tif"

        controller.confirm_download(
            {
                "requestId": "query-1",
                "revision": 3,
                "planId": plan["planId"],
                "largeDownloadConfirmed": False,
            }
        )
        progress = await _wait_for(publisher, "refinement_download_progress")
        assert progress["state"] == TechnicalResourceState.QUEUED.value
        preparation = next(
            message
            for message in publisher.messages
            if message.get("type") == "refinement_operation_progress"
            and message.get("operation") == "confirm"
        )
        assert "2 fitxers" in preparation["message"]
        assert len(catalog.descriptors) == 1
        assert len(jobs.started) == 1
        assert jobs.queued_before_start
        installations = repository.list_installations()
        assert len(installations) == 1
        installation = installations[0]
        assert installation.job_id == progress["jobId"]

        # The controller may have restarted while the resource job is still
        # active; cancellation must recover from persisted resource identity.
        controller._active_downloads.clear()
        controller.cancel_download(
            {
                "requestId": "query-1",
                "revision": 3,
                "planId": plan["planId"],
            }
        )
        for _ in range(100):
            if jobs.cancelled:
                break
            await asyncio.sleep(0.01)
        assert len(jobs.cancelled) == 1
        cancelled = repository.get(installation.installation_id)
        assert cancelled is not None
        assert cancelled.technical_state is TechnicalResourceState.CANCELLED

        controller.remove_installation(
            {
                "requestId": "remove-1",
                "revision": 4,
                "installationId": installation.installation_id,
            }
        )
        await _wait_for(publisher, "refinement_installation_removed")
        assert repository.list_installations() == ()
        assert len(jobs.deleted) == 1

    asyncio.run(scenario())
