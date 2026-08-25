from __future__ import annotations

import asyncio
import os
from urllib.parse import parse_qs, urlsplit

import aiohttp
import pytest
from aiohttp import web

from terralab3d.domain.refinement.discovery import DiscoveryRequest
from terralab3d.domain.refinement.licensing import CommercialLicensePolicy, LicenseUseStage
from terralab3d.infrastructure.adapters.refinement.providers.corine import (
    CORINE_2018_TRANSLATION,
    CorineLandCoverAdapter,
    CorineProviderConfiguration,
    corine_refinement_products,
)
from terralab3d.infrastructure.adapters.surface.tlst_catalog import (
    load_builtin_land_cover_registry,
)


_AOI = {
    "type": "Polygon",
    "coordinates": (
        ((2.16, 41.38), (2.17, 41.38), (2.17, 41.39), (2.16, 41.39), (2.16, 41.38)),
    ),
}


async def _serve_count(handler) -> tuple[web.AppRunner, str]:
    app = web.Application()
    app.router.add_get("/MapServer/0/query", handler)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "127.0.0.1", 0)
    await site.start()
    port = site._server.sockets[0].getsockname()[1]
    return runner, f"http://127.0.0.1:{port}/MapServer/0"


def _request(category_key: str = "surface") -> DiscoveryRequest:
    return DiscoveryRequest("corine-request", 3, category_key, _AOI)


def test_corine_freezes_all_paged_vector_queries_from_simulated_count() -> None:
    async def scenario() -> None:
        async def handler(request: web.Request) -> web.Response:
            assert request.query["returnCountOnly"] == "true"
            assert request.query["geometryType"] == "esriGeometryEnvelope"
            assert request.query["inSR"] == "4326"
            return web.json_response({"count": 1501})

        runner, layer_url = await _serve_count(handler)
        try:
            adapter = CorineLandCoverAdapter(
                CorineProviderConfiguration(
                    layer_url=layer_url,
                    retry_count=0,
                )
            )
            products = await adapter.discover(_request())
        finally:
            await runner.cleanup()

        assert len(products) == 1
        candidate = products[0]
        assert len(candidate.assets) == 2
        assert candidate.assets[0].class_attribute == "Code_18"
        assert candidate.assets[0].s3_path == "corine-2018-page-0001.geojson"
        first_query = parse_qs(urlsplit(candidate.assets[0].download_url).query)
        second_query = parse_qs(urlsplit(candidate.assets[1].download_url).query)
        assert first_query["f"] == ["geojson"]
        assert first_query["outFields"] == ["Code_18"]
        assert first_query["resultOffset"] == ["0"]
        assert second_query["resultOffset"] == ["1000"]
        assert CommercialLicensePolicy().evaluate(
            candidate.license,
            stage=LicenseUseStage.CATALOG_DISPLAY,
        ).allowed

    asyncio.run(scenario())


def test_corine_returns_nothing_for_unsupported_or_empty_intersection() -> None:
    adapter = CorineLandCoverAdapter()
    assert not asyncio.run(adapter.discover(_request("snow_ice.permanent_snow")))
    outside = {
        "type": "Polygon",
        "coordinates": (((120, -30), (121, -30), (121, -29), (120, -29), (120, -30)),),
    }
    assert not asyncio.run(
        adapter.discover(DiscoveryRequest("outside", 0, "surface", outside))
    )


def test_corine_translation_covers_all_official_level_three_classes() -> None:
    assert len(CORINE_2018_TRANSLATION) == 44
    assert CORINE_2018_TRANSLATION[131] == "artificial.extraction.quarry_mine"
    assert CORINE_2018_TRANSLATION[213] == "agriculture.cropland.arable.rice"
    assert CORINE_2018_TRANSLATION[313] == "tree_cover.mixed"
    assert CORINE_2018_TRANSLATION[423] == "wetland.coastal.intertidal_flat"
    assert CORINE_2018_TRANSLATION[522] == "water.coastal.estuary"
    product = corine_refinement_products()[0]
    assert product.data_kind.value == "vector"
    assert set(product.tlst_nodes) == set(CORINE_2018_TRANSLATION.values())
    taxonomy = load_builtin_land_cover_registry().taxonomy
    assert set(CORINE_2018_TRANSLATION.values()) <= set(taxonomy.category_keys)


@pytest.mark.skipif(
    os.environ.get("TERRALAB_RUN_CORINE_SMOKE") != "1",
    reason="Set TERRALAB_RUN_CORINE_SMOKE=1 for the official endpoint smoke test",
)
def test_corine_official_endpoint_returns_geojson_with_class_field() -> None:
    async def scenario() -> None:
        products = await CorineLandCoverAdapter(
            CorineProviderConfiguration(retry_count=0)
        ).discover(_request("artificial.built"))
        assert products
        asset = products[0].assets[0]
        timeout = aiohttp.ClientTimeout(total=30)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(asset.download_url) as response:
                response.raise_for_status()
                document = await response.json(content_type=None)
        assert document["type"] == "FeatureCollection"
        assert document["features"]
        assert "Code_18" in document["features"][0]["properties"]

    asyncio.run(scenario())
