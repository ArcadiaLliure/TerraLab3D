"""LRO/LOLA visible-limb profiles from the managed floating-point DEM."""

from __future__ import annotations

import hashlib
import json
import logging
import math
from pathlib import Path
from typing import Any

from terralab3d.domain.eclipses.models import (
    ApparentEventBody,
    LunarLimbProfile,
    LunarLimbSample,
    Vector3,
)
from terralab3d.infrastructure.app_paths import resolve_data_root

log = logging.getLogger("terralab3d.assets.lunar_limb")
REFERENCE_RADIUS_KM = 1_737.4


class LroLolaLimbProfileProvider:
    """Own one lazy DEM handle and derive the observer-specific terrain limb."""

    def __init__(self, moon_dir: Path | None = None) -> None:
        self._moon_dir = (
            moon_dir.resolve(strict=False)
            if moon_dir is not None
            else resolve_data_root() / "data" / "sky" / "moon"
        )
        self._dem_path: Path | None = None
        self._expected_sha256: str | None = None
        self._image: Any | None = None
        self._verified = False
        self._cache: dict[tuple[object, ...], LunarLimbProfile] = {}
        self.load_count = 0
        self.profile_count = 0
        self._read_manifest()

    def profile(
        self,
        moon: ApparentEventBody,
        *,
        sample_count: int = 720,
    ) -> LunarLimbProfile | None:
        if (
            self._dem_path is None
            or moon.body_to_icrf_quaternion is None
            or sample_count < 72
            or sample_count > 4096
        ):
            return None
        key = (
            tuple(round(value, 9) for value in moon.body_to_icrf_quaternion),
            tuple(round(value, 9) for value in moon.direction_icrf),
            round(moon.distance_km, 3),
            sample_count,
        )
        cached = self._cache.get(key)
        if cached is not None:
            return cached
        image = self._load_image()
        if image is None:
            return None

        line = _normalize(moon.direction_icrf)
        north = _reject((0.0, 0.0, 1.0), line)
        if _dot(north, north) <= 1.0e-20:
            north = _reject((1.0, 0.0, 0.0), line)
        north = _normalize(north)
        east = _normalize(_cross(north, line))
        inverse = _quaternion_conjugate(moon.body_to_icrf_quaternion)
        samples = []
        for index in range(sample_count):
            position_angle = index * 360.0 / sample_count
            angle = math.radians(position_angle)
            limb_icrf = tuple(
                north[axis] * math.cos(angle) + east[axis] * math.sin(angle)
                for axis in range(3)
            )
            limb_body = _quaternion_apply(inverse, limb_icrf)
            longitude = math.degrees(math.atan2(limb_body[1], limb_body[0]))
            latitude = math.degrees(math.asin(max(-1.0, min(1.0, limb_body[2]))))
            elevation = _bilinear_dem(image, longitude, latitude)
            samples.append(
                LunarLimbSample(
                    position_angle_deg=position_angle,
                    elevation_km=elevation,
                    angular_radius_deg=math.degrees(
                        math.atan2(REFERENCE_RADIUS_KM + elevation, moon.distance_km)
                    ),
                )
            )
        result = LunarLimbProfile(
            samples=tuple(samples),
            dataset_id="nasa-cgi-moon-kit-lro-lola-ldem16",
            asset_sha256=self._expected_sha256,
            quality="lro_lola",
        )
        if len(self._cache) >= 8:
            self._cache.clear()
        self._cache[key] = result
        self.profile_count += 1
        return result

    def close(self) -> None:
        if self._image is not None:
            self._image.close()
            self._image = None
        self._cache.clear()

    def _read_manifest(self) -> None:
        manifest_path = self._moon_dir / "moon-surface-manifest.json"
        try:
            payload = json.loads(manifest_path.read_text(encoding="utf-8"))
            dem = payload["dem"]
            source_name = str(dem["sourceFile"])
            if Path(source_name).name != source_name:
                raise ValueError("Unsafe LOLA DEM name")
            source_root = (self._moon_dir / "source").resolve(strict=False)
            path = (source_root / source_name).resolve(strict=False)
            if path.parent != source_root or not path.is_file():
                raise ValueError(f"LOLA DEM is missing: {path}")
            if int(dem["widthPx"]) != 5760 or int(dem["heightPx"]) != 2880:
                raise ValueError("Unexpected LOLA DEM dimensions")
            if str(dem["verticalUnits"]) != "floating-point kilometres relative to radius 1737.4 km":
                raise ValueError("Unexpected LOLA DEM units")
            self._dem_path = path
            self._expected_sha256 = str(dem["sha256"]).lower()
        except (OSError, ValueError, TypeError, KeyError, json.JSONDecodeError) as exc:
            log.warning("LRO/LOLA limb unavailable: %s", exc)
            self._dem_path = None

    def _load_image(self) -> Any | None:
        if self._image is not None:
            return self._image
        if self._dem_path is None:
            return None
        try:
            if not self._verified:
                actual = _sha256(self._dem_path)
                if actual != self._expected_sha256:
                    raise ValueError("LOLA DEM hash mismatch")
                self._verified = True
            from PIL import Image

            image = Image.open(self._dem_path)
            if image.size != (5760, 2880) or image.mode != "F":
                image.close()
                raise ValueError("LOLA DEM must be a 5760x2880 float image")
            image.load()
            self._image = image
            self.load_count += 1
            log.debug("MGP: [LroLolaLimbProfileProvider] [load] [DEM LOLA validat]")
            return image
        except (ImportError, OSError, ValueError) as exc:
            log.warning("LRO/LOLA limb load failed: %s", exc)
            return None


def _bilinear_dem(image: Any, longitude_deg: float, latitude_deg: float) -> float:
    width, height = image.size
    x = ((longitude_deg + 180.0) % 360.0) / 360.0 * width
    y = (90.0 - max(-90.0, min(90.0, latitude_deg))) / 180.0 * (height - 1)
    x0 = int(math.floor(x)) % width
    x1 = (x0 + 1) % width
    y0 = max(0, min(height - 1, int(math.floor(y))))
    y1 = min(height - 1, y0 + 1)
    fx = x - math.floor(x)
    fy = y - math.floor(y)
    top = float(image.getpixel((x0, y0))) * (1.0 - fx) + float(image.getpixel((x1, y0))) * fx
    bottom = float(image.getpixel((x0, y1))) * (1.0 - fx) + float(image.getpixel((x1, y1))) * fx
    return top * (1.0 - fy) + bottom * fy


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _dot(first: Vector3, second: Vector3) -> float:
    return sum(a * b for a, b in zip(first, second, strict=True))


def _normalize(vector: Vector3) -> Vector3:
    length = math.sqrt(_dot(vector, vector))
    if length <= 1.0e-15:
        raise ValueError("Degenerate limb direction")
    return tuple(value / length for value in vector)  # type: ignore[return-value]


def _reject(vector: Vector3, axis: Vector3) -> Vector3:
    projection = _dot(vector, axis)
    return tuple(vector[index] - projection * axis[index] for index in range(3))  # type: ignore[return-value]


def _cross(first: Vector3, second: Vector3) -> Vector3:
    return (
        first[1] * second[2] - first[2] * second[1],
        first[2] * second[0] - first[0] * second[2],
        first[0] * second[1] - first[1] * second[0],
    )


def _quaternion_conjugate(value: tuple[float, float, float, float]) -> tuple[float, float, float, float]:
    return -value[0], -value[1], -value[2], value[3]


def _quaternion_apply(
    quaternion: tuple[float, float, float, float],
    vector: Vector3,
) -> Vector3:
    x, y, z, w = quaternion
    vx, vy, vz = vector
    tx = 2.0 * (y * vz - z * vy)
    ty = 2.0 * (z * vx - x * vz)
    tz = 2.0 * (x * vy - y * vx)
    return (
        vx + w * tx + y * tz - z * ty,
        vy + w * ty + z * tx - x * tz,
        vz + w * tz + x * ty - y * tx,
    )
