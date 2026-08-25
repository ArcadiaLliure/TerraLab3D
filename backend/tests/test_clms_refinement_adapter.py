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
from terralab3d.infrastructure.adapters.surface.tlst_catalog import (
    load_builtin_land_cover_registry,
)


def _request(request_id: str = "request-1", revision: int = 1) -> DiscoveryRequest:
    return DiscoveryRequest(
        request_id=request_id,
        revision=revision,
        category_key="agriculture.cropland.permanent_crop.vineyard",
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


def test_global_dynamic_land_cover_mapping_is_available_without_overinterpretation() -> None:
    async def scenario() -> None:
        filters: list[str] = []

        async def handler(request: web.Request) -> web.Response:
            filters.append(request.query["$filter"])
            return web.json_response({"value": [_record("global-tile")]})

        runner, url = await _serve(handler)
        try:
            adapter = ClmsODataAdapter(
                ClmsProviderConfiguration(catalogue_url=url, retry_count=0)
            )
            request = DiscoveryRequest(
                "global",
                1,
                "snow_ice",
                _request().aoi_geojson,
            )
            products = await adapter.discover(request)
        finally:
            await runner.cleanup()

        assert len(products) == 2
        assert any("lcm_global_10m_yearly_v1" in item for item in filters)
        global_product = next(
            product
            for product in products
            if product.dataset_identifier == "lcm_global_10m_yearly_v1"
        )
        assert global_product.class_translation[110] == "snow_ice.unspecified"
        assert global_product.class_translation[80] == "bare_sparse.unspecified"
        assert global_product.endpoint_verified is True

    asyncio.run(scenario())


def test_all_clms_template_nodes_are_canonical_tlst_keys() -> None:
    from terralab3d.infrastructure.adapters.refinement.providers.clms import (
        clms_refinement_products,
    )

    taxonomy = load_builtin_land_cover_registry().taxonomy
    nodes = {node for product in clms_refinement_products() for node in product.tlst_nodes}
    assert nodes <= set(taxonomy.category_keys)


def test_grassland_mapping_preserves_mixed_grassland_semantics() -> None:
    async def scenario() -> None:
        filters: list[str] = []

        async def handler(request: web.Request) -> web.Response:
            filters.append(request.query["$filter"])
            return web.json_response({"value": [_record("grass-tile")]})

        runner, url = await _serve(handler)
        try:
            products = await ClmsODataAdapter(
                ClmsProviderConfiguration(catalogue_url=url, retry_count=0)
            ).discover(
                DiscoveryRequest(
                    "grass",
                    1,
                    "low_vegetation.herbaceous.unspecified",
                    _request().aoi_geojson,
                )
            )
        finally:
            await runner.cleanup()

        grass = next(
            product
            for product in products
            if product.dataset_identifier
            == "clms_vlcc_grassland_europe_10m_yearly_v1"
        )
        assert any("clms_vlcc_grassland_europe_10m_yearly_v1" in item for item in filters)
        assert grass.class_translation == {1: "low_vegetation.herbaceous.unspecified"}
        assert grass.nodata_values == (0, 255)

    asyncio.run(scenario())


def test_snow_phenology_separates_seasonal_from_full_year_snow() -> None:
    async def scenario() -> None:
        async def handler(request: web.Request) -> web.Response:
            return web.json_response({"value": [_record("snow-tile")]})

        runner, url = await _serve(handler)
        try:
            products = await ClmsODataAdapter(
                ClmsProviderConfiguration(catalogue_url=url, retry_count=0)
            ).discover(
                DiscoveryRequest(
                    "snow",
                    1,
                    "snow_ice.seasonal",
                    _request().aoi_geojson,
                )
            )
        finally:
            await runner.cleanup()

        snow = next(
            product
            for product in products
            if product.dataset_identifier
            == "clms_wsi_snow-phenology-s2_europe_utm_20m_yearly_v1"
        )
        assert snow.class_translation[1] == "snow_ice.seasonal"
        assert snow.class_translation[364] == "snow_ice.seasonal"
        assert snow.class_translation[365] == "snow_ice.permanent.snow"
        assert snow.qualifier_key == "snow_cover_duration_days"

    asyncio.run(scenario())


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


@pytest.mark.skipif(
    os.getenv("TERRALAB_RUN_CLMS_SMOKE") != "1",
    reason="manual smoke test against the official CLMS OData catalogue",
)
def test_official_global_lcm_odata_smoke() -> None:
    async def scenario() -> None:
        adapter = ClmsODataAdapter(
            ClmsProviderConfiguration(page_size=1, max_pages=1, timeout_seconds=30)
        )
        request = DiscoveryRequest(
            "global-smoke",
            1,
            "artificial.built",
            _request().aoi_geojson,
        )
        products = await adapter.discover(request)
        assert products
        assert products[0].dataset_identifier == "lcm_global_10m_yearly_v1"
        assert products[0].endpoint_verified

    asyncio.run(scenario())


@pytest.mark.skipif(
    os.getenv("TERRALAB_RUN_CLMS_SMOKE") != "1",
    reason="manual smoke test against the official CLMS OData catalogue",
)
def test_official_grassland_odata_smoke() -> None:
    async def scenario() -> None:
        adapter = ClmsODataAdapter(
            ClmsProviderConfiguration(page_size=1, max_pages=1, timeout_seconds=30)
        )
        request = DiscoveryRequest(
            "grassland-smoke",
            1,
            "low_vegetation.herbaceous.unspecified",
            _request().aoi_geojson,
        )
        products = await adapter.discover(request)
        assert any(
            product.dataset_identifier
            == "clms_vlcc_grassland_europe_10m_yearly_v1"
            for product in products
        )

    asyncio.run(scenario())


@pytest.mark.skipif(
    os.getenv("TERRALAB_RUN_CLMS_SMOKE") != "1",
    reason="manual smoke test against the official CLMS OData catalogue",
)
def test_official_snow_phenology_odata_smoke() -> None:
    async def scenario() -> None:
        products = await ClmsODataAdapter(
            ClmsProviderConfiguration(page_size=1, max_pages=1, timeout_seconds=30)
        ).discover(
            DiscoveryRequest(
                "snow-smoke",
                1,
                "snow_ice.seasonal",
                _request().aoi_geojson,
            )
        )
        assert any(
            product.dataset_identifier
            == "clms_wsi_snow-phenology-s2_europe_utm_20m_yearly_v1"
            for product in products
        )

    asyncio.run(scenario())
