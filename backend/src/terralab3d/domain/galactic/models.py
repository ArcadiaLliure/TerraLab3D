"""Models de domini tipats per a la capacitat Via Làctia i pols."""


from dataclasses import dataclass
from terralab3d.domain.identifiers import ResourceId

@dataclass(frozen=True, slots=True)
class GalacticTextureResource:
    resource_id: ResourceId
    version: int
    coordinate_frame: str
    texture_key: str

@dataclass(frozen=True, slots=True)
class GalacticAppearance:
    opacity: float
    dust_density_strength: float
    dust_extinction_strength: float
