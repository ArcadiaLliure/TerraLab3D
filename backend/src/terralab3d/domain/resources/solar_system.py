"""Renderer-neutral resource descriptors for Step 8.6 external assets."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any


class SolarSystemResourceStatus(str, Enum):
    READY = "ready"
    PARTIAL = "partial"
    UNAVAILABLE = "unavailable"
    INVALID = "invalid"


@dataclass(frozen=True, slots=True)
class PlanetTextureAsset:
    body_id: str
    naif_id: int
    role: str
    name: str
    url: str
    sha256: str
    byte_size: int
    width_px: int
    height_px: int
    image_format: str
    color_space: str
    projection: str
    central_meridian_deg: float | None
    uv_flip_x: bool
    uv_flip_y: bool
    uv_rotation_deg: float
    texture_quality: str
    credits: str
    license_name: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "bodyId": self.body_id,
            "naifId": self.naif_id,
            "role": self.role,
            "name": self.name,
            "url": self.url,
            "sha256": self.sha256,
            "byteSize": self.byte_size,
            "widthPx": self.width_px,
            "heightPx": self.height_px,
            "format": self.image_format,
            "colorSpace": self.color_space,
            "projection": self.projection,
            "centralMeridianDeg": self.central_meridian_deg,
            "uvFlipX": self.uv_flip_x,
            "uvFlipY": self.uv_flip_y,
            "uvRotationDeg": self.uv_rotation_deg,
            "textureQuality": self.texture_quality,
            "credits": self.credits,
            "license": self.license_name,
        }


@dataclass(frozen=True, slots=True)
class SolarSystemResourceDescriptor:
    status: SolarSystemResourceStatus
    manifest_version: str | None
    textures: tuple[PlanetTextureAsset, ...]
    catalog_payload: dict[str, Any] | None
    kernel_payload: dict[str, Any] | None
    detail: str | None = None

    def texture_manifest_dict(self) -> dict[str, Any]:
        return {
            "status": self.status.value,
            "manifestVersion": self.manifest_version,
            "textures": [asset.to_dict() for asset in self.textures],
            "detail": self.detail,
        }

    def catalog_manifest_dict(self) -> dict[str, Any]:
        payload = dict(self.catalog_payload or {})
        payload["status"] = self.status.value
        if self.detail is not None:
            payload["detail"] = self.detail
        return payload

