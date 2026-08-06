"""Models de domini tipats per a la capacitat observador."""


from dataclasses import dataclass
from terralab3d.domain.identifiers import ObserverId

@dataclass(frozen=True, slots=True)
class GeoLocation:
    latitude_deg: float
    longitude_deg: float
    elevation_m: float | None = None

@dataclass(frozen=True, slots=True)
class ObserverProfile:
    observer_id: ObserverId
    location: GeoLocation
    height_offset_m: float = 0.0
