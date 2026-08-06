"""Models de domini tipats per a la capacitat recursos."""


from dataclasses import dataclass
from enum import Enum
from terralab3d.domain.identifiers import ResourceId

class ResourceStatus(str, Enum):
    MISSING = "missing"
    QUEUED = "queued"
    LOADING = "loading"
    READY = "ready"
    FAILED = "failed"

@dataclass(frozen=True, slots=True)
class DatasetState:
    resource_id: ResourceId
    status: ResourceStatus
    version: int | None
    progress_fraction: float | None
    message: str | None
