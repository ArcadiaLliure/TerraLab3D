"""Provider-neutral discovery results and frozen download assets."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Mapping

from .errors import RefinementValidationError
from .licensing import LicenseMetadata


@dataclass(frozen=True, slots=True)
class DiscoveryRequest:
    request_id: str
    revision: int
    category_key: str
    aoi_geojson: Mapping[str, object]

    def __post_init__(self) -> None:
        if not self.request_id.strip() or self.revision < 0 or not self.category_key.strip():
            raise RefinementValidationError("Discovery request metadata is invalid")
        geometry_type = self.aoi_geojson.get("type")
        if geometry_type not in {"Polygon", "MultiPolygon"}:
            raise RefinementValidationError("Discovery AOI must be a Polygon or MultiPolygon")
        normalized = json.loads(json.dumps(dict(self.aoi_geojson)))
        object.__setattr__(self, "aoi_geojson", MappingProxyType(normalized))


@dataclass(frozen=True, slots=True)
class RemoteAsset:
    asset_id: str
    download_url: str
    s3_path: str | None
    footprint: Mapping[str, object]
    order: int
    estimated_bytes: int | None
    checksum_algorithm: str | None
    checksum_value: str | None
    requires_authentication: bool

    def __post_init__(self) -> None:
        if not self.asset_id.strip() or not self.download_url.strip() or self.order < 0:
            raise RefinementValidationError("Remote asset metadata is invalid")
        normalized = json.loads(json.dumps(dict(self.footprint)))
        object.__setattr__(self, "footprint", MappingProxyType(normalized))


@dataclass(frozen=True, slots=True)
class DiscoveredRefinementProduct:
    candidate_id: str
    provider_id: str
    provider: str
    product: str
    version: str
    dataset_identifier: str
    compatible_tlst_nodes: tuple[str, ...]
    footprint: Mapping[str, object]
    resolution_m: float
    temporal_start: str | None
    temporal_end: str | None
    format: str
    estimated_bytes: int | None
    license: LicenseMetadata
    assets: tuple[RemoteAsset, ...]
    endpoint_verified: bool
    qualifier_key: str | None = None
    class_translation: Mapping[int, str] = field(default_factory=dict)
    nodata_values: tuple[int, ...] = ()

    def __post_init__(self) -> None:
        if not self.candidate_id.strip() or not self.assets:
            raise RefinementValidationError("Discovered product requires an id and assets")
        normalized = json.loads(json.dumps(dict(self.footprint)))
        object.__setattr__(self, "footprint", MappingProxyType(normalized))
        object.__setattr__(
            self,
            "class_translation",
            MappingProxyType(dict(self.class_translation)),
        )


@dataclass(frozen=True, slots=True)
class ProviderDiscoveryFailure:
    provider_id: str
    code: str
    message: str


@dataclass(frozen=True, slots=True)
class DiscoveryResult:
    request_id: str
    revision: int
    candidates: tuple[DiscoveredRefinementProduct, ...]
    failures: tuple[ProviderDiscoveryFailure, ...] = ()
