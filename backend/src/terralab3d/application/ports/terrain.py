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


class LandCoverPort(Protocol):
    """Infrastructure boundary for categorical land-cover raster data.

    Implementations read configured raster sources, manage CRS transforms,
    and sample class IDs for terrain vertex coordinates.  This port is
    completely separate from OrthophotoPort: land-cover sources are never
    used for photo-realistic rendering.
    """

    def metadata(self) -> list["LandCoverSourceDescriptor"]:
        """Return descriptors for all configured land-cover sources."""
        ...

    def sample_classes(
        self,
        request: "LandCoverSamplingRequest",
    ) -> "LandCoverSampleGrid":
        """Sample categorical class IDs at the given coordinates."""
        ...

    def legend(self, legend_id: str) -> "LandCoverLegend":
        """Retrieve a legend by its identifier."""
        ...

    def close(self) -> None:
        """Release any open raster handles."""
        ...


# Deferred imports for type hints used in LandCoverPort
from terralab3d.domain.surface.models import (  # noqa: E402
    LandCoverLegend,
    LandCoverSampleGrid,
    LandCoverSamplingRequest,
    LandCoverSourceDescriptor,
)

