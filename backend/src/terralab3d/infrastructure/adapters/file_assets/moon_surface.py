"""Validated local catalog for the user-managed NASA LRO/LOLA Moon layer."""

from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import replace
from pathlib import Path
from typing import Any

from terralab3d.domain.resources.moon_surface import (
    MoonSurfaceAsset,
    MoonSurfaceResourceDescriptor,
    MoonSurfaceStatus,
    unavailable_moon_surface,
)
from terralab3d.infrastructure.app_paths import resolve_data_root

log = logging.getLogger("terralab3d.assets.moon")

MANIFEST_NAME = "moon-surface-manifest.json"
REQUIRED_MANIFEST_FIELDS = {
    "source",
    "sourcePage",
    "sourceUrl",
    "sourceFile",
    "sourceVersion",
    "acquisitionDate",
    "sha256",
    "projection",
    "centralLongitudeDeg",
    "colorSpace",
    "generatedAsset",
    "generatedAssetSha256",
    "generatorVersion",
    "credits",
    "assets",
}


class ManagedMoonSurfaceAssets:
    """Loads and hashes an installed layer once; it never downloads at runtime."""

    def __init__(self, moon_dir: Path | None = None) -> None:
        self._moon_dir = (
            moon_dir.resolve(strict=False)
            if moon_dir is not None
            else resolve_data_root() / "data" / "sky" / "moon"
        )
        self._files: dict[str, Path] = {}
        self._descriptor = self._load()

    @property
    def descriptor(self) -> MoonSurfaceResourceDescriptor:
        return self._descriptor

    def resolve_asset(self, asset_name: str) -> Path | None:
        return self._files.get(asset_name)

    def _load(self) -> MoonSurfaceResourceDescriptor:
        manifest_path = self._moon_dir / MANIFEST_NAME
        if not manifest_path.is_file():
            return unavailable_moon_surface(f"Managed layer manifest not found: {manifest_path}")
        try:
            payload = json.loads(manifest_path.read_text(encoding="utf-8"))
            missing_fields = REQUIRED_MANIFEST_FIELDS.difference(payload)
            if missing_fields:
                raise ValueError("Manifest fields missing: " + ", ".join(sorted(missing_fields)))
            assets: dict[str, MoonSurfaceAsset] = {}
            for item in payload["assets"]:
                role = str(item["role"])
                if role in assets:
                    raise ValueError(f"Duplicate Moon asset role: {role}")
                assets[role] = self._validate_asset(item)
            albedo_8k = assets.get("albedo_8k")
            albedo_4k = assets.get("albedo_4k")
            if albedo_8k is None and albedo_4k is None:
                raise ValueError("Manifest has no usable albedo_8k or albedo_4k asset")
            label = "LRO 2025 8K" if albedo_8k is not None else "LRO 2025 4K fallback"
            descriptor = MoonSurfaceResourceDescriptor(
                status=MoonSurfaceStatus.READY,
                label=label,
                dataset_id=str(payload.get("datasetId", "nasa-cgi-moon-kit-lro-lola")),
                version=str(payload["sourceVersion"]),
                projection=str(payload["projection"]),
                central_longitude_deg=float(payload["centralLongitudeDeg"]),
                color_space=str(payload["colorSpace"]),
                albedo_8k=albedo_8k,
                albedo_4k=albedo_4k,
                normal_map=assets.get("normal_4k"),
                credits=tuple(str(value) for value in payload["credits"]),
            )
            log.info(
                "Managed Moon layer ready: %s files=%d directory=%s",
                descriptor.label,
                len(self._files),
                self._moon_dir,
            )
            return descriptor
        except (OSError, ValueError, TypeError, KeyError, json.JSONDecodeError) as exc:
            self._files.clear()
            log.warning("Managed Moon layer invalid; retaining Step 8 fallback: %s", exc)
            return replace(
                unavailable_moon_surface(str(exc)),
                status=MoonSurfaceStatus.INVALID,
            )

    def _validate_asset(self, item: dict[str, Any]) -> MoonSurfaceAsset:
        name = str(item["name"])
        if Path(name).name != name:
            raise ValueError(f"Unsafe Moon asset name: {name}")
        path = (self._moon_dir / "runtime" / name).resolve(strict=False)
        runtime_root = (self._moon_dir / "runtime").resolve(strict=False)
        if path.parent != runtime_root or not path.is_file():
            raise ValueError(f"Moon asset is missing: {path}")
        expected_sha256 = str(item["sha256"]).lower()
        actual_sha256 = _sha256(path)
        if actual_sha256 != expected_sha256:
            raise ValueError(f"Moon asset hash mismatch: {name}")
        if path.stat().st_size != int(item["byteSize"]):
            raise ValueError(f"Moon asset size mismatch: {name}")
        self._files[name] = path
        return MoonSurfaceAsset(
            role=str(item["role"]),
            name=name,
            url=f"/moon-assets/{name}",
            width_px=int(item["widthPx"]),
            height_px=int(item["heightPx"]),
            sha256=actual_sha256,
            byte_size=path.stat().st_size,
        )


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
