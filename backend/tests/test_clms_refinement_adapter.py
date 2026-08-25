from __future__ import annotations

import asyncio
import os
from datetime import date

import pytest
from aiohttp import web

from terralab3d.application.refinement.discovery import RefinementDiscoveryCoordinator
from terralab3d.domain.refinement.discovery import (
    DiscoveredRefinementProduct,
    DiscoveryRequest,
    RemoteAsset,
)
from terralab3d.domain.refinement.licensing import CommercialLicensePolicy, LicenseMetadata
from terralab3d.infrastructure.adapters.refinement.providers.clms import (
    ClmsDiscoveryError,
    ClmsODataAdapter,
    ClmsProviderConfiguration,
)


def _request(request_id: str = "request-1", revision: int = 1) -> DiscoveryRequest:
    return DiscoveryRequest(
        request_id=request_id,
        revision=revision,
        category_key="agriculture.cropland",
        aoi_geojson={
            "type": "Polygon",
            "coordinates": (((2.0, 41.0), (2.2, 41.0), (2.2, 41.2), (2.0, 41.2), (2.0, 41.0)),),
        },
    )


def _record(product_id: str) -> dict[str, object]:
    return {
        "Id": product_id,
        "Name": f"CLMS_{product_id}",
        "ContentType": "image/tiff",
        "ContentLength": 1234,
        "S3Path": f"/eodata/CLMS/{product_id}",
        "Checksum": [{"Algorithm": "MD5", "Value": f"md5-{product_id}"}],
        "ContentDate": {"Start": "2023-01-01T00:00:00Z", "End": "2023-12-31T23:59:59Z"},
        "GeoFootprint": {
            "type": "Polygon",
            "coordinates": (((2.0, 41.0), (2.1, 41.0), (2.1, 41.1), (2.0, 41.1), (2.0, 41.0)),),
        },
        "Attributes": [
            {"Name": "fileFormat", "Value": "cog"},
            {"Name": "productVersion", "Value": "V01_R00"},
        ],
    }


async def _serve(handler) -> tuple[web.AppRunner, str]:
    app = web.Application()
    app.router.add_get("/Products", handler)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "127.0.0.1", 0)
    await site.start()
    socket = site._server.sockets[0]
    port = socket.getsockname()[1]
    return runner, f"http://127.0.0.1:{port}/Products"


def test_clms_contract_handles_catalog_query_pagination_tiles_and_cache() -> None:
    async def scenario() -> None:
        calls: list[str] = []

        async def handler(request: web.Request) -> web.Response:
            calls.append(str(request.rel_url))
            if request.query.get("page") == "2":
                return web.json_response({"value": [_record("tile-2")]})
            assert "datasetIdentifier" in request.query["$filter"]
            assert "OData.CSC.Intersects" in request.query["$filter"]
            next_link = f"{request.scheme}://{request.host}/Products?page=2"
            return web.json_response(
                {"value": [_record("tile-1")], "@odata.nextLink": next_link}
            )

        runner, url = await _serve(handler)
        try:
            adapter = ClmsODataAdapter(
                ClmsProviderConfiguration(
                    catalogue_url=url,
                    download_url="https://download.example.test/odata/v1",
                    cache_ttl_seconds=60,
                )
            )
            first = await adapter.discover(_request())
            second = await adapter.discover(_request())
        finally:
            await runner.cleanup()

        assert len(first) == 2
        assert second == first
        assert len(calls) == 2
        assert first[0].format == "cog"
        assert first[0].estimated_bytes == 1234
        assert first[0].assets[0].checksum_algorithm == "md5"
        assert first[0].assets[0].requires_authentication
        assert first[0].assets[0].download_url.endswith("Products(tile-1)/$value")
        assert first[0].license.commercial_use is True

    asyncio.run(scenario())


def test_clms_contract_retries_transient_http_errors() -> None:
    async def scenario() -> None:
        calls = 0

        async def handler(request: web.Request) -> web.Response:
            nonlocal calls
            calls += 1
            if calls == 1:
                raise web.HTTPServiceUnavailable()
            return web.json_response({"value": [_record("recovered")]})

        runner, url = await _serve(handler)
        try:
            adapter = ClmsODataAdapter(
                ClmsProviderConfiguration(
                    catalogue_url=url,
                    retry_count=1,
                    retry_backoff_seconds=0,
                )
            )
            products = await adapter.discover(_request())
        finally:
            await runner.cleanup()
        assert calls == 2
        assert products[0].candidate_id == "recovered"

    asyncio.run(scenario())


def test_clms_contract_reports_timeout_after_bounded_retry() -> None:
    async def scenario() -> None:
        async def handler(request: web.Request) -> web.Response:
            await asyncio.sleep(0.05)
            return web.json_response({"value": []})

        runner, url = await _serve(handler)
        try:
            adapter = ClmsODataAdapter(
                ClmsProviderConfiguration(
                    catalogue_url=url,
                    timeout_seconds=0.01,
                    retry_count=0,
                )
            )
            with pytest.raises(ClmsDiscoveryError, match="after retries"):
                await adapter.discover(_request())
        finally:
            await runner.cleanup()

    asyncio.run(scenario())


def _candidate(candidate_id: str) -> DiscoveredRefinementProduct:
    footprint = {
        "type": "Polygon",
        "coordinates": (((2, 41), (2.1, 41), (2.1, 41.1), (2, 41.1), (2, 41)),),
    }
    license_metadata = LicenseMetadata(
        license_id="CC-BY-4.0",
        official_url="https://creativecommons.org/licenses/by/4.0/",
        attribution_text="Attribution",
        citation="Citation",
        provider="Provider",
        product="Product",
        version="1",
        checked_at=date(2026, 8, 25),
        provenance_url="https://example.test",
        asset_fingerprints=(candidate_id,),
        commercial_use=True,
    )
    asset = RemoteAsset(
        candidate_id,
        "https://example.test/file.tif",
        None,
        footprint,
        0,
        10,
        None,
        None,
        False,
    )
    return DiscoveredRefinementProduct(
        candidate_id,
        "good",
        "Good provider",
        "Product",
        "1",
        "dataset",
        ("agriculture.cropland",),
        footprint,
        10,
        None,
        None,
        "cog",
        10,
        license_metadata,
        (asset,),
        True,
    )


def test_provider_failure_does_not_hide_other_provider_results() -> None:
    class GoodProvider:
        provider_id = "good"

        async def discover(self, request):
            return (_candidate("candidate"),)

    class BadProvider:
        provider_id = "bad"

        async def discover(self, request):
            raise RuntimeError("provider unavailable")

    result = asyncio.run(
        RefinementDiscoveryCoordinator(
            (GoodProvider(), BadProvider()),
            CommercialLicensePolicy(),
        ).discover(_request())
    )

    assert tuple(item.candidate_id for item in result.candidates) == ("candidate",)
    assert result.failures[0].provider_id == "bad"
    assert result.failures[0].code == "provider_error"


@pytest.mark.skipif(
    os.getenv("TERRALAB_RUN_CLMS_SMOKE") != "1",
    reason="manual smoke test against the official CLMS OData catalogue",
)
def test_official_clms_odata_smoke() -> None:
    async def scenario() -> None:
        adapter = ClmsODataAdapter(
            ClmsProviderConfiguration(page_size=1, max_pages=1, timeout_seconds=30)
        )
        products = await adapter.discover(_request("official-smoke", 1))
        assert products
        assert products[0].dataset_identifier == (
            "clms_vlcc_crop-types_europe_10m_yearly_v1"
        )
        assert products[0].endpoint_verified

    asyncio.run(scenario())
