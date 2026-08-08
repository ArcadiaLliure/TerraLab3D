"""Explicit installer/generator for the optional NASA LRO/LOLA Moon layer.

This tool is intentionally never called by the application.  It downloads the
source material only after an explicit CLI invocation, stores every file in the
user-selected TerraLab data library, and writes a hash-pinned runtime manifest.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import shutil
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

GENERATOR_VERSION = "terralab3d-moon-assets/1.0.0"
NASA_SOURCE_PAGE = "https://svs.gsfc.nasa.gov/4720/"
ALBEDO_SOURCE = (
    "lroc_color_16bit_srgb_8k.tif",
    "https://svs.gsfc.nasa.gov/vis/a000000/a004700/a004720/"
    "lroc_color_16bit_srgb_8k.tif",
)
DEM_SOURCE = (
    "ldem_16.tif",
    "https://svs.gsfc.nasa.gov/vis/a000000/a004700/a004720/ldem_16.tif",
)
ORIENTATION_SOURCES = (
    (
        "moon_080317.tf",
        "https://naif.jpl.nasa.gov/pub/naif/generic_kernels/fk/satellites/moon_080317.tf",
    ),
    (
        "moon_pa_de421_1900-2050.bpc",
        "https://naif.jpl.nasa.gov/pub/naif/generic_kernels/pck/"
        "moon_pa_de421_1900-2050.bpc",
    ),
)
RUNTIME_ALBEDO_8K = "moon_albedo_lro_2025_8k.jpg"
RUNTIME_ALBEDO_4K = "moon_albedo_lro_2025_4k.jpg"
RUNTIME_NORMAL_4K = "moon_normal_lola_4k.png"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--data-root",
        required=True,
        type=Path,
        help="TerraLab data-library root selected by the user (for example I:\\TerraLab)",
    )
    parser.add_argument(
        "--force-regenerate",
        action="store_true",
        help="Regenerate derived runtime files while preserving downloaded sources",
    )
    args = parser.parse_args()

    try:
        import numpy as np
        from PIL import Image
    except ImportError as exc:
        print(
            "Install the pinned tool dependencies first: "
            "python -m pip install -r tools/requirements-moon-assets.txt",
            file=sys.stderr,
        )
        raise SystemExit(2) from exc

    moon_dir = args.data_root.expanduser().resolve(strict=False) / "data" / "sky" / "moon"
    source_dir = moon_dir / "source"
    runtime_dir = moon_dir / "runtime"
    orientation_dir = moon_dir / "orientation"
    for directory in (source_dir, runtime_dir, orientation_dir):
        directory.mkdir(parents=True, exist_ok=True)

    albedo_source = _download(ALBEDO_SOURCE[1], source_dir / ALBEDO_SOURCE[0])
    dem_source = _download(DEM_SOURCE[1], source_dir / DEM_SOURCE[0])
    orientation_files = {
        name: _download(url, orientation_dir / name)
        for name, url in ORIENTATION_SOURCES
    }

    albedo_8k = runtime_dir / RUNTIME_ALBEDO_8K
    albedo_4k = runtime_dir / RUNTIME_ALBEDO_4K
    normal_4k = runtime_dir / RUNTIME_NORMAL_4K
    if args.force_regenerate or not albedo_8k.is_file() or not albedo_4k.is_file():
        _generate_albedo_derivatives(Image, albedo_source, albedo_8k, albedo_4k)
    if args.force_regenerate or not normal_4k.is_file():
        _generate_normal_map(np, Image, dem_source, normal_4k)

    assets = (
        _asset("albedo_8k", albedo_8k, 8192, 4096),
        _asset("albedo_4k", albedo_4k, 4096, 2048),
        _asset("normal_4k", normal_4k, 4096, 2048),
    )
    manifest: dict[str, Any] = {
        "schemaVersion": 1,
        "datasetId": "nasa-cgi-moon-kit-lro-lola",
        "source": "NASA Scientific Visualization Studio — CGI Moon Kit",
        "sourcePage": NASA_SOURCE_PAGE,
        "sourceUrl": ALBEDO_SOURCE[1],
        "sourceFile": ALBEDO_SOURCE[0],
        "sourceVersion": "LROC color map 2025",
        "acquisitionDate": datetime.now(timezone.utc).date().isoformat(),
        "sha256": _sha256(albedo_source),
        "projection": "global equirectangular/cylindrical",
        "centralLongitudeDeg": 0,
        "longitudeDirection": "east-positive",
        "northAtTop": True,
        "uvConvention": (
            "U increases eastward from -180 to +180 degrees; V source rows run north to south; "
            "the renderer applies one fixed mesh-to-MOON_ME_DE421 calibration"
        ),
        "colorSpace": "sRGB",
        "generatedAsset": RUNTIME_ALBEDO_8K,
        "generatedAssetSha256": assets[0]["sha256"],
        "generatorVersion": GENERATOR_VERSION,
        "credits": [
            "NASA's Scientific Visualization Studio",
            "Ernie Wright (USRA), visualizer",
            "Noah Petro (NASA/GSFC), scientist",
            "LROC WAC Color Mosaic — LRO Camera / Arizona State University",
            "DEM — Lunar Reconnaissance Orbiter Laser Altimeter (LOLA)",
        ],
        "assets": list(assets),
        "dem": {
            "sourceFile": DEM_SOURCE[0],
            "sourceUrl": DEM_SOURCE[1],
            "sha256": _sha256(dem_source),
            "widthPx": 5760,
            "heightPx": 2880,
            "verticalUnits": "floating-point kilometres relative to radius 1737.4 km",
            "referenceRadiusKm": 1737.4,
            "normalScale": 1.0,
            "generatedAsset": RUNTIME_NORMAL_4K,
            "generatedAssetSha256": assets[2]["sha256"],
        },
        "orientation": {
            "frame": "MOON_ME_DE421",
            "rangeStartUtc": "1900-01-01",
            "rangeEndUtcExclusive": "2051-01-01",
            "files": [
                {
                    "name": name,
                    "url": url,
                    "sha256": _sha256(orientation_files[name]),
                }
                for name, url in ORIENTATION_SOURCES
            ],
        },
    }
    manifest_path = moon_dir / "moon-surface-manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"Moon layer installed: {manifest_path}")
    for item in assets:
        print(f"  {item['role']}: {item['name']} sha256={item['sha256']}")
    return 0


def _download(url: str, destination: Path) -> Path:
    if destination.is_file() and destination.stat().st_size > 0:
        print(f"Reusing source: {destination}")
        return destination
    temporary = destination.with_suffix(destination.suffix + ".download")
    print(f"Downloading {url}")
    request = urllib.request.Request(url, headers={"User-Agent": "TerraLab3D asset installer/1.0"})
    try:
        with urllib.request.urlopen(request, timeout=120) as response, temporary.open("wb") as output:
            shutil.copyfileobj(response, output, length=1024 * 1024)
        temporary.replace(destination)
    finally:
        if temporary.exists():
            temporary.unlink()
    return destination


def _generate_albedo_derivatives(Image: Any, source: Path, output_8k: Path, output_4k: Path) -> None:
    print("Generating neutral sRGB albedo derivatives")
    with Image.open(source) as image:
        rgb = image.convert("RGB")
        if rgb.size != (8192, 4096):
            rgb = rgb.resize((8192, 4096), Image.Resampling.LANCZOS)
        rgb.save(output_8k, "JPEG", quality=94, subsampling=0, optimize=True, progressive=True)
        fallback = rgb.resize((4096, 2048), Image.Resampling.LANCZOS)
        fallback.save(output_4k, "JPEG", quality=94, subsampling=0, optimize=True, progressive=True)


def _generate_normal_map(np: Any, Image: Any, source: Path, output: Path) -> None:
    """Generate tangent-space normals at physical scale 1.0 from LOLA kilometres."""

    print("Generating LOLA tangent-space normal map at physical scale 1.0")
    with Image.open(source) as image:
        elevation_image = image.convert("F").resize((4096, 2048), Image.Resampling.LANCZOS)
        height_km = np.asarray(elevation_image, dtype=np.float32)

    rows, columns = height_km.shape
    delta_lon = 2.0 * math.pi / columns
    delta_lat = math.pi / rows
    east_derivative = (np.roll(height_km, -1, axis=1) - np.roll(height_km, 1, axis=1)) / (
        2.0 * delta_lon
    )
    north_derivative = np.empty_like(height_km)
    north_derivative[1:-1] = (height_km[:-2] - height_km[2:]) / (2.0 * delta_lat)
    north_derivative[0] = (height_km[0] - height_km[1]) / delta_lat
    north_derivative[-1] = (height_km[-2] - height_km[-1]) / delta_lat

    latitude = math.pi / 2.0 - (np.arange(rows, dtype=np.float32) + 0.5) * delta_lat
    east_radius = 1737.4 * np.maximum(np.cos(latitude), 1.0e-4)
    slope_east = east_derivative / east_radius[:, None]
    slope_north = north_derivative / 1737.4
    inverse_length = 1.0 / np.sqrt(slope_east**2 + slope_north**2 + 1.0)
    encoded = np.empty((rows, columns, 3), dtype=np.uint8)
    encoded[:, :, 0] = np.clip((-slope_east * inverse_length * 0.5 + 0.5) * 255.0, 0, 255)
    encoded[:, :, 1] = np.clip((-slope_north * inverse_length * 0.5 + 0.5) * 255.0, 0, 255)
    encoded[:, :, 2] = np.clip((inverse_length * 0.5 + 0.5) * 255.0, 0, 255)
    Image.fromarray(encoded).save(output, "PNG", optimize=True)


def _asset(role: str, path: Path, width_px: int, height_px: int) -> dict[str, Any]:
    return {
        "role": role,
        "name": path.name,
        "widthPx": width_px,
        "heightPx": height_px,
        "sha256": _sha256(path),
        "byteSize": path.stat().st_size,
    }


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


if __name__ == "__main__":
    raise SystemExit(main())
