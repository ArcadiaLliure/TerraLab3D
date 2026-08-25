"""AOI exports from the official CLMS Water & Wetness ImageServer."""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from datetime import date
from urllib.parse import urlencode

from pyproj import Transformer
from shapely.geometry import box, mapping, shape
from shapely.ops import transform

from terralab3d.domain.refinement.discovery import (
    DiscoveredRefinementProduct,
    DiscoveryRequest,
    RemoteAsset,
)
from terralab3d.domain.refinement.errors import RefinementValidationError
from terralab3d.domain.refinement.installations import (
    GeometryRecord,
    RefinementDataKind,
    RefinementProduct,
)
from terralab3d.domain.refinement.licensing import LicenseMetadata


WATER_WETNESS_2018_TRANSLATION: dict[int, str] = {
    1: "water.unspecified",
    2: "water.unspecified",
    3: "wetland.unspecified",
    4: "wetland.unspecified",
    253: "water.marine.sea_ocean",
}
_COMPATIBLE_NODES = tuple(sorted(set(WATER_WETNESS_2018_TRANSLATION.values())))
_EUROPE_FOOTPRINT = mapping(box(-31.5, 24.0, 45.0, 72.0))
_PROVENANCE_URL = (
    "https://land.copernicus.eu/en/products/high-resolution-layer-water-and-wetness/"
    "water-and-wetness-status-2018"
)
_LICENSE_URL = "https://land.copernicus.eu/en/faq/data-use-terms-and-conditions"


@dataclass(frozen=True, slots=True)
class WaterWetnessConfiguration:
    image_server_url: str = (
        "https://image.discomap.eea.europa.eu/arcgis/rest/services/"
        "GioLandPublic/HRL_WaterWetness_2018/ImageServer"
    )
    resolution_m: float = 10.0
    maximum_tile_pixels: int = 4_000
    maximum_tiles: int = 256

    def __post_init__(self) -> None:
        if (
            not self.image_server_url.startswith(("http://", "https://"))
            or self.resolution_m <= 0
            or self.maximum_tile_pixels <= 0
            or self.maximum_tile_pixels > 4_100
            or self.maximum_tiles <= 0
        ):
            raise RefinementValidationError("Invalid Water & Wetness configuration")


class WaterWetnessImageServerAdapter:
    """Freeze bounded raw GeoTIFF exports; WMS imagery is never used analytically."""

    provider_id = "copernicus-water-wetness"

    def __init__(self, configuration: WaterWetnessConfiguration | None = None) -> None:
        self._configuration = configuration or WaterWetnessConfiguration()

    async def discover(
        self,
        request: DiscoveryRequest,
    ) -> tuple[DiscoveredRefinementProduct, ...]:
        if not _supports_category(request.category_key):
            return ()
        aoi = shape(dict(request.aoi_geojson))
        available = shape(_EUROPE_FOOTPRINT)
        if aoi.is_empty or not aoi.is_valid or not available.intersects(aoi):
            return ()
        footprint = aoi.intersection(available)
        to_laea = Transformer.from_crs("EPSG:4326", "EPSG:3035", always_xy=True)
        to_wgs84 = Transformer.from_crs("EPSG:3035", "EPSG:4326", always_xy=True)
        projected = transform(to_laea.transform, footprint)
        min_x, min_y, max_x, max_y = projected.bounds
        tile_span = self._configuration.maximum_tile_pixels * self._configuration.resolution_m
        columns = max(1, math.ceil((max_x - min_x) / tile_span))
        rows = max(1, math.ceil((max_y - min_y) / tile_span))
        if columns * rows > self._configuration.maximum_tiles:
            raise RefinementValidationError(
                "Water & Wetness AOI is too large for a bounded ImageServer export"
            )

        assets: list[RemoteAsset] = []
        estimated_bytes = 0
        for row in range(rows):
            tile_min_y = min_y + row * tile_span
            tile_max_y = min(max_y, tile_min_y + tile_span)
            for column in range(columns):
                tile_min_x = min_x + column * tile_span
                tile_max_x = min(max_x, tile_min_x + tile_span)
                tile = box(tile_min_x, tile_min_y, tile_max_x, tile_max_y)
                clipped = tile.intersection(projected)
                if clipped.is_empty:
                    continue
                width = max(1, math.ceil((tile_max_x - tile_min_x) / self._configuration.resolution_m))
                height = max(1, math.ceil((tile_max_y - tile_min_y) / self._configuration.resolution_m))
                order = len(assets)
                file_name = f"waw-2018-r{row:03d}-c{column:03d}.tif"
                params = {
                    "bbox": ",".join(
                        f"{value:.3f}"
                        for value in (tile_min_x, tile_min_y, tile_max_x, tile_max_y)
                    ),
                    "bboxSR": "3035",
                    "imageSR": "3035",
                    "size": f"{width},{height}",
                    "format": "tiff",
                    "pixelType": "U8",
                    "interpolation": "RSP_NearestNeighbor",
                    "renderingRule": json.dumps(
                        {"rasterFunction": "None"}, separators=(",", ":")
                    ),
                    "f": "image",
                }
                byte_count = width * height
                estimated_bytes += byte_count
                assets.append(
                    RemoteAsset(
                        asset_id=f"clms-waw-2018-{row:03d}-{column:03d}",
                        download_url=(
                            f"{self._configuration.image_server_url.rstrip('/')}/exportImage?"
                            f"{urlencode(params)}"
                        ),
                        s3_path=file_name,
                        footprint=mapping(transform(to_wgs84.transform, clipped)),
                        order=order,
                        estimated_bytes=byte_count,
                        checksum_algorithm=None,
                        checksum_value=None,
                        requires_authentication=False,
                    )
                )
        if not assets:
            return ()
        return (
            DiscoveredRefinementProduct(
                candidate_id="clms-water-wetness-2018-v2",
                provider_id=self.provider_id,
                provider="Copernicus Land Monitoring Service",
                product="Water and Wetness status 2018",
                version="2018-v2",
                dataset_identifier="clms-hrl-water-wetness-2018",
                compatible_tlst_nodes=_COMPATIBLE_NODES,
                footprint=mapping(footprint),
                resolution_m=self._configuration.resolution_m,
                temporal_start="2012-01-01",
                temporal_end="2018-12-31",
                format="GeoTIFF",
                estimated_bytes=estimated_bytes,
                license=_license(),
                assets=tuple(assets),
                endpoint_verified=True,
                class_translation=WATER_WETNESS_2018_TRANSLATION,
                nodata_values=(0, 254, 255),
            ),
        )


def water_wetness_refinement_products() -> tuple[RefinementProduct, ...]:
    return (
        RefinementProduct(
            product_id="clms-hrl-water-wetness-2018",
            resource_id="earth.refinement.clms.water-wetness-2018",
            variant_id="2018-v2",
            provider="Copernicus Land Monitoring Service",
            product="Water and Wetness status 2018",
            version="2018-v2",
            tlst_nodes=_COMPATIBLE_NODES,
            data_kind=RefinementDataKind.RASTER,
            original_crs="EPSG:3035",
            planned_geometry=GeometryRecord("EPSG:4326", _EUROPE_FOOTPRINT),
            license=_license(),
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


def _license() -> LicenseMetadata:
    return LicenseMetadata(
        license_id="Copernicus-CLMS",
        official_url=_LICENSE_URL,
        attribution_text=(
            "European Union, Copernicus Land Monitoring Service, "
            "Water and Wetness 2018"
        ),
        citation="Copernicus Land Monitoring Service, HRL Water and Wetness 2018",
        provider="European Environment Agency",
        product="Water and Wetness status 2018",
        version="2018-v2",
        checked_at=date(2026, 8, 25),
        provenance_url=_PROVENANCE_URL,
        asset_fingerprints=("service:HRL_WaterWetness_2018/ImageServer",),
        commercial_use=True,
    )
