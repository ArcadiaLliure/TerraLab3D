from __future__ import annotations

import asyncio

from terralab3d.domain.refinement.discovery import DiscoveryRequest
from terralab3d.domain.refinement.licensing import CommercialLicensePolicy, LicenseUseStage
from terralab3d.infrastructure.adapters.refinement.providers.icgc import (
    ICGC_MCSC_2024_TRANSLATION,
    IcgcLandCoverAdapter,
    IcgcLandCoverConfiguration,
    icgc_refinement_products,
)


CATALONIA_AOI = {
    "type": "Polygon",
    "coordinates": (((1.8, 41.4), (2.1, 41.4), (2.1, 41.7), (1.8, 41.7), (1.8, 41.4)),),
}


def test_icgc_discovers_official_analytic_raster_for_catalonia() -> None:
    adapter = IcgcLandCoverAdapter(
        IcgcLandCoverConfiguration(
            asset_url="https://example.test/mcsc-2024.tif",
            estimated_bytes=1234,
        )
    )
    result = asyncio.run(
        adapter.discover(DiscoveryRequest("request-1", 2, "artificial.transport", CATALONIA_AOI))
    )
    assert len(result) == 1
    candidate = result[0]
    assert candidate.resolution_m == 1
    assert candidate.estimated_bytes == 1234
    assert candidate.assets[0].requires_authentication is False
    assert candidate.endpoint_verified is True
    assert candidate.class_translation[31] == "artificial.transport.road"
    assert candidate.class_translation[41] == "water.marine.sea_ocean"
    assert candidate.nodata_values == (0,)
    assert CommercialLicensePolicy().evaluate(
        candidate.license, stage=LicenseUseStage.CATALOG_DISPLAY
    ).allowed


def test_icgc_rejects_aoi_outside_catalonia_and_unsupported_node() -> None:
    adapter = IcgcLandCoverAdapter()
    outside = {
        "type": "Polygon",
        "coordinates": (((-4.0, 39.0), (-3.0, 39.0), (-3.0, 40.0), (-4.0, 40.0), (-4.0, 39.0)),),
    }
    assert not asyncio.run(adapter.discover(DiscoveryRequest("r", 0, "water", outside)))
    assert not asyncio.run(
        adapter.discover(DiscoveryRequest("r", 0, "snow_ice.glacier_ice", CATALONIA_AOI))
    )


def test_icgc_catalog_and_mapping_cover_relevant_tlst_families() -> None:
    assert len(ICGC_MCSC_2024_TRANSLATION) == 41
    translated = set(ICGC_MCSC_2024_TRANSLATION.values())
    assert {
        "artificial.transport.airport",
        "agriculture.cropland.permanent_crop.vineyard",
        "tree_cover.needleleaf",
        "low_vegetation.shrub.shrubland",
        "wetland.inland.forested_wetland",
        "bare_sparse.sand.beach",
        "water.artificial.canal",
    } <= translated
    template = icgc_refinement_products()[0]
    assert template.priority == 0
    assert set(template.tlst_nodes) == translated
