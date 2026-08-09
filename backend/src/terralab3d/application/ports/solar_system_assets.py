"""Filesystem boundary for Step 8.6 Solar System resources."""

from pathlib import Path
from typing import Protocol

from terralab3d.domain.resources.solar_system import SolarSystemResourceDescriptor
from terralab3d.domain.solar_system.catalog import SatelliteCatalogSnapshot


class SolarSystemAssetPort(Protocol):
    @property
    def descriptor(self) -> SolarSystemResourceDescriptor: ...

    @property
    def satellite_catalog(self) -> SatelliteCatalogSnapshot | None: ...

    @property
    def kernel_manifest_path(self) -> Path | None: ...

    def resolve_texture(self, asset_name: str) -> Path | None: ...
