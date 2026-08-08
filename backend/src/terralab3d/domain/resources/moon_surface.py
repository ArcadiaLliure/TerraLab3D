"""Renderer-neutral descriptor for the optional managed lunar surface layer."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any


class MoonSurfaceStatus(str, Enum):
    READY = "ready"
    UNAVAILABLE = "unavailable"
    INVALID = "invalid"


@dataclass(frozen=True, slots=True)
class MoonSurfaceAsset:
    role: str
    name: str
    url: str
    width_px: int
    height_px: int
    sha256: str
    byte_size: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "role": self.role,
            "name": self.name,
            "url": self.url,
            "widthPx": self.width_px,
            "heightPx": self.height_px,
            "sha256": self.sha256,
            "byteSize": self.byte_size,
        }


@dataclass(frozen=True, slots=True)
class MoonSurfaceResourceDescriptor:
    status: MoonSurfaceStatus
    label: str
    dataset_id: str
    version: str | None
    projection: str | None
    central_longitude_deg: float | None
    color_space: str | None
    albedo_8k: MoonSurfaceAsset | None
    albedo_4k: MoonSurfaceAsset | None
    normal_map: MoonSurfaceAsset | None
    credits: tuple[str, ...]
    detail: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status.value,
            "label": self.label,
            "datasetId": self.dataset_id,
            "version": self.version,
            "projection": self.projection,
            "centralLongitudeDeg": self.central_longitude_deg,
            "colorSpace": self.color_space,
            "albedo8k": self.albedo_8k.to_dict() if self.albedo_8k is not None else None,
            "albedo4k": self.albedo_4k.to_dict() if self.albedo_4k is not None else None,
            "normalMap": self.normal_map.to_dict() if self.normal_map is not None else None,
            "credits": list(self.credits),
            "detail": self.detail,
        }


def unavailable_moon_surface(detail: str | None = None) -> MoonSurfaceResourceDescriptor:
    return MoonSurfaceResourceDescriptor(
        status=MoonSurfaceStatus.UNAVAILABLE,
        label="surface unavailable",
        dataset_id="nasa-cgi-moon-kit-lro-lola",
        version=None,
        projection=None,
        central_longitude_deg=None,
        color_space=None,
        albedo_8k=None,
        albedo_4k=None,
        normal_map=None,
        credits=("NASA's Scientific Visualization Studio",),
        detail=detail,
    )
