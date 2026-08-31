"""Persistent refinement installation and product contracts."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from types import MappingProxyType
from typing import Mapping

from .errors import RefinementValidationError
from .licensing import LicenseMetadata
from .states import SpatialCoverageState


class RefinementDataKind(str, Enum):
    RASTER = "raster"
    VECTOR = "vector"


class TechnicalResourceState(str, Enum):
    QUEUED = "QUEUED"
    AUTHENTICATING = "AUTHENTICATING"
    DOWNLOADING = "DOWNLOADING"
    VERIFYING = "VERIFYING"
    PROCESSING = "PROCESSING"
    READY = "READY"
    ERROR = "ERROR"
    CANCELLED = "CANCELLED"


class CoverageVerificationMethod(str, Enum):
    RASTER_VALID_MASK = "raster_valid_mask"
    VECTOR_GEOMETRY = "vector_geometry"
    METADATA_FOOTPRINT = "metadata_footprint"


@dataclass(frozen=True, slots=True)
class GeometryRecord:
    crs: str
    geojson: Mapping[str, object]

    def __post_init__(self) -> None:
        if not self.crs.strip():
            raise RefinementValidationError("Geometry record CRS is required")
        geometry_type = self.geojson.get("type")
        if not isinstance(geometry_type, str) or not geometry_type:
            raise RefinementValidationError("Geometry record requires valid GeoJSON")
        normalized = json.loads(json.dumps(dict(self.geojson)))
        object.__setattr__(self, "geojson", MappingProxyType(normalized))


@dataclass(frozen=True, slots=True)
class RefinementProduct:
    product_id: str
    resource_id: str
    variant_id: str
    provider: str
    product: str
    version: str
    tlst_nodes: tuple[str, ...]
    data_kind: RefinementDataKind
    original_crs: str
    planned_geometry: GeometryRecord
    license: LicenseMetadata
    provenance_url: str
    priority: int = 0

    def __post_init__(self) -> None:
        required = (
            self.product_id,
            self.resource_id,
            self.variant_id,
            self.provider,
            self.product,
            self.version,
            self.original_crs,
            self.provenance_url,
        )
        if any(not value.strip() for value in required) or not self.tlst_nodes:
            raise RefinementValidationError("Refinement product metadata is incomplete")


@dataclass(frozen=True, slots=True)
class RefinementInstallation:
    installation_id: str
    resource_id: str
    variant_id: str
    provider: str
    product: str
    version: str
    tlst_nodes: tuple[str, ...]
    data_kind: RefinementDataKind
    local_path: str
    planned_geometry: GeometryRecord
    verified_geometry: GeometryRecord | None
    original_crs: str
    created_at: datetime
    installed_at: datetime | None
    technical_state: TechnicalResourceState
    spatial_state: SpatialCoverageState
    job_id: str | None
    license: LicenseMetadata
    provenance_url: str
    file_fingerprints: tuple[str, ...] = field(default_factory=tuple)
    verification_method: CoverageVerificationMethod | None = None
    aoi_id: str = "default"

    def __post_init__(self) -> None:
        required = (
            self.installation_id,
            self.resource_id,
            self.variant_id,
            self.provider,
            self.product,
            self.version,
            self.local_path,
            self.original_crs,
            self.provenance_url,
            self.aoi_id,
        )
        if any(not value.strip() for value in required) or not self.tlst_nodes:
            raise RefinementValidationError("Refinement installation metadata is incomplete")
        if self.technical_state is TechnicalResourceState.READY:
            if self.verified_geometry is None or self.installed_at is None:
                raise RefinementValidationError(
                    "A READY refinement requires verified geometry and installation date"
                )
            if not self.file_fingerprints or self.verification_method is None:
                raise RefinementValidationError(
                    "A READY refinement requires fingerprints and a verification method"
                )
