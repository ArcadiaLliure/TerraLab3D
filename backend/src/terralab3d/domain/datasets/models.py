"""Models de domini tipats per a la capacitat datasets, descàrregues i validació."""


import math
from dataclasses import dataclass
from enum import Enum


class SourceRole(str, Enum):
    """Paper estricte d'una font dins del pipeline territorial TLST."""

    BASE_CATEGORICAL = "BASE_CATEGORICAL"
    SEMANTIC_REFINEMENT = "SEMANTIC_REFINEMENT"
    CONTEXT = "CONTEXT"
    AUTHORITATIVE_GEOMETRY = "AUTHORITATIVE_GEOMETRY"


@dataclass(frozen=True, slots=True)
class FontTerritorial:
    """Configuracio immutable de participacio en la interpretacio territorial.

    ``installed`` descriu disponibilitat tecnica. ``enabled`` es una decisio
    semantica independent: una font instal.lada pot quedar ignorada sense
    perdre fitxers, procedencia ni metadades.
    """

    stable_id: str
    source_role: SourceRole
    installed: bool
    enabled: bool
    priority: int
    spatial_resolution_m: float | None
    available: bool = True

    def __post_init__(self) -> None:
        if not self.stable_id.strip():
            raise ValueError("La font territorial necessita un stable_id")
        if not isinstance(self.source_role, SourceRole):
            raise ValueError("source_role ha de ser un SourceRole")
        if (
            not isinstance(self.installed, bool)
            or not isinstance(self.enabled, bool)
            or not isinstance(self.available, bool)
        ):
            raise ValueError("installed, available i enabled han de ser booleans")
        if isinstance(self.priority, bool) or not isinstance(self.priority, int):
            raise ValueError("priority ha de ser un enter")
        if (
            self.spatial_resolution_m is not None
            and (
                isinstance(self.spatial_resolution_m, bool)
                or not isinstance(self.spatial_resolution_m, (int, float))
                or not math.isfinite(float(self.spatial_resolution_m))
                or self.spatial_resolution_m <= 0
            )
        ):
            raise ValueError("spatial_resolution_m ha de ser positiva i finita")
        if (
            self.source_role is SourceRole.BASE_CATEGORICAL
            and self.spatial_resolution_m is None
        ):
            raise ValueError("Una BASE_CATEGORICAL necessita spatial_resolution_m")

    @property
    def activa(self) -> bool:
        return self.installed and self.available and self.enabled


class DatasetRequirement(str, Enum):
    REQUIRED = "required"
    OPTIONAL = "optional"
    FALLBACK = "fallback"


@dataclass(frozen=True, slots=True)
class DatasetManifest:
    dataset_id: str
    version: str
    checksum: str
    byte_size: int
    requirement: DatasetRequirement


@dataclass(frozen=True, slots=True)
class DatasetInstallation:
    dataset_id: str
    version: str | None
    installed: bool
    valid: bool
