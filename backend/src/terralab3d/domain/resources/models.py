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
            "format": self.format,
            "mimeType": self.mime_type,
            "width": self.width,
            "height": self.height,
            "publishedSizeLabel": self.published_size_label,
            "expectedBytes": self.expected_bytes,
            "checksum": self.checksum.to_dict() if self.checksum else None,
            "metadata": dict(self.metadata),
        }


@dataclass(frozen=True, slots=True)
class ResourceDescriptor:
    id: ResourceId
    title: str
    provider: str
    acquisition_kind: AcquisitionKind
    source_page_url: str | None = None
    variants: tuple[ResourceVariant, ...] = field(default_factory=tuple)
    credits: tuple[str, ...] = field(default_factory=tuple)
    license: str | None = None
    dependencies: tuple[ResourceId, ...] = field(default_factory=tuple)
    metadata: ResourceMetadata = field(default_factory=tuple)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "provider": self.provider,
            "acquisitionKind": self.acquisition_kind.value,
            "sourcePageUrl": self.source_page_url,
            "variants": [v.to_dict() for v in self.variants],
            "credits": list(self.credits),
            "license": self.license,
            "dependencies": list(self.dependencies),
            "metadata": dict(self.metadata),
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
        }
