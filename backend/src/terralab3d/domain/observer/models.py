"""Models de domini tipats per a la capacitat observador."""


from dataclasses import dataclass
from terralab3d.domain.identifiers import ObserverId

@dataclass(frozen=True, slots=True)
class GeoLocation:
    latitude_deg: float
    longitude_deg: float
    elevation_m: float | None = None

    def __post_init__(self) -> None:
        import math
        if not (math.isfinite(self.latitude_deg) and math.isfinite(self.longitude_deg)):
            raise ValueError("Latitud i longitud han de ser nombres finits")
        if not (-90.0 <= self.latitude_deg <= 90.0):
            raise ValueError(f"La latitud ha d'estar entre -90 i 90 graus (obtingut: {self.latitude_deg})")
        if not (-180.0 <= self.longitude_deg <= 180.0):
            raise ValueError(f"La longitud ha d'estar entre -180 i 180 graus (obtingut: {self.longitude_deg})")

@dataclass(frozen=True, slots=True)
class ObserverProfile:
    observer_id: ObserverId
    location: GeoLocation
    height_offset_m: float = 0.0

    @property
    def effective_height_m(self) -> float:
        return (self.location.elevation_m or 0.0) + self.height_offset_m
