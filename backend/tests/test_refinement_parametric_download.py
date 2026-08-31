from __future__ import annotations

import asyncio
import hashlib
import zipfile
from dataclasses import replace
from datetime import date
from pathlib import Path

import pytest
import aiohttp
from aiohttp import web

from terralab3d.application.refinement.downloads import (
    freeze_parametric_plan,
    refinement_resource_id,
    resource_descriptor_from_plan,
)
from terralab3d.domain.refinement.discovery import (
    DiscoveredRefinementProduct,
    DiscoveryRequest,
    RemoteAsset,
)
from terralab3d.domain.refinement.downloads import ParametricDownloadPlan
from terralab3d.domain.identifiers import ResourceId, VariantId
from terralab3d.domain.refinement.licensing import (
    CommercialLicensePolicy,
    LicenseMetadata,
)
from terralab3d.domain.resources.models import ResourceInstallState
from terralab3d.infrastructure.resources.acquirers import (
    ParametricRasterAcquirer,
    ResourceVerificationError,
    safe_extract_zip,
)
from terralab3d.infrastructure.resources.installation_repository import (
    ResourceInstallationRepository,
)


_AOI = {
    "type": "Polygon",
    "coordinates": (((2.0, 41.0), (2.1, 41.0), (2.1, 41.1), (2.0, 41.1), (2.0, 41.0)),),
}


class _Manager:
    def __init__(self) -> None:
        self.snapshots = []
        self.failures: list[tuple[str, str]] = []

    async def _send_snapshot(self, snapshot, force: bool = False) -> None:
        del force
        self.snapshots.append(snapshot)

    async def _fail_job(
        self,
        job_id,
        resource_id,
        variant_id,
        code: str,
        message: str,
    ) -> None:
        del job_id, resource_id, variant_id
        self.failures.append((code, message))


class _AuthCoordinator:
    def __init__(self) -> None:
        self.calls = 0

    async def get_valid_token(self, interactive: bool = True) -> str:
        assert interactive is True
        self.calls += 1
        return "fixture-token"


def _request() -> DiscoveryRequest:
    return DiscoveryRequest("request-1", 2, "agriculture.cropland", _AOI)


def _candidate(url: str, payload: bytes, *, authenticated: bool = False):
    license_metadata = LicenseMetadata(
        license_id="CC-BY-4.0",
        official_url="https://creativecommons.org/licenses/by/4.0/",
        attribution_text="Fixture attribution",
        citation="Fixture citation",
        provider="Fixture provider",
        product="Fixture crop type",
        version="1",
        checked_at=date(2026, 8, 25),
        provenance_url="https://example.test/provenance",
        asset_fingerprints=("fixture-asset",),
        commercial_use=True,
    )
    asset = RemoteAsset(
        asset_id="fixture-asset",
        download_url=url,
        s3_path="/eodata/fixture.tif",
        footprint=_AOI,
        order=0,
        estimated_bytes=len(payload),
        checksum_algorithm="sha256",
        checksum_value=hashlib.sha256(payload).hexdigest(),
        requires_authentication=authenticated,
    )
    return DiscoveredRefinementProduct(
        candidate_id="fixture-product",
        provider_id="fixture",
        provider="Fixture provider",
        product="Fixture crop type",
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


async def _serve(payload: bytes) -> tuple[web.AppRunner, str]:
    async def handler(request: web.Request) -> web.Response:
        return web.Response(body=payload, content_type="image/tiff")

    app = web.Application()
    app.router.add_get("/fixture.tif", handler)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "127.0.0.1", 0)
    await site.start()
    port = site._server.sockets[0].getsockname()[1]
    return runner, f"http://127.0.0.1:{port}/fixture.tif"


def test_freezes_roundtrips_and_describes_exact_plan() -> None:
    payload = b"small-geotiff-fixture"
    candidate = _candidate("https://download.test/Products(id)/$value", payload)
    plan = freeze_parametric_plan(
        _request(),
        (candidate,),
        (candidate.candidate_id,),
        CommercialLicensePolicy(),
        plan_id="Crop plan 1",
    )

    restored = ParametricDownloadPlan.from_json(plan.to_json())
    descriptor = resource_descriptor_from_plan(restored)

    assert restored == plan
    assert restored.assets[0].file_name == "fixture.tif"
    assert restored.estimated_bytes == len(payload)
    assert descriptor.acquisition_kind.value == "PARAMETRIC_DOWNLOAD"
    assert descriptor.id == refinement_resource_id(plan.plan_id)
    assert descriptor.variants[0].source_urls == (candidate.assets[0].download_url,)


def test_parametric_acquirer_downloads_verifies_and_persists_fixture(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def scenario() -> None:
        payload = b"small-geotiff-fixture"
        runner, url = await _serve(payload)
        try:
            candidate = _candidate(url, payload)
            plan = freeze_parametric_plan(
                _request(),
                (candidate,),
                (candidate.candidate_id,),
                CommercialLicensePolicy(),
                plan_id="fixture-plan",
            )
            descriptor = resource_descriptor_from_plan(plan)
            variant = descriptor.variants[0]
            manager = _Manager()
            repository = ResourceInstallationRepository(tmp_path / "installations.json")
            acquirer = ParametricRasterAcquirer(manager, repository, None, {})
            await acquirer.acquire("job-1", descriptor, variant, {"job-1"})
        finally:
            await runner.cleanup()

        state = repository.get_resource_state(descriptor.id, variant.id)
        assert state is not None
        assert state["status"] == ResourceInstallState.READY.value
        assert Path(state["resolvedPath"]).read_bytes() == payload
        assert state["manifestData"]["parametricPlan"]["requestId"] == "request-1"
        assert state["manifestData"]["downloadedFiles"][0]["license"] == "CC-BY-4.0"
        assert not manager.failures

    monkeypatch.setenv("TERRALAB_DATA_ROOT", str(tmp_path / "library"))
    asyncio.run(scenario())


def test_parametric_acquirer_starts_independent_assets_in_parallel(
    tmp_path: Path,
) -> None:
    async def scenario() -> None:
        payload = b"parallel"
        first = _candidate("https://download.test/first", payload)
        second_asset = replace(
            first.assets[0],
            asset_id="fixture-asset-second",
            download_url="https://download.test/second",
            s3_path="/eodata/second.tif",
        )
        second = replace(
            first,
            candidate_id="fixture-product-second",
            assets=(second_asset,),
        )
        plan = freeze_parametric_plan(
            _request(),
            (first, second),
            (first.candidate_id, second.candidate_id),
            CommercialLicensePolicy(),
            plan_id="parallel-plan",
        )
        manager = _Manager()
        acquirer = ParametricRasterAcquirer(manager, None, None, {})
        started: list[str] = []
        release = asyncio.Event()

        async def fake_download_asset(**kwargs) -> int:
            started.append(kwargs["file_name"])
            await release.wait()
            await kwargs["progress_reporter"](kwargs["file_name"], len(payload))
            return len(payload)

        acquirer._download_asset = fake_download_asset  # type: ignore[method-assign]
        async with aiohttp.ClientSession() as session:
            task = asyncio.create_task(
                acquirer._download_assets_in_parallel(
                    session=session,
                    job_id="parallel-job",
                    resource_id=ResourceId("earth.parallel"),
                    variant_id=VariantId("local"),
                    plan=plan,
                    final_paths=(tmp_path / "first.tif", tmp_path / "second.tif"),
                    token="",
                    temp_dir=tmp_path,
                    active_tasks={"parallel-job"},
                )
            )
            for _ in range(10):
                if len(started) == 2:
                    break
                await asyncio.sleep(0)
            assert len(started) == 2
            release.set()
            assert await task == len(payload) * 2

    asyncio.run(scenario())


def test_parametric_acquirer_requires_external_token_for_authenticated_asset() -> None:
    async def scenario() -> None:
        payload = b"fixture"
        candidate = _candidate("https://download.test/asset", payload, authenticated=True)
        plan = freeze_parametric_plan(
            _request(),
            (candidate,),
            (candidate.candidate_id,),
            CommercialLicensePolicy(),
            plan_id="auth-plan",
        )
        descriptor = resource_descriptor_from_plan(plan)
        manager = _Manager()
        acquirer = ParametricRasterAcquirer(manager, None, None, {})
        await acquirer.acquire(
            "job-auth", descriptor, descriptor.variants[0], {"job-auth"}
        )
        assert manager.failures[0][0] == "CONFIG_REQUIRED"

    asyncio.run(scenario())


def test_authenticated_download_reports_authentication_before_transfer(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def scenario() -> None:
        payload = b"authenticated-fixture"
        runner, url = await _serve(payload)
        try:
            candidate = _candidate(url, payload, authenticated=True)
            plan = freeze_parametric_plan(
                _request(),
                (candidate,),
                (candidate.candidate_id,),
                CommercialLicensePolicy(),
                plan_id="authenticated-plan",
            )
            descriptor = resource_descriptor_from_plan(plan)
            manager = _Manager()
            repository = ResourceInstallationRepository(tmp_path / "state.json")
            auth = _AuthCoordinator()
            acquirer = ParametricRasterAcquirer(
                manager,
                repository,
                None,
                {},
                auth,
            )
            await acquirer.acquire(
                "job-authenticated",
                descriptor,
                descriptor.variants[0],
                {"job-authenticated"},
            )
        finally:
            await runner.cleanup()

        states = [snapshot.state for snapshot in manager.snapshots]
        assert auth.calls == 1
        assert states[0] is ResourceInstallState.AUTHENTICATING
        assert ResourceInstallState.DOWNLOADING in states
        authenticating = manager.snapshots[0]
        assert authenticating.downloaded_bytes == 0
        assert authenticating.total_bytes == len(payload)
        assert authenticating.progress == 0.0
        assert states.index(ResourceInstallState.AUTHENTICATING) < states.index(
            ResourceInstallState.DOWNLOADING
        )

    monkeypatch.setenv("TERRALAB_DATA_ROOT", str(tmp_path / "library"))
    asyncio.run(scenario())


def test_parametric_acquirer_rejects_wrong_checksum(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def scenario() -> None:
        payload = b"fixture-with-checksum"
        runner, url = await _serve(payload)
        try:
            candidate = _candidate(url, payload)
            wrong_asset = replace(candidate.assets[0], checksum_value="0" * 64)
            candidate = replace(candidate, assets=(wrong_asset,))
            plan = freeze_parametric_plan(
                _request(),
                (candidate,),
                (candidate.candidate_id,),
                CommercialLicensePolicy(),
                plan_id="bad-checksum",
            )
            descriptor = resource_descriptor_from_plan(plan)
            manager = _Manager()
            repository = ResourceInstallationRepository(tmp_path / "state.json")
            acquirer = ParametricRasterAcquirer(manager, repository, None, {})
            await acquirer.acquire(
                "job-bad-checksum",
                descriptor,
                descriptor.variants[0],
                {"job-bad-checksum"},
            )
        finally:
            await runner.cleanup()
        assert manager.failures[0][0] == "VERIFY_ERROR"

    monkeypatch.setenv("TERRALAB_DATA_ROOT", str(tmp_path / "library"))
    asyncio.run(scenario())


def test_parametric_acquirer_cancellation_never_commits_ready_state(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def scenario() -> None:
        payload = b"partial-fixture"
        runner, url = await _serve(payload)
        try:
            candidate = _candidate(url, payload)
            plan = freeze_parametric_plan(
                _request(),
                (candidate,),
                (candidate.candidate_id,),
                CommercialLicensePolicy(),
                plan_id="cancelled-plan",
            )
            descriptor = resource_descriptor_from_plan(plan)
            manager = _Manager()
            repository = ResourceInstallationRepository(tmp_path / "state.json")
            acquirer = ParametricRasterAcquirer(manager, repository, None, {})
            await acquirer.acquire(
                "job-cancelled", descriptor, descriptor.variants[0], set()
            )
        finally:
            await runner.cleanup()
        partial = tmp_path / "library" / "state" / "downloads" / "fixture.tif.part"
        assert partial.exists()
        assert not any(
            snapshot.state is ResourceInstallState.READY for snapshot in manager.snapshots
        )

    monkeypatch.setenv("TERRALAB_DATA_ROOT", str(tmp_path / "library"))
    asyncio.run(scenario())


def test_safe_zip_extraction_rejects_path_traversal(tmp_path: Path) -> None:
    archive = tmp_path / "unsafe.zip"
    with zipfile.ZipFile(archive, "w") as bundle:
        bundle.writestr("../escape.tif", b"malicious")

    with pytest.raises(ResourceVerificationError, match="Unsafe ZIP member"):
        safe_extract_zip(archive, tmp_path / "extracted")
    assert not (tmp_path / "escape.tif").exists()
