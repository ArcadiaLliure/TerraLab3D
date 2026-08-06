"""Models de domini tipats per a la capacitat horitzó."""


from dataclasses import dataclass
from terralab3d.domain.identifiers import ResourceId

@dataclass(frozen=True, slots=True)
class HorizonRequest:
    latitude_deg: float
    longitude_deg: float
    observer_elevation_m: float
    visible_radius_m: float
    angular_step_deg: float

@dataclass(frozen=True, slots=True)
class HorizonSample:
    azimuth_deg: float
    elevation_angle_deg: float
    distance_m: float

@dataclass(frozen=True, slots=True)
class HorizonProfile:
    resource_id: ResourceId
    version: int
    samples: tuple[HorizonSample, ...]
