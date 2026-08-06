"""Models de domini tipats per a la capacitat elevacions i DEM."""


from dataclasses import dataclass
from terralab3d.domain.observer.models import GeoLocation

@dataclass(frozen=True, slots=True)
class ElevationSample:
    location: GeoLocation
    elevation_m: float
    source_id: str

@dataclass(frozen=True, slots=True)
class ElevationGrid:
    width: int
    height: int
    spacing_m: float
    crs: str
    elevation_buffer_key: str
