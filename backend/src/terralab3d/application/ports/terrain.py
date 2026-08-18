"""Ports for elevation, terrain and surface infrastructure boundaries."""

from typing import Callable, Protocol

from terralab3d.domain.elevation.models import (
    ElevationBatch,
    ElevationBatchRequest,
    ElevationGrid,
    ElevationSample,
    ElevationSourceMetadata,
)
from terralab3d.domain.observer.models import GeoLocation
from terralab3d.domain.surface.models import SurfaceSampleGrid
from terralab3d.domain.terrain.models import TerrainTileRequest


class ElevationPort(Protocol):
    """DEM I/O only. Horizon science deliberately does not belong here."""

    def elevation(
        self,
        location: GeoLocation,
        cancellation_check: Callable[[], bool] | None = None,
    ) -> ElevationSample: ...
    def sample_points(self, request: ElevationBatchRequest) -> ElevationBatch: ...
    def metadata(self) -> ElevationSourceMetadata: ...
    def terrain_grid(self, request: TerrainTileRequest) -> ElevationGrid: ...
    def close(self) -> None: ...


class RadialCoordinateProjector(Protocol):
    """Infrastructure boundary for local metric radial coordinates to WGS84."""

    @property
    def working_crs(self) -> str: ...

    def project(
        self,
        latitude_deg: float,
        longitude_deg: float,
        azimuth_deg: object,
        distance_m: object,
    ) -> tuple[object, object]: ...


class OrthophotoPort(Protocol):
    def sample(self, request: TerrainTileRequest) -> SurfaceSampleGrid: ...

