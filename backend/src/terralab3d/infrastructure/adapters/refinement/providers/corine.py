"""CORINE Land Cover discovery through the official EEA ArcGIS service."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import date
from urllib.parse import urlencode

import aiohttp
from shapely.geometry import box, mapping, shape

from terralab3d.domain.refinement.discovery import (
    DiscoveredRefinementProduct,
    DiscoveryRequest,
    RemoteAsset,
)
from terralab3d.domain.refinement.errors import RefinementError, RefinementValidationError
from terralab3d.domain.refinement.installations import (
    GeometryRecord,
    RefinementDataKind,
    RefinementProduct,
)
from terralab3d.domain.refinement.licensing import LicenseMetadata


class CorineDiscoveryError(RefinementError):
    """The official CORINE feature endpoint failed after bounded retries."""


@dataclass(frozen=True, slots=True)
class CorineProviderConfiguration:
    layer_url: str = (
        "https://image.discomap.eea.europa.eu/arcgis/rest/services/"
        "Corine/CLC2018_WM/MapServer/0"
    )
    timeout_seconds: float = 30.0
    retry_count: int = 2
    retry_backoff_seconds: float = 0.25
    page_size: int = 1000

    def __post_init__(self) -> None:
        if (
            self.timeout_seconds <= 0
            or self.retry_count < 0
            or self.page_size <= 0
            or self.page_size > 1000
        ):
            raise RefinementValidationError("Invalid CORINE provider configuration")


# The 44 official CLC level-3 classes. Mixed source concepts are intentionally
# kept at a TLST parent rather than being promoted to a false leaf.
CORINE_2018_TRANSLATION: dict[int, str] = {
    111: "artificial.built.urban_fabric",
    112: "artificial.built.urban_fabric",
    121: "artificial.industrial_commercial",
    122: "artificial.transport",
    123: "artificial.transport.port",
    124: "artificial.transport.airport",
    131: "artificial.extraction.quarry_mine",
    132: "artificial.waste",
    133: "artificial.construction_site",
    141: "artificial.artificial_green.urban_green",
    142: "artificial.artificial_green.sport_leisure",
    211: "agriculture.cropland.arable.annual_crop",
    212: "agriculture.cropland.arable.annual_crop",
    213: "agriculture.cropland.arable.rice",
    221: "agriculture.cropland.permanent_crop.vineyard",
    222: "agriculture.cropland.permanent_crop.orchard",
    223: "agriculture.cropland.permanent_crop.olive_grove",
    231: "agriculture.managed_grassland.pasture",
    241: "agriculture.heterogeneous.annual_and_permanent",
    242: "agriculture.heterogeneous.complex_cultivation",
    243: "agriculture.heterogeneous.agriculture_natural_mosaic",
    244: "agriculture.agroforestry",
    311: "tree_cover.broadleaf",
    312: "tree_cover.needleleaf",
    313: "tree_cover.mixed",
    321: "low_vegetation.herbaceous.natural_grassland",
    322: "low_vegetation.shrub.heath_moor",
    323: "low_vegetation.shrub.sclerophyllous",
    324: "low_vegetation.transitional_woodland_shrub",
    331: "bare_sparse.sand",
    332: "bare_sparse.bare_rock",
    333: "bare_sparse.sparse_vegetation",
    334: "bare_sparse.unspecified",
    335: "snow_ice.permanent.glacier_ice",
    411: "wetland.inland.marsh",
    412: "wetland.inland.peat_bog",
    421: "wetland.coastal.salt_marsh",
    422: "wetland.coastal.salt_pan",
    423: "wetland.coastal.intertidal_flat",
    511: "water.inland.watercourse",
    512: "water.inland.standing_water",
    521: "water.coastal.lagoon",
    522: "water.coastal.estuary",
    523: "water.marine.sea_ocean",
}
_COMPATIBLE_NODES = tuple(sorted(set(CORINE_2018_TRANSLATION.values())))
_EUROPE_FOOTPRINT = mapping(box(-31.6, 27.0, 45.0, 72.0))
_PROVENANCE_URL = "https://land.copernicus.eu/en/products/corine-land-cover/clc2018"
_LICENSE_URL = "https://land.copernicus.eu/en/faq/data-use-terms-and-conditions"


class CorineLandCoverAdapter:
    """Freeze paged, AOI-clipped GeoJSON queries for CLC 2018."""

    provider_id = "copernicus-corine"

    def __init__(self, configuration: CorineProviderConfiguration | None = None) -> None:
        self._configuration = configuration or CorineProviderConfiguration()

    async def discover(
        self,
        request: DiscoveryRequest,
    ) -> tuple[DiscoveredRefinementProduct, ...]:
        if not _supports_category(request.category_key):
            return ()
        aoi = shape(dict(request.aoi_geojson))
        europe = shape(_EUROPE_FOOTPRINT)
        if aoi.is_empty or not aoi.is_valid or not europe.intersects(aoi):
            return ()
        footprint = aoi.intersection(europe)
        bounds = footprint.bounds
        count = await self._feature_count(bounds)
        if count <= 0:
            return ()
        config = self._configuration
        page_count = (count + config.page_size - 1) // config.page_size
        footprint_geojson = mapping(footprint)
        assets = tuple(
            RemoteAsset(
                asset_id=f"corine-2018-page-{page_index + 1:04d}",
                download_url=self._feature_url(
                    bounds,
                    offset=page_index * config.page_size,
                ),
                s3_path=f"corine-2018-page-{page_index + 1:04d}.geojson",
                footprint=footprint_geojson,
                order=page_index,
                estimated_bytes=None,
                checksum_algorithm=None,
                checksum_value=None,
                requires_authentication=False,
                class_attribute="Code_18",
            )
            for page_index in range(page_count)
        )
        return (
            DiscoveredRefinementProduct(
                candidate_id=(
                    f"corine-2018-{request.request_id}-r{request.revision}"
                ),
                provider_id=self.provider_id,
                provider="Copernicus Land Monitoring Service / EEA",
                product="CORINE Land Cover 2018",
                version="v2020_20u1",
                dataset_identifier="corine-land-cover-2018",
                compatible_tlst_nodes=_COMPATIBLE_NODES,
                footprint=footprint_geojson,
                resolution_m=100,
                temporal_start="2018-01-01",
                temporal_end="2018-12-31",
                format="GeoJSON",
                estimated_bytes=None,
                license=_license(config),
                assets=assets,
                endpoint_verified=True,
                class_translation=CORINE_2018_TRANSLATION,
            ),
        )

    async def _feature_count(self, bounds: tuple[float, float, float, float]) -> int:
        params = self._spatial_params(bounds)
        params.update({"returnCountOnly": "true", "f": "json"})
        url = f"{self._configuration.layer_url.rstrip('/')}/query"
        timeout = aiohttp.ClientTimeout(total=self._configuration.timeout_seconds)
        error: Exception | None = None
        for attempt in range(self._configuration.retry_count + 1):
            try:
                async with aiohttp.ClientSession(timeout=timeout) as session:
                    async with session.get(url, params=params) as response:
                        response.raise_for_status()
                        payload = await response.json(content_type=None)
                if not isinstance(payload, dict) or not isinstance(payload.get("count"), int):
                    raise CorineDiscoveryError("CORINE count response is invalid")
                return int(payload["count"])
            except (aiohttp.ClientError, asyncio.TimeoutError, ValueError) as exc:
                error = exc
                if attempt < self._configuration.retry_count:
                    await asyncio.sleep(
                        self._configuration.retry_backoff_seconds * (attempt + 1)
                    )
        raise CorineDiscoveryError("CORINE discovery failed after retries") from error

    def _feature_url(
        self,
        bounds: tuple[float, float, float, float],
        *,
        offset: int,
    ) -> str:
        params = self._spatial_params(bounds)
        params.update(
            {
                "outFields": "Code_18",
                "returnGeometry": "true",
                "outSR": "4326",
                "orderByFields": "OBJECTID",
                "resultOffset": str(offset),
                "resultRecordCount": str(self._configuration.page_size),
                "f": "geojson",
            }
        )
        query = urlencode(params, safe=",")
        return f"{self._configuration.layer_url.rstrip('/')}/query?{query}"

    @staticmethod
    def _spatial_params(
        bounds: tuple[float, float, float, float],
    ) -> dict[str, str]:
        return {
            "where": "1=1",
            "geometry": ",".join(f"{coordinate:.8f}" for coordinate in bounds),
            "geometryType": "esriGeometryEnvelope",
            "inSR": "4326",
            "spatialRel": "esriSpatialRelIntersects",
        }


def corine_refinement_products() -> tuple[RefinementProduct, ...]:
    config = CorineProviderConfiguration()
    return (
        RefinementProduct(
            product_id="corine-land-cover-2018",
            resource_id="earth.refinement.copernicus.corine.2018",
            variant_id="v2020_20u1",
            provider="Copernicus Land Monitoring Service / EEA",
            product="CORINE Land Cover 2018",
            version="v2020_20u1",
            tlst_nodes=_COMPATIBLE_NODES,
            data_kind=RefinementDataKind.VECTOR,
            original_crs="EPSG:3857",
            planned_geometry=GeometryRecord("EPSG:4326", _EUROPE_FOOTPRINT),
            license=_license(config),
            provenance_url=_PROVENANCE_URL,
            priority=20,
        ),
    )


def _supports_category(category_key: str) -> bool:
    if category_key == "surface":
        return True
    return any(
        node == category_key
        or node.startswith(f"{category_key}.")
        or category_key.startswith(f"{node}.")
        for node in _COMPATIBLE_NODES
    )


def _license(config: CorineProviderConfiguration) -> LicenseMetadata:
    return LicenseMetadata(
        license_id="Copernicus-CLMS",
        official_url=_LICENSE_URL,
        attribution_text="Contains modified Copernicus Service information (2018).",
        citation="Copernicus Land Monitoring Service, CORINE Land Cover 2018",
        provider="Copernicus Land Monitoring Service / EEA",
        product="CORINE Land Cover 2018",
        version="v2020_20u1",
        checked_at=date(2026, 8, 25),
        provenance_url=_PROVENANCE_URL,
        asset_fingerprints=(f"arcgis-layer:{config.layer_url}",),
        commercial_use=True,
    )
