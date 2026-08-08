"""Filesystem boundary for the optional managed LRO/LOLA Moon layer."""

from pathlib import Path
from typing import Protocol

from terralab3d.domain.resources.moon_surface import MoonSurfaceResourceDescriptor


class MoonSurfaceAssetPort(Protocol):
    @property
    def descriptor(self) -> MoonSurfaceResourceDescriptor: ...

    def resolve_asset(self, asset_name: str) -> Path | None: ...
