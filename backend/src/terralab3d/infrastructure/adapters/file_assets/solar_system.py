"""Validated access to external planet textures, kernels and catalogue."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from terralab3d.domain.resources.solar_system import (
    PlanetTextureAsset,
    SolarSystemResourceDescriptor,
    SolarSystemResourceStatus,
)
from terralab3d.domain.solar_system.catalog import SatelliteCatalogSnapshot
from terralab3d.infrastructure.app_paths import resolve_data_root

log = logging.getLogger("terralab3d.solar_system.assets")


class ManagedSolarSystemAssets:
    """Owns validated descriptors; texture bytes remain in ``data_root``."""

    def __init__(self, solar_root: Path | None = None) -> None:
        self._root = (
            solar_root.resolve()
            if solar_root is not None
            else (resolve_data_root() / "data" / "sky" / "solar-system").resolve()
        )
        self._manifests = self._root / "kernels" / "manifests"
        self._textures_by_name: dict[str, Path] = {}
        self._satellite_catalog: SatelliteCatalogSnapshot | None = None
        self._kernel_manifest_path: Path | None = None
        self._descriptor = self._load()

    @property
    def descriptor(self) -> SolarSystemResourceDescriptor:
        return self._descriptor

    @property
    def satellite_catalog(self) -> SatelliteCatalogSnapshot | None:
        return self._satellite_catalog

    @property
    def kernel_manifest_path(self) -> Path | None:
        return self._kernel_manifest_path

    def resolve_texture(self, asset_name: str) -> Path | None:
        if Path(asset_name).name != asset_name:
            return None
        return self._textures_by_name.get(asset_name)

    def _load(self) -> SolarSystemResourceDescriptor:
        texture_path = self._manifests / "planet_texture_manifest.json"
        catalog_path = self._manifests / "satellite_catalog.json"
        kernel_path = self._manifests / "kernel_manifest.json"
        missing = [path.name for path in (texture_path, catalog_path, kernel_path) if not path.is_file()]
        if missing:
            detail = "Missing Solar System manifest(s): " + ", ".join(missing)
            log.warning("MGP: [ManagedSolarSystemAssets.py] [load] [%s]", detail)
            return SolarSystemResourceDescriptor(
                SolarSystemResourceStatus.UNAVAILABLE, None, (), None, None, detail
            )
        try:
            texture_payload = _read_json(texture_path)
            catalog_payload = _read_json(catalog_path)
            kernel_payload = _read_json(kernel_path)
            textures = self._validated_textures(texture_payload)
            self._satellite_catalog = SatelliteCatalogSnapshot.from_dict(catalog_payload)
            self._validate_catalog(self._satellite_catalog)
            self._validate_kernels(kernel_payload, kernel_path)
            status = (
                SolarSystemResourceStatus.READY
                if len(textures) >= 9
                else SolarSystemResourceStatus.PARTIAL
            )
            log.debug(
                "MGP: [ManagedSolarSystemAssets.py] [load] "
                "[Recursos validats textures=%d catalog=%d kernels=%d]",
                len(textures),
                self._satellite_catalog.total_count,
                len(kernel_payload.get("kernels", ())),
            )
            return SolarSystemResourceDescriptor(
                status=status,
                manifest_version=str(texture_payload.get("manifestVersion")),
                textures=tuple(textures),
                catalog_payload=catalog_payload,
                kernel_payload=kernel_payload,
            )
        except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
            detail = f"Invalid Solar System resources: {exc}"
            log.exception("MGP: [ManagedSolarSystemAssets.py] [load] [%s]", detail)
            self._textures_by_name.clear()
            self._satellite_catalog = None
            self._kernel_manifest_path = None
            return SolarSystemResourceDescriptor(
                SolarSystemResourceStatus.INVALID, None, (), None, None, detail
            )

    def _validated_textures(self, payload: dict[str, Any]) -> list[PlanetTextureAsset]:
        result: list[PlanetTextureAsset] = []
        planets_root = (self._root / "planets").resolve()
        for raw in payload.get("assets", ()):
            name = Path(str(raw["sourceFile"])).name
            path = (planets_root / name).resolve()
            if path.parent != planets_root or not path.is_file():
                raise ValueError(f"Texture missing or outside data_root: {name}")
            if path.stat().st_size != int(raw["byteSize"]):
                raise ValueError(f"Texture size mismatch: {name}")
            asset = PlanetTextureAsset(
                body_id=str(raw["bodyId"]),
                naif_id=int(raw["naifId"]),
                role=str(raw["role"]),
                name=name,
                url=str(raw["url"]),
                sha256=str(raw["sha256"]),
                byte_size=int(raw["byteSize"]),
                width_px=int(raw["width"]),
                height_px=int(raw["height"]),
                image_format=str(raw["format"]),
                color_space=str(raw["colorSpace"]),
                projection=str(raw["projection"]),
                central_meridian_deg=(
                    float(raw["centralMeridianDeg"])
                    if raw.get("centralMeridianDeg") is not None
                    else None
                ),
                uv_flip_x=bool(raw["uvFlipX"]),
                uv_flip_y=bool(raw["uvFlipY"]),
                uv_rotation_deg=float(raw["uvRotationDeg"]),
                texture_quality=str(raw["textureQuality"]),
                credits=str(raw["credits"]),
                license_name=str(raw["license"]),
            )
            self._textures_by_name[name] = path
            result.append(asset)
        return result

    @staticmethod
    def _validate_catalog(catalog: SatelliteCatalogSnapshot) -> None:
        expected = {
            "earth": 1,
            "mars": 2,
            "jupiter": 115,
            "saturn": 293,
            "uranus": 29,
            "neptune": 16,
            "pluto": 5,
        }
        if catalog.total_count != 461 or catalog.by_parent != expected:
            raise ValueError(f"Unexpected satellite catalogue counts: {catalog.by_parent}")
        ids = [item.naif_id for item in catalog.satellites if item.naif_id is not None]
        if len(ids) != len(set(ids)):
            raise ValueError("Duplicate satellite NAIF ID")

    def _validate_kernels(self, payload: dict[str, Any], manifest_path: Path) -> None:
        kernels_root = manifest_path.parent.parent
        sky_root = self._root.parent.resolve()
        for item in payload.get("kernels", ()):
            if not item.get("installed"):
                continue
            base = sky_root if item.get("relativeBase") == "sky" else kernels_root
            path = (base / str(item["relativePath"])).resolve()
            if sky_root not in path.parents or not path.is_file():
                raise ValueError(f"Kernel missing: {item['fileName']}")
            if path.stat().st_size != int(item["byteSize"]):
                raise ValueError(f"Kernel size mismatch: {item['fileName']}")
        self._kernel_manifest_path = manifest_path.resolve()


def _read_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)
