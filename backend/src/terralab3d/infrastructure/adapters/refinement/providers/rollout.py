"""Auditable rollout matrix for automatic TLST refinement providers."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class ProviderRolloutState(str, Enum):
    ENABLED = "enabled"
    DISABLED = "disabled"


@dataclass(frozen=True, slots=True)
class ProviderRollout:
    provider_key: str
    datasets: tuple[str, ...]
    state: ProviderRolloutState
    license_status: str
    tlst_families: tuple[str, ...]
    reason: str


def refinement_provider_rollout() -> tuple[ProviderRollout, ...]:
    """Return explicit states; disabled integrations never leak into discovery."""

    return (
        ProviderRollout(
            "icgc-mcsc",
            ("Mapa de Cobertes del Sòl de Catalunya 2024",),
            ProviderRolloutState.ENABLED,
            "CC-BY-4.0 verified",
            ("artificial", "agriculture", "tree_cover", "low_vegetation", "wetland", "bare_sparse", "water"),
            "Official analytic GeoTIFF and 41-class legend verified.",
        ),
        ProviderRollout(
            "icgc-rtt",
            ("Referencial Topogràfic Territorial",),
            ProviderRolloutState.DISABLED,
            "CC-BY-4.0 verified",
            ("artificial", "transport", "water"),
            "No stable unattended AOI download contract and class-field mapping is frozen yet.",
        ),
        ProviderRollout(
            "copernicus-corine",
            ("CORINE Land Cover 2018 vector",),
            ProviderRolloutState.ENABLED,
            "Copernicus-CLMS verified",
            ("artificial", "agriculture", "tree_cover", "low_vegetation", "wetland", "bare_sparse", "water", "snow_ice"),
            "Official EEA ArcGIS layer, AOI query, pagination and 44-class mapping verified.",
        ),
        ProviderRollout(
            "copernicus-clcplus-backbone",
            ("CLCplus Backbone 2023",),
            ProviderRolloutState.DISABLED,
            "Copernicus-CLMS verified",
            ("surface",),
            "Download packaging and exact class translation have not passed an official smoke test.",
        ),
        ProviderRollout(
            "copernicus-urban-impervious-bbh",
            ("Urban Atlas", "Imperviousness", "Built-Up", "Building Block Height"),
            ProviderRolloutState.DISABLED,
            "Copernicus-CLMS verified",
            ("artificial",),
            "Product-specific AOI adapters and categorical thresholds are not implemented.",
        ),
        ProviderRollout(
            "copernicus-clms-grassland",
            ("GRA 10m yearly",),
            ProviderRolloutState.ENABLED,
            "Copernicus-CLMS verified",
            ("low_vegetation.herbaceous",),
            "Official OData identifier, binary legend and live endpoint verified.",
        ),
        ProviderRollout(
            "eu-hydro-coastal-riparian",
            ("EU-Hydro", "Coastal Zones", "Riparian Zones"),
            ProviderRolloutState.DISABLED,
            "Copernicus products verified; EU-Hydro lineage requires product review",
            ("water", "wetland", "bare_sparse"),
            "No common stable direct AOI contract; general water/coastal coverage comes from enabled CORINE and global CLMS layers.",
        ),
        ProviderRollout(
            "copernicus-clms-snow",
            ("Snow Phenology Sentinel-2 20m yearly", "CORINE glacier class"),
            ProviderRolloutState.ENABLED,
            "Copernicus-CLMS verified",
            ("snow_ice.seasonal", "snow_ice.permanent"),
            "Official duration band and endpoint verified; 365-366 day pixels remain permanent snow.",
        ),
        ProviderRollout(
            "inspire-hvd-buildings",
            ("INSPIRE/HVD Buildings",),
            ProviderRolloutState.DISABLED,
            "review each national endpoint",
            ("artificial.built",),
            "Federated national services do not share one endpoint or one reusable license record.",
        ),
        ProviderRollout(
            "inspire-hvd-transport",
            ("INSPIRE/HVD Transport Networks",),
            ProviderRolloutState.DISABLED,
            "review each national endpoint",
            ("artificial.transport",),
            "Federated national services require per-country schema and license adapters.",
        ),
        ProviderRollout(
            "open-maps-for-europe-2",
            ("Open Maps for Europe 2",),
            ProviderRolloutState.DISABLED,
            "product lineage review required",
            ("artificial", "transport", "water"),
            "Direct AOI assets and upstream attribution lineage are not frozen per product.",
        ),
        ProviderRollout(
            "copernicus-clms-thematic",
            ("Crop Types", "Tree Cover Density", "Dominant Leaf Type", "Forest Type"),
            ProviderRolloutState.ENABLED,
            "Copernicus-CLMS verified",
            ("agriculture.cropland", "tree_cover"),
            "Official OData identifiers, legends, fixtures and live endpoints verified.",
        ),
        ProviderRollout(
            "copernicus-global-dynamic",
            ("Global Dynamic Land Cover 10m 2020 beta",),
            ProviderRolloutState.ENABLED,
            "Copernicus-CLMS verified",
            ("surface",),
            "Official global fallback identifier, 11-class legend and live endpoint verified.",
        ),
        ProviderRollout(
            "nasa-usgs-fallback",
            ("NASA/USGS global and national land-cover products",),
            ProviderRolloutState.DISABLED,
            "public-domain candidates; dataset-specific review required",
            ("surface",),
            "No single selected product improves the enabled 10m global fallback without adding coarser duplicate semantics.",
        ),
        ProviderRollout(
            "copernicus-water-wetness",
            ("HRL Water and Wetness 2018",),
            ProviderRolloutState.ENABLED,
            "Copernicus-CLMS verified",
            ("water", "wetland"),
            "Official raw 10 m ImageServer export, legend, tiling and live endpoint verified.",
        ),
    )
