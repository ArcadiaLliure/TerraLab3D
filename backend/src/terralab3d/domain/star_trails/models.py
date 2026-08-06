"""Models de domini tipats per a la capacitat traces circumpolars."""


from dataclasses import dataclass
from datetime import datetime
from terralab3d.domain.identifiers import ResourceId

@dataclass(frozen=True, slots=True)
class StarTrailRequest:
    start_utc: datetime
    end_utc: datetime
    sample_count: int
    magnitude_limit: float

@dataclass(frozen=True, slots=True)
class StarTrailGeometry:
    resource_id: ResourceId
    version: int
    segment_count: int
