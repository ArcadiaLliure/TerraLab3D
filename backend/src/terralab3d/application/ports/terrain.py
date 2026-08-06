"""Ports de dades d’elevació, horitzó, terreny i superfícies."""
from typing import Protocol
from terralab3d.domain.elevation.models import ElevationGrid, ElevationSample
from terralab3d.domain.horizon.models import HorizonRequest, HorizonSample
from terralab3d.domain.observer.models import GeoLocation
from terralab3d.domain.surface.models import SurfaceSampleGrid
from terralab3d.domain.terrain.models import TerrainTileRequest

class ElevationPort(Protocol):
    def elevation(self, location: GeoLocation) -> ElevationSample | None: ...
    def horizon_samples(self, request: HorizonRequest) -> tuple[HorizonSample, ...]: ...
    def terrain_grid(self, request: TerrainTileRequest) -> ElevationGrid: ...

class OrthophotoPort(Protocol):
    def sample(self, request: TerrainTileRequest) -> SurfaceSampleGrid: ...

class LandCoverPort(Protocol):
    def sample(self, request: TerrainTileRequest) -> SurfaceSampleGrid: ...
