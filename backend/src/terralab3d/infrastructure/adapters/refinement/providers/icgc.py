"""ICGC Mapa de Cobertes del Sòl discovery from its official analytic GeoTIFF."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from shapely.geometry import shape

from terralab3d.domain.refinement.discovery import (
    DiscoveredRefinementProduct,
    DiscoveryRequest,
    RemoteAsset,
)
from terralab3d.domain.refinement.installations import (
    GeometryRecord,
    RefinementDataKind,
    RefinementProduct,
)
from terralab3d.domain.refinement.licensing import LicenseMetadata


_PROVENANCE_URL = (
    "https://www.icgc.cat/ca/Geoinformacio-i-mapes/Mapes/"
    "Mapa-de-cobertes-del-sol-de-Catalunya"
)
_LICENSE_URL = (
    "https://www.icgc.cat/ca/LICGC/Informacio-publica/Transparencia/"
    "Reutilitzacio-de-la-informacio"
)
_CATALONIA = {
    "type": "Polygon",
    "coordinates": (
        ((0.14, 40.46), (3.34, 40.46), (3.34, 42.87), (0.14, 42.87), (0.14, 40.46)),
    ),
}

# Official 41-class raster legend. Ambiguous mixed classes are deliberately
# mapped only to an unspecified parent instead of inventing a false leaf.
ICGC_MCSC_2024_TRANSLATION: dict[int, str] = {
    1: "agriculture.cropland.arable.annual_crop",
    2: "agriculture.cropland.arable.annual_crop",
    3: "agriculture.cropland.permanent_crop.vineyard",
    4: "agriculture.cropland.permanent_crop.olive_grove",
    5: "agriculture.cropland.permanent_crop.other",
    6: "agriculture.cropland.unspecified",
    7: "tree_cover.needleleaf",
    8: "tree_cover.broadleaf",
    9: "tree_cover.broadleaf",
    10: "low_vegetation.shrub.shrubland",
    11: "tree_cover.needleleaf",
    12: "tree_cover.broadleaf",
    13: "tree_cover.broadleaf",
    14: "low_vegetation.herbaceous.natural_grassland",
    15: "wetland.inland.forested_wetland",
    16: "bare_sparse.bare_soil",
    17: "bare_sparse.unspecified",
    18: "bare_sparse.unspecified",
    19: "bare_sparse.sand.beach",
    20: "wetland.unspecified",
    21: "artificial.built.urban_fabric",
    22: "artificial.built.urban_fabric",
    23: "artificial.built.residential",
    24: "artificial.built.unspecified",
    25: "artificial.built.residential",
    26: "artificial.artificial_green.urban_green",
    27: "artificial.industrial_commercial",
    28: "artificial.artificial_green.sport_leisure",
    29: "artificial.unspecified",
    30: "artificial.construction_site",
    31: "artificial.transport.road",
    32: "artificial.unspecified",
    33: "artificial.transport.airport",
    34: "artificial.transport.railway",
    35: "artificial.transport.port",
    36: "water.artificial.reservoir",
    37: "water.inland.standing_water",
    38: "water.inland.watercourse",
    39: "water.inland.standing_water",
    40: "water.artificial.canal",
    41: "water.marine.sea_ocean",
}
_COMPATIBLE_NODES = tuple(sorted(set(ICGC_MCSC_2024_TRANSLATION.values())))


@dataclass(frozen=True, slots=True)
class IcgcLandCoverConfiguration:
    asset_url: str = (
        "https://datacloud.icgc.cat/datacloud/cobertes-sol/tif_unzip/"
        "cobertes-sol-v1r0-2024.tif"
    )
    estimated_bytes: int = 1_786_008_665
    version: str = "2024-v1r0"


class IcgcLandCoverAdapter:
    """Return the current ICGC analytical raster when the AOI intersects Catalonia."""

    provider_id = "icgc-mcsc"

    def __init__(self, configuration: IcgcLandCoverConfiguration | None = None) -> None:
        self._configuration = configuration or IcgcLandCoverConfiguration()

    async def discover(
        self,
        request: DiscoveryRequest,
    ) -> tuple[DiscoveredRefinementProduct, ...]:
        if not _supports_category(request.category_key):
            return ()
        aoi = shape(dict(request.aoi_geojson))
        footprint = shape(_CATALONIA)
        if aoi.is_empty or not aoi.is_valid or not footprint.intersects(aoi):
            return ()
        config = self._configuration
        asset = RemoteAsset(
            asset_id=f"icgc-mcsc-{config.version}",
            download_url=config.asset_url,
            s3_path=None,
            footprint=_CATALONIA,
            order=0,
            estimated_bytes=config.estimated_bytes,
            checksum_algorithm=None,
            checksum_value=None,
            requires_authentication=False,
        )
        return (
            DiscoveredRefinementProduct(
                candidate_id=f"icgc-mcsc-{config.version}",
                provider_id=self.provider_id,
                provider="Institut Cartogràfic i Geològic de Catalunya",
                product="Mapa de Cobertes del Sòl de Catalunya",
                version=config.version,
                dataset_identifier="icgc-mcsc",
                compatible_tlst_nodes=_COMPATIBLE_NODES,
                footprint=_CATALONIA,
                resolution_m=1,
                temporal_start="2024-01-01",
                temporal_end="2024-12-31",
                format="GeoTIFF",
                estimated_bytes=config.estimated_bytes,
                license=_license(config),
                assets=(asset,),
                endpoint_verified=True,
                class_translation=ICGC_MCSC_2024_TRANSLATION,
                nodata_values=(0,),
            ),
        )


def icgc_refinement_products() -> tuple[RefinementProduct, ...]:
    config = IcgcLandCoverConfiguration()
    return (
        RefinementProduct(
            product_id="icgc-mcsc",
            resource_id="earth.refinement.icgc.mcsc",
            variant_id=config.version,
            provider="Institut Cartogràfic i Geològic de Catalunya",
            product="Mapa de Cobertes del Sòl de Catalunya",
            version=config.version,
            tlst_nodes=_COMPATIBLE_NODES,
            data_kind=RefinementDataKind.RASTER,
            original_crs="EPSG:25831",
            planned_geometry=GeometryRecord("EPSG:4326", _CATALONIA),
            license=_license(config),
            provenance_url=_PROVENANCE_URL,
            priority=0,
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


def _license(config: IcgcLandCoverConfiguration) -> LicenseMetadata:
    return LicenseMetadata(
        license_id="CC-BY-4.0",
        official_url=_LICENSE_URL,
        attribution_text=(
            "Mapa derivat del Mapa de Cobertes del Sòl de Catalunya de l'ICGC, "
            "utilitzat sota una llicència CC BY 4.0."
        ),
        citation="Institut Cartogràfic i Geològic de Catalunya, MCSC 2024",
        provider="Institut Cartogràfic i Geològic de Catalunya",
        product="Mapa de Cobertes del Sòl de Catalunya",
        version=config.version,
        checked_at=date(2026, 8, 25),
        provenance_url=_PROVENANCE_URL,
        asset_fingerprints=(f"url:{config.asset_url}",),
        commercial_use=True,
    )
