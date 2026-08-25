"""Domain DTOs for streamed categorical surface layers."""

from dataclasses import dataclass

from terralab3d.domain.surface.tlst import (
    ClassificationStatus,
    QualifierAssignment,
    SampleValidity,
)


@dataclass(frozen=True, slots=True)
class LandCoverTileRequest:
    min_x: float
    min_y: float
    max_x: float
    max_y: float
    resolution: float
    crs: str
    source_mode: str
    source_id: str | None


@dataclass(frozen=True, slots=True)
class LandCoverProvenance:
    source_id: str
    source_name: str
    generation: int
    scheme_key: str
    scheme_version: str
    taxonomy_key: str
    taxonomy_version: str
    source_dtype: str
    mapping_revision: str = "1"


@dataclass(frozen=True, slots=True)
class LandCoverLegendEntry:
    source_code: int
    source_label: str
    color_rgba: tuple[int, int, int, int]
    source_label_key: str | None
    sample_validity: SampleValidity | None
    classification_status: ClassificationStatus | None
    category_key: str | None
    category_label_key: str | None
    category_label: str | None
    qualifiers: tuple[QualifierAssignment, ...]
    source_value: int | str | None = None
    mapping_kind: str = "observation_state"
    resolved_path: tuple[str, ...] = ()
    semantic_depth: int | None = None
    unresolved_children: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class LandCoverLegend:
    scheme_key: str
    scheme_version: str
    source_name: str
    taxonomy_key: str
    taxonomy_version: str
    entries: tuple[LandCoverLegendEntry, ...]
    mapping_revision: str = "1"


@dataclass(frozen=True, slots=True)
class LandCoverTile:
    resource_id: str
    provenance: LandCoverProvenance
    min_x: float
    min_y: float
    max_x: float
    max_y: float
    width: int
    height: int
    resolution: float
    crs: str
    valid_pixels: int
    source_code_buffer: bytes
    sample_validity_buffer: bytes
    buffer_dtype: str = "uint16"
    validity_encoding: str = "tlst-sample-validity-2bit-v1"

    @property
    def binary_payload(self) -> bytes:
        return self.source_code_buffer + self.sample_validity_buffer

    @property
    def byte_size(self) -> int:
        return len(self.source_code_buffer) + len(self.sample_validity_buffer)
