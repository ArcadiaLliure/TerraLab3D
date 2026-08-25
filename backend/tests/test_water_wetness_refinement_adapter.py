from __future__ import annotations

import asyncio
import json
import os

import aiohttp
import numpy as np
import pytest
from aiohttp import web
from rasterio.io import MemoryFile
from rasterio.transform import from_origin

from terralab3d.domain.refinement.discovery import DiscoveryRequest
from terralab3d.domain.refinement.errors import RefinementValidationError
from terralab3d.domain.refinement.licensing import CommercialLicensePolicy, LicenseUseStage
from terralab3d.infrastructure.adapters.refinement.providers.water_wetness import (
    WATER_WETNESS_2018_TRANSLATION,
    WaterWetnessConfiguration,
    WaterWetnessImageServerAdapter,
    water_wetness_refinement_products,
)
from terralab3d.infrastructure.adapters.surface.tlst_catalog import (
    load_builtin_land_cover_registry,
)


_AOI = {
    "type": "Polygon",
    "coordinates": (((2.10, 41.30), (2.11, 41.30), (2.11, 41.31), (2.10, 41.31), (2.10, 41.30)),),
}


def _request(category_key: str = "wetland") -> DiscoveryRequest:
    return DiscoveryRequest("water-wetness", 1, category_key, _AOI)


def test_water_wetness_freezes_raw_bounded_geotiff_exports() -> None:
    products = asyncio.run(WaterWetnessImageServerAdapter().discover(_request()))
    assert len(products) == 1
    candidate = products[0]
    assert candidate.endpoint_verified
    assert candidate.resolution_m == 10
    assert candidate.class_translation == WATER_WETNESS_2018_TRANSLATION
    assert candidate.nodata_values == (0, 254, 255)
    assert candidate.assets
    assert all(asset.s3_path and asset.s3_path.endswith(".tif") for asset in candidate.assets)
    assert all("/exportImage?" in asset.download_url for asset in candidate.assets)
    assert CommercialLicensePolicy().evaluate(
        candidate.license,
        stage=LicenseUseStage.CATALOG_DISPLAY,
    ).allowed


def test_water_wetness_tiles_requests_and_rejects_unbounded_continental_exports() -> None:
    tiled = asyncio.run(
        WaterWetnessImageServerAdapter(
            WaterWetnessConfiguration(maximum_tile_pixels=64, maximum_tiles=64)
        ).discover(_request("water"))
    )
    assert len(tiled[0].assets) > 1
    with pytest.raises(RefinementValidationError, match="too large"):
        asyncio.run(
            WaterWetnessImageServerAdapter(
                WaterWetnessConfiguration(maximum_tile_pixels=16, maximum_tiles=1)
            ).discover(_request("water"))
        )


def test_water_wetness_simulated_image_server_contract_returns_analytic_tiff() -> None:
    async def scenario() -> None:
        with MemoryFile() as memory:
            with memory.open(
                driver="GTiff",
                width=2,
                height=2,
                count=1,
                dtype="uint8",
                crs="EPSG:3035",
                transform=from_origin(4_000_000, 3_000_000, 10, 10),
            ) as dataset:
                dataset.write(np.array([[0, 1], [3, 253]], dtype=np.uint8), 1)
            payload = memory.read()

        async def handler(request: web.Request) -> web.Response:
            assert request.query["bboxSR"] == "3035"
            assert request.query["imageSR"] == "3035"
            assert request.query["format"] == "tiff"
            assert request.query["pixelType"] == "U8"
            assert request.query["interpolation"] == "RSP_NearestNeighbor"
            assert json.loads(request.query["renderingRule"])["rasterFunction"] == "None"
            assert request.query["f"] == "image"
            return web.Response(body=payload, content_type="image/tiff")

        app = web.Application()
        app.router.add_get("/ImageServer/exportImage", handler)
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, "127.0.0.1", 0)
        await site.start()
        port = site._server.sockets[0].getsockname()[1]
        try:
            products = await WaterWetnessImageServerAdapter(
                WaterWetnessConfiguration(
                    image_server_url=f"http://127.0.0.1:{port}/ImageServer",
                )
            ).discover(_request())
            async with aiohttp.ClientSession() as session:
                async with session.get(products[0].assets[0].download_url) as response:
                    response.raise_for_status()
                    downloaded = await response.read()
        finally:
            await runner.cleanup()

        with MemoryFile(downloaded) as memory:
            with memory.open() as dataset:
                assert dataset.count == 1
                assert dataset.dtypes == ("uint8",)
                assert {1, 3, 253} <= set(dataset.read(1).ravel())

    asyncio.run(scenario())


def test_water_wetness_mapping_and_static_catalog_are_canonical() -> None:
    taxonomy = load_builtin_land_cover_registry().taxonomy
    assert set(WATER_WETNESS_2018_TRANSLATION.values()) <= set(taxonomy.category_keys)
    product = water_wetness_refinement_products()[0]
    assert product.original_crs == "EPSG:3035"
    assert product.data_kind.value == "raster"


@pytest.mark.skipif(
    os.getenv("TERRALAB_RUN_WATER_WETNESS_SMOKE") != "1",
    reason="Set TERRALAB_RUN_WATER_WETNESS_SMOKE=1 for the official endpoint smoke test",
)
def test_official_water_wetness_export_is_single_band_analytic_tiff() -> None:
    async def scenario() -> None:
        products = await WaterWetnessImageServerAdapter().discover(_request())
        timeout = aiohttp.ClientTimeout(total=60)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(products[0].assets[0].download_url) as response:
                response.raise_for_status()
                payload = await response.read()
                assert response.headers["Content-Type"].startswith("image/tiff")
        with MemoryFile(payload) as memory:
            with memory.open() as dataset:
                assert 'AUTHORITY["EPSG","3035"]' in dataset.crs.to_wkt()
                assert dataset.count == 1
                assert dataset.dtypes == ("uint8",)
                assert int(dataset.read(1).max()) <= 255

    asyncio.run(scenario())
