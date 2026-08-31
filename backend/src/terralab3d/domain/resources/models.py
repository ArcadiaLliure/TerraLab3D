"""Models de domini tipats per a la capacitat de recursos.

Aquesta capa encapsula l'estat d'instal·lació (ResourceInstallState),
els descriptors estàtics (ResourceDescriptor), i les variants associades (ResourceVariant).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Literal, TypeAlias

from terralab3d.domain.identifiers import ResourceId, VariantId


ResourceMetadataValue: TypeAlias = str | int | float | bool
ResourceMetadata: TypeAlias = tuple[tuple[str, ResourceMetadataValue], ...]


class AcquisitionKind(str, Enum):
    STATIC_FILE = "STATIC_FILE"
    HTTP_BUNDLE = "HTTP_BUNDLE"
    TAP_QUERY = "TAP_QUERY"
    GENERATED_DATASET = "GENERATED_DATASET"
    PARAMETRIC_DOWNLOAD = "PARAMETRIC_DOWNLOAD"
    EXTERNAL_FILE = "EXTERNAL_FILE"


class ResourceInstallState(str, Enum):
    NOT_INSTALLED = "NOT_INSTALLED"
    PARTIAL = "PARTIAL"
    QUEUED = "QUEUED"
    AUTHENTICATING = "AUTHENTICATING"
    DOWNLOADING = "DOWNLOADING"
    PAUSED = "PAUSED"
    VERIFYING = "VERIFYING"
    PROCESSING = "PROCESSING"
    READY = "READY"
    INVALID = "INVALID"
    UPDATE_AVAILABLE = "UPDATE_AVAILABLE"
    ERROR = "ERROR"


@dataclass(frozen=True, slots=True)
class ChecksumSpec:
    algorithm: Literal["md5", "sha256"]
    value: str

    def to_dict(self) -> dict[str, str]:
        return {"algorithm": self.algorithm, "value": self.value}


@dataclass(frozen=True, slots=True)
class ResourceVariant:
    id: VariantId
    title: str
    source_url: str | None = None
    source_urls: tuple[str, ...] = field(default_factory=tuple)
    format: str | None = None
    mime_type: str | None = None
    width: int | None = None
    height: int | None = None
    published_size_label: str | None = None
    expected_bytes: int | None = None
    checksum: ChecksumSpec | None = None
    priority: int = 0
    metadata: ResourceMetadata = field(default_factory=tuple)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "sourceUrl": self.source_url,
            "sourceUrls": list(self.source_urls),
            "format": self.format,
            "mimeType": self.mime_type,
            "width": self.width,
            "height": self.height,
            "publishedSizeLabel": self.published_size_label,
            "expectedBytes": self.expected_bytes,
            "checksum": self.checksum.to_dict() if self.checksum else None,
            "metadata": dict(self.metadata),
        }


class ResourceDomain(str, Enum):
    SKY = "sky"
    EARTH = "earth"


class ResourceCategory(str, Enum):
    SOLAR_SYSTEM = "solar_system"
    DEEP_SKY = "deep_sky"
    ELEVATION = "elevation"
    LAND_COVER = "land_cover"
    LIGHT_POLLUTION = "light_pollution"




@dataclass(frozen=True, slots=True)
class ResourceDescriptor:
    id: ResourceId
    name: str
    description: str
    domain: ResourceDomain
    category: ResourceCategory
    provider: str
    acquisition_kind: AcquisitionKind
    citation: str
    license: str
    original_source_url: str | None = None
    direct_url: str | None = None
    variants: tuple[ResourceVariant, ...] = field(default_factory=tuple)
    credits: tuple[str, ...] = field(default_factory=tuple)
    dependencies: tuple[ResourceId, ...] = field(default_factory=tuple)
    metadata: ResourceMetadata = field(default_factory=tuple)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "domain": self.domain.value,
            "category": self.category.value,
            "provider": self.provider,
            "acquisitionKind": self.acquisition_kind.value,
            "citation": self.citation,
            "license": self.license,
            "originalSourceUrl": self.original_source_url,
            "directUrl": self.direct_url,
            "variants": [v.to_dict() for v in self.variants],
            "credits": list(self.credits),
            "dependencies": list(self.dependencies),
            "metadata": dict(self.metadata),
        }


@dataclass(frozen=True, slots=True)
class DownloadAssetProgress:
    file_name: str
    downloaded_bytes: int
    total_bytes: int | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "fileName": self.file_name,
            "downloadedBytes": self.downloaded_bytes,
            "totalBytes": self.total_bytes,
        }


@dataclass(frozen=True, slots=True)
class DownloadJobSnapshot:
    job_id: str
    resource_id: ResourceId
    variant_id: VariantId | None
    state: ResourceInstallState
    downloaded_bytes: int
    total_bytes: int | None
    progress: float | None
    current_file: str | None
    error_code: str | None
    error_message: str | None
    asset_progress: tuple[DownloadAssetProgress, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "jobId": self.job_id,
            "resourceId": self.resource_id,
            "variantId": self.variant_id,
            "state": self.state.value,
            "downloadedBytes": self.downloaded_bytes,
            "totalBytes": self.total_bytes,
            "progress": self.progress,
            "currentFile": self.current_file,
            "errorCode": self.error_code,
            "errorMessage": self.error_message,
            "assetProgress": [item.to_dict() for item in self.asset_progress],
        }
