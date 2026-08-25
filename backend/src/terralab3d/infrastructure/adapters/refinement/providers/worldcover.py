"""ESA WorldCover discovery from the public 2021 v200 COG tile archive."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from math import floor
from pathlib import PurePosixPath
from typing import Iterable

from shapely.geometry import box, mapping, shape

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
from terralab3d.domain.surface.tlst import SingleSurface
from terralab3d.infrastructure.adapters.refinement.acquisition import (
    AsyncHttpRangeClient,
    HttpClientConfiguration,
)
from terralab3d.infrastructure.adapters.surface.tlst_catalog import (
    load_builtin_land_cover_registry,
)


_PROVENANCE_URL = "https://esa-worldcover.org/en/data-access"
_LICENSE_URL = "https://creativecommons.org/licenses/by/4.0/"
_WORLD_FOOTPRINT = {
    "type": "Polygon",
    "coordinates": (((-180.0, -90.0), (180.0, -90.0), (180.0, 90.0),
                     (-180.0, 90.0), (-180.0, -90.0)),),
}


def _worldcover_translation() -> dict[int, str]:
    scheme = load_builtin_land_cover_registry().get("esa_worldcover", "2021-v200")
    return {
        definition.source_code: definition.translation.category_key
        for definition in scheme.classes
        if isinstance(definition.translation, SingleSurface)
    }


WORLD_COVER_2021_TRANSLATION = _worldcover_translation()
_COMPATIBLE_NODES = tuple(sorted(set(WORLD_COVER_2021_TRANSLATION.values())))


@dataclass(frozen=True, slots=True)
class WorldCoverConfiguration:
    """Frozen public archive contract documented by ESA WorldCover."""

    base_url: str = (
        "https://esa-worldcover.s3.eu-central-1.amazonaws.com/"
        "v200/2021/map"
    )
    version: str = "2021-v200"
    tile_size_degrees: int = 3
    maximum_tiles_per_request: int = 128
    timeout_seconds: float = 30.0
    maximum_concurrency: int = 8

    def __post_init__(self) -> None:
        if self.tile_size_degrees <= 0 or 180 % self.tile_size_degrees:
            raise RefinementValidationError("WorldCover tile size must divide 180 degrees")
        if self.maximum_tiles_per_request <= 0:
            raise RefinementValidationError("WorldCover tile limit must be positive")


class WorldCoverCogAdapter:
    """Discover only existing public 3x3 degree COGs intersecting an AOI."""

    provider_id = "esa-worldcover"

    def __init__(
        self,
        configuration: WorldCoverConfiguration | None = None,
        *,
        http_client: AsyncHttpRangeClient | None = None,
    ) -> None:
        self._configuration = configuration or WorldCoverConfiguration()
        self._http = http_client or AsyncHttpRangeClient(
            HttpClientConfiguration(
                timeout_seconds=self._configuration.timeout_seconds,
                maximum_concurrency=self._configuration.maximum_concurrency,
            )
        )

    async def discover(
        self,
        request: DiscoveryRequest,
    ) -> tuple[DiscoveredRefinementProduct, ...]:
        if not _supports_category(request.category_key):
            return ()
        aoi = shape(dict(request.aoi_geojson))
        if aoi.is_empty or not aoi.is_valid:
            return ()

        tile_origins = _intersecting_tile_origins(
            request.aoi_geojson,
            tile_size_degrees=self._configuration.tile_size_degrees,
        )
        if len(tile_origins) > self._configuration.maximum_tiles_per_request:
            raise RefinementValidationError(
                "AOI requires too many WorldCover tiles; reduce the selection "
                f"below {self._configuration.maximum_tiles_per_request} tiles"
            )
        urls = tuple(self._tile_url(latitude, longitude) for latitude, longitude in tile_origins)
        metadata = await self._http.probe_many(urls)

        assets: list[RemoteAsset] = []
        footprints = []
        total_bytes = 0
        has_unknown_size = False
        for order, ((latitude, longitude), url, item) in enumerate(
            zip(tile_origins, urls, metadata, strict=True)
        ):
            if item is None:
                continue
            footprint = box(
                longitude,
                latitude,
                longitude + self._configuration.tile_size_degrees,
                latitude + self._configuration.tile_size_degrees,
            )
            clipped = footprint.intersection(aoi)
            if clipped.is_empty:
                continue
            footprints.append(clipped)
            if item.size_bytes is None:
                has_unknown_size = True
            else:
                total_bytes += item.size_bytes
            filename = PurePosixPath(url).name
            assets.append(
                RemoteAsset(
                    asset_id=filename.removesuffix(".tif"),
                    download_url=url,
                    s3_path=f"v200/2021/map/{filename}",
                    footprint=dict(mapping(footprint)),
                    order=order,
                    estimated_bytes=item.size_bytes,
                    checksum_algorithm="etag" if item.etag else None,
                    checksum_value=item.etag,
                    requires_authentication=False,
                )
            )
        if not assets:
            return ()

        from shapely.ops import unary_union

        available = unary_union(footprints)
        config = self._configuration
        return (
            DiscoveredRefinementProduct(
                candidate_id=(
                    f"esa-worldcover-{config.version}-{request.request_id}-r{request.revision}"
                ),
                provider_id=self.provider_id,
                provider="European Space Agency",
                product="ESA WorldCover",
                version=config.version,
                dataset_identifier="esa-worldcover-2021-v200",
                compatible_tlst_nodes=_COMPATIBLE_NODES,
                footprint=dict(mapping(available)),
                resolution_m=10,
                temporal_start="2021-01-01",
                temporal_end="2021-12-31",
                format="Cloud Optimized GeoTIFF",
                estimated_bytes=None if has_unknown_size else total_bytes,
                license=_license(config),
                assets=tuple(assets),
                endpoint_verified=True,
                class_translation=WORLD_COVER_2021_TRANSLATION,
                nodata_values=(0,),
            ),
        )

    def _tile_url(self, latitude: int, longitude: int) -> str:
        filename = _worldcover_tile_filename(latitude, longitude)
        return f"{self._configuration.base_url.rstrip('/')}/{filename}"


def worldcover_refinement_products() -> tuple[RefinementProduct, ...]:
    config = WorldCoverConfiguration()
    return (
        RefinementProduct(
            product_id="esa-worldcover-2021",
            resource_id="earth.refinement.esa.worldcover",
            variant_id=config.version,
            provider="European Space Agency",
            product="ESA WorldCover",
            version=config.version,
            tlst_nodes=_COMPATIBLE_NODES,
            data_kind=RefinementDataKind.RASTER,
            original_crs="EPSG:4326",
            planned_geometry=GeometryRecord("EPSG:4326", _WORLD_FOOTPRINT),
            license=_license(config),
            provenance_url=_PROVENANCE_URL,
            priority=20,
        ),
    )


def _intersecting_tile_origins(
    geojson: object,
    *,
    tile_size_degrees: int,
) -> tuple[tuple[int, int], ...]:
    concrete = shape(dict(geojson))  # type: ignore[arg-type]
    min_x, min_y, max_x, max_y = concrete.bounds
    if min_y < -90 or max_y > 90 or min_x < -180 or max_x > 180:
        raise RefinementValidationError("WorldCover AOI coordinates exceed WGS84 bounds")

    longitude_ranges = _longitude_ranges(concrete)
    latitudes = _origins(min_y, max_y, tile_size_degrees, lower=-90, upper=90)
    origins: set[tuple[int, int]] = set()
    for range_min, range_max in longitude_ranges:
        longitudes = _origins(
            range_min,
            range_max,
            tile_size_degrees,
            lower=-180,
            upper=180,
        )
        for latitude in latitudes:
            for longitude in longitudes:
                tile = box(
                    longitude,
                    latitude,
                    longitude + tile_size_degrees,
                    latitude + tile_size_degrees,
                )
                if tile.intersects(concrete) or len(longitude_ranges) > 1:
                    origins.add((latitude, longitude))
    return tuple(sorted(origins))


def _longitude_ranges(concrete: object) -> tuple[tuple[float, float], ...]:
    coordinates = tuple(_coordinate_pairs(concrete.__geo_interface__["coordinates"]))
    if not any(abs(left[0] - right[0]) > 180 for left, right in zip(coordinates, coordinates[1:])):
        bounds = concrete.bounds
        return ((float(bounds[0]), float(bounds[2])),)
    positive = [longitude for longitude, _ in coordinates if longitude >= 0]
    negative = [longitude for longitude, _ in coordinates if longitude < 0]
    if not positive or not negative:
        return ((float(concrete.bounds[0]), float(concrete.bounds[2])),)
    return ((min(positive), 180.0), (-180.0, max(negative)))


def _coordinate_pairs(value: object) -> Iterable[tuple[float, float]]:
    if (
        isinstance(value, (list, tuple))
        and len(value) >= 2
        and isinstance(value[0], (int, float))
        and isinstance(value[1], (int, float))
    ):
        yield float(value[0]), float(value[1])
        return
    if isinstance(value, (list, tuple)):
        for child in value:
            yield from _coordinate_pairs(child)


def _origins(
    minimum: float,
    maximum: float,
    step: int,
    *,
    lower: int,
    upper: int,
) -> tuple[int, ...]:
    first = max(lower, floor(minimum / step) * step)
    exclusive_maximum = maximum if maximum > minimum else minimum + 1e-12
    last = min(upper - step, floor((exclusive_maximum - 1e-12) / step) * step)
    return tuple(range(first, last + step, step)) if last >= first else ()


def _worldcover_tile_filename(latitude: int, longitude: int) -> str:
    latitude_label = f"{'N' if latitude >= 0 else 'S'}{abs(latitude):02d}"
    longitude_label = f"{'E' if longitude >= 0 else 'W'}{abs(longitude):03d}"
    return f"ESA_WorldCover_10m_2021_v200_{latitude_label}{longitude_label}_Map.tif"


def _supports_category(category_key: str) -> bool:
    if category_key == "surface":
        return True
    return any(
        node == category_key
        or node.startswith(f"{category_key}.")
        or category_key.startswith(f"{node}.")
        for node in _COMPATIBLE_NODES
    )


def _license(config: WorldCoverConfiguration) -> LicenseMetadata:
    return LicenseMetadata(
        license_id="CC-BY-4.0",
        official_url=_LICENSE_URL,
        attribution_text="Contains modified Copernicus Sentinel data (2021), processed by ESA WorldCover consortium.",
        citation="Zanaga et al. (2022), ESA WorldCover 10 m 2021 v200",
        provider="European Space Agency",
        product="ESA WorldCover",
        version=config.version,
        checked_at=date(2026, 8, 25),
        provenance_url=_PROVENANCE_URL,
        asset_fingerprints=(f"url:{config.base_url}",),
        commercial_use=True,
    )
