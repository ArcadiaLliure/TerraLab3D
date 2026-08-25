"""Copernicus CLMS discovery through the public CDSE OData catalogue."""

from __future__ import annotations

import asyncio
import json
import time
from dataclasses import dataclass
from datetime import date
from typing import Any

import aiohttp
from shapely.geometry import shape

from terralab3d.domain.refinement.discovery import (
    DiscoveredRefinementProduct,
    DiscoveryRequest,
    RemoteAsset,
)
from terralab3d.domain.refinement.errors import RefinementError, RefinementValidationError
from terralab3d.domain.refinement.licensing import LicenseMetadata


class ClmsDiscoveryError(RefinementError):
    """CLMS catalogue discovery failed after bounded retries."""


@dataclass(frozen=True, slots=True)
class ClmsProviderConfiguration:
    catalogue_url: str = "https://catalogue.dataspace.copernicus.eu/odata/v1/Products"
    download_url: str = "https://download.dataspace.copernicus.eu/odata/v1"
    timeout_seconds: float = 30.0
    retry_count: int = 2
    retry_backoff_seconds: float = 0.25
    cache_ttl_seconds: float = 300.0
    page_size: int = 100
    max_pages: int = 20

    def __post_init__(self) -> None:
        if self.timeout_seconds <= 0 or self.retry_count < 0 or self.page_size <= 0:
            raise RefinementValidationError("Invalid CLMS provider configuration")


@dataclass(frozen=True, slots=True)
class _ClmsDataset:
    dataset_identifier: str
    product: str
    version: str
    resolution_m: float
    compatible_nodes: tuple[str, ...]
    endpoint_verified: bool = True
    qualifier_key: str | None = None


_CLMS_DATASETS = (
    _ClmsDataset(
        "clms_vlcc_crop-types_europe_10m_yearly_v1",
        "High Resolution Layer Crop Types",
        "v1",
        10,
        ("agriculture.cropland",),
    ),
    _ClmsDataset(
        "clms_vlcc_tree-cover-density_europe_10m_yearly_v1",
        "High Resolution Layer Tree Cover Density",
        "v1",
        10,
        ("tree_cover",),
        qualifier_key="canopy_cover",
    ),
    _ClmsDataset(
        "clms_vlcc_dominant-leaf-type_europe_10m_yearly_v1",
        "High Resolution Layer Dominant Leaf Type",
        "v1",
        10,
        ("tree_cover.broadleaf", "tree_cover.needleleaf"),
    ),
    _ClmsDataset(
        "clms_vlcc_forest-type_europe_10m_3yearly_v1",
        "High Resolution Layer Forest Type",
        "v1",
        10,
        (
            "tree_cover.broadleaf",
            "tree_cover.needleleaf",
            "tree_cover.mixed",
            "tree_cover.unspecified",
        ),
    ),
    _ClmsDataset(
        "clms_hrl_water-wetness_europe_10m_2018_v1",
        "High Resolution Layer Water and Wetness",
        "2018-v1",
        10,
        ("water", "wetland"),
        endpoint_verified=False,
    ),
)


class ClmsODataAdapter:
    provider_id = "copernicus-clms"

    def __init__(self, configuration: ClmsProviderConfiguration | None = None) -> None:
        self._configuration = configuration or ClmsProviderConfiguration()
        self._cache: dict[str, tuple[float, tuple[DiscoveredRefinementProduct, ...]]] = {}

    async def discover(
        self,
        request: DiscoveryRequest,
    ) -> tuple[DiscoveredRefinementProduct, ...]:
        datasets = tuple(
            dataset
            for dataset in _CLMS_DATASETS
            if _dataset_supports_category(dataset, request.category_key)
        )
        if not datasets:
            return ()
        aoi = shape(dict(request.aoi_geojson))
        if aoi.is_empty or not aoi.is_valid:
            raise RefinementValidationError("CLMS discovery AOI is invalid")
        cache_key = json.dumps(
            [request.category_key, dict(request.aoi_geojson)],
            sort_keys=True,
            separators=(",", ":"),
        )
        cached = self._cache.get(cache_key)
        now = time.monotonic()
        if cached is not None and now - cached[0] <= self._configuration.cache_ttl_seconds:
            return cached[1]

        timeout = aiohttp.ClientTimeout(total=self._configuration.timeout_seconds)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            batches = await asyncio.gather(
                *(self._discover_dataset(session, dataset, aoi.wkt) for dataset in datasets)
            )
        candidates = tuple(
            sorted(
                (candidate for batch in batches for candidate in batch),
                key=lambda item: (item.dataset_identifier, item.temporal_start or "", item.candidate_id),
            )
        )
        self._cache[cache_key] = (now, candidates)
        return candidates

    async def _discover_dataset(
        self,
        session: aiohttp.ClientSession,
        dataset: _ClmsDataset,
        aoi_wkt: str,
    ) -> tuple[DiscoveredRefinementProduct, ...]:
        filters = (
            "Collection/Name eq 'CLMS' and "
            "Attributes/OData.CSC.StringAttribute/any(att:att/Name eq "
            f"'datasetIdentifier' and att/OData.CSC.StringAttribute/Value eq '{dataset.dataset_identifier}') "
            f"and OData.CSC.Intersects(area=geography'SRID=4326;{aoi_wkt}')"
        )
        url: str | None = self._configuration.catalogue_url
        params: dict[str, str] | None = {
            "$count": "true",
            "$top": str(self._configuration.page_size),
            "$expand": "Attributes",
            "$filter": filters,
        }
        records: list[dict[str, Any]] = []
        page = 0
        while url and page < self._configuration.max_pages:
            payload = await self._get_json(session, url, params=params)
            values = payload.get("value", [])
            if not isinstance(values, list):
                raise ClmsDiscoveryError("CLMS OData response has no value array")
            records.extend(item for item in values if isinstance(item, dict))
            next_link = payload.get("@odata.nextLink")
            url = str(next_link) if next_link else None
            params = None
            page += 1
        return tuple(self._parse_record(dataset, record) for record in records)

    async def _get_json(
        self,
        session: aiohttp.ClientSession,
        url: str,
        *,
        params: dict[str, str] | None,
    ) -> dict[str, Any]:
        last_error: Exception | None = None
        for attempt in range(self._configuration.retry_count + 1):
            try:
                async with session.get(url, params=params) as response:
                    if response.status in {429, 500, 502, 503, 504}:
                        raise ClmsDiscoveryError(f"Temporary CLMS HTTP {response.status}")
                    if response.status != 200:
                        text = await response.text()
                        raise ClmsDiscoveryError(
                            f"CLMS HTTP {response.status}: {text[:200]}"
                        )
                    payload = await response.json()
                    if not isinstance(payload, dict):
                        raise ClmsDiscoveryError("CLMS response is not a JSON object")
                    return payload
            except (aiohttp.ClientError, asyncio.TimeoutError, ClmsDiscoveryError) as exc:
                last_error = exc
                if attempt >= self._configuration.retry_count:
                    break
                await asyncio.sleep(
                    self._configuration.retry_backoff_seconds * (2**attempt)
                )
        raise ClmsDiscoveryError("CLMS catalogue request failed after retries") from last_error

    def _parse_record(
        self,
        dataset: _ClmsDataset,
        record: dict[str, Any],
    ) -> DiscoveredRefinementProduct:
        product_id = str(record.get("Id", "")).strip()
        footprint = record.get("GeoFootprint")
        if not product_id or not isinstance(footprint, dict):
            raise ClmsDiscoveryError("CLMS product lacks id or GeoFootprint")
        attributes = {
            str(item.get("Name")): item.get("Value")
            for item in record.get("Attributes", [])
            if isinstance(item, dict) and item.get("Name")
        }
        checksum_algorithm, checksum_value = _preferred_checksum(record.get("Checksum"))
        temporal = record.get("ContentDate")
        temporal = temporal if isinstance(temporal, dict) else {}
        content_length = record.get("ContentLength")
        asset = RemoteAsset(
            asset_id=product_id,
            download_url=(
                f"{self._configuration.download_url}/Products({product_id})/$value"
            ),
            s3_path=str(record["S3Path"]) if record.get("S3Path") else None,
            footprint=footprint,
            order=0,
            estimated_bytes=int(content_length) if content_length is not None else None,
            checksum_algorithm=checksum_algorithm,
            checksum_value=checksum_value,
            requires_authentication=True,
        )
        license_metadata = _clms_license(dataset, product_id)
        return DiscoveredRefinementProduct(
            candidate_id=product_id,
            provider_id=self.provider_id,
            provider="Copernicus Land Monitoring Service",
            product=dataset.product,
            version=str(attributes.get("productVersion") or dataset.version),
            dataset_identifier=dataset.dataset_identifier,
            compatible_tlst_nodes=dataset.compatible_nodes,
            footprint=footprint,
            resolution_m=dataset.resolution_m,
            temporal_start=str(temporal.get("Start")) if temporal.get("Start") else None,
            temporal_end=str(temporal.get("End")) if temporal.get("End") else None,
            format=str(attributes.get("fileFormat") or record.get("ContentType") or "unknown"),
            estimated_bytes=asset.estimated_bytes,
            license=license_metadata,
            assets=(asset,),
            endpoint_verified=dataset.endpoint_verified,
            qualifier_key=dataset.qualifier_key,
        )


def _dataset_supports_category(dataset: _ClmsDataset, category_key: str) -> bool:
    return any(
        node == category_key
        or node.startswith(f"{category_key}.")
        or category_key.startswith(f"{node}.")
        for node in dataset.compatible_nodes
    )


def _preferred_checksum(value: object) -> tuple[str | None, str | None]:
    if not isinstance(value, list):
        return None, None
    checksums = {
        str(item.get("Algorithm", "")).lower(): str(item.get("Value", ""))
        for item in value
        if isinstance(item, dict)
    }
    for algorithm in ("sha256", "md5"):
        if checksums.get(algorithm):
            return algorithm, checksums[algorithm]
    return None, None


def _clms_license(dataset: _ClmsDataset, asset_id: str) -> LicenseMetadata:
    return LicenseMetadata(
        license_id="copernicus-clms",
        official_url="https://land.copernicus.eu/en/faq/data-use-terms-and-conditions",
        attribution_text="Contains modified Copernicus Service information (2026)",
        citation="Copernicus Land Monitoring Service",
        provider="Copernicus Land Monitoring Service",
        product=dataset.product,
        version=dataset.version,
        checked_at=date(2026, 8, 25),
        provenance_url=(
            "https://documentation.dataspace.copernicus.eu/Data/"
            "CopernicusServices/CLMS.html"
        ),
        asset_fingerprints=(f"cdse-product:{asset_id}",),
        commercial_use=True,
    )
