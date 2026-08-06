"""Models de domini tipats per a la capacitat datasets, descàrregues i validació."""


from dataclasses import dataclass
from enum import Enum

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
