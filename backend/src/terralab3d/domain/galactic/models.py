"""Models purs de la capacitat Via Làctia i pols Planck."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from terralab3d.domain.identifiers import ResourceId


class GalacticCoordinateFrame(str, Enum):
    ICRF_J2000 = "ICRF/J2000"
    GALACTIC = "GALACTIC"


class GalacticTextureProjection(str, Enum):
    EQUIRECTANGULAR = "plate-carree/equirectangular"
    HEALPIX = "HEALPix"


@dataclass(frozen=True, slots=True)
class EquirectangularOrientation:
    longitude_at_center_deg: float
    longitude_increases_left: bool
    latitude_increases_up: bool = True


@dataclass(frozen=True, slots=True)
class GalacticTextureResource:
    resource_id: ResourceId
    version: str
    coordinate_frame: GalacticCoordinateFrame
    projection: GalacticTextureProjection
    source_format: str
    orientation: EquirectangularOrientation


@dataclass(frozen=True, slots=True)
class GalacticAppearance:
    opacity: float
    dust_density_strength: float
    dust_extinction_strength: float

    def __post_init__(self) -> None:
        for name, value in (
            ("opacity", self.opacity),
            ("dust_density_strength", self.dust_density_strength),
            ("dust_extinction_strength", self.dust_extinction_strength),
        ):
            if not 0.0 <= value <= 1.0:
                raise ValueError(f"{name} ha d'estar dins [0, 1]")
