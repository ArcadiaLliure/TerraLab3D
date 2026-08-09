#!/usr/bin/env python3
"""Instal·la i inventaria les dades externes del Sistema Solar del Pas 8.6.

Els kernels i les textures continuen fora de Git, sota ``data_root``. Només els
manifests reproduïbles i el snapshot compacte del catàleg s'escriuen al
workspace. Les descàrregues són idempotents, reprenibles i verificades contra
els MD5 publicats per NAIF quan la font en proporciona un.
"""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import os
import re
import shutil
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, Iterable

NAIF_ROOT = "https://naif.jpl.nasa.gov/pub/naif/generic_kernels"
SATELLITE_ROOT = f"{NAIF_ROOT}/spk/satellites"
PLANET_ROOT = f"{NAIF_ROOT}/spk/planets"
JPL_DISCOVERY_URL = "https://ssd.jpl.nasa.gov/sats/discovery.html"
JPL_PHYSICAL_URL = "https://ssd.jpl.nasa.gov/sats/phys_par/"
CATALOG_VERSION = "jpl-planetary-satellites-2026-07-09"
CATALOG_DATE = "2026-07-09"

SATELLITE_KERNELS = (
    "mar099s.bsp",
    "jup365.bsp",
    "jup347.bsp",
    "jup348.bsp",
    "jup349.bsp",
    "sat393_daphnis.bsp",
    "sat415.bsp",
    "sat441.bsp",
    "sat455.bsp",
    "sat456.bsp",
    "sat457.bsp",
    "sat459.bsp",
    "sat480.bsp",
    "ura184_part-1.bsp",
    "ura184_part-2.bsp",
    "ura184_part-3.bsp",
    # Load the older specialised solutions first.  The 2026 NEP098 global
    # solution is the Horizons-aligned authority wherever coverage overlaps.
    "nep104.bsp",
    "nep105.bsp",
    "nep098_part-1.bsp",
    "nep098_part-2.bsp",
    "nep098_part-3.bsp",
    "plu060.bsp",
)

SMALL_KERNELS = (
    ("lsk", "naif0012.tls", f"{NAIF_ROOT}/lsk/naif0012.tls"),
    ("pck", "pck00011.tpc", f"{NAIF_ROOT}/pck/pck00011.tpc"),
    ("pck", "earth_latest_high_prec.bpc", f"{NAIF_ROOT}/pck/earth_latest_high_prec.bpc"),
    ("spk/planets", "de440s.bsp", f"{PLANET_ROOT}/de440s.bsp"),
)

PARENT_INFO = {
    "Earth": (399, "earth"),
    "Mars": (499, "mars"),
    "Jupiter": (599, "jupiter"),
    "Saturn": (699, "saturn"),
    "Uranus": (799, "uranus"),
    "Neptune": (899, "neptune"),
    "Dwarf Planet Pluto": (999, "pluto"),
}

TEXTURE_BODY_FILES = {
    "mercury.jpg": ("mercury", 199, "surface"),
    "venus.jpg": ("venus", 299, "atmosphere_reference"),
    "venus_surface.jpg": ("venus", 299, "surface_reference"),
    "mars.jpg": ("mars", 499, "surface"),
    "jupiter.jpg": ("jupiter", 599, "atmosphere_reference"),
    "saturn.jpg": ("saturn", 699, "atmosphere_reference"),
    "saturn_rings.png": ("saturn", 699, "rings"),
    "uranus.jpg": ("uranus", 799, "atmosphere_reference"),
    "neptune.jpg": ("neptune", 899, "atmosphere_reference"),
}


@dataclass(frozen=True)
class KernelSummary:
    file_name: str
    body_names: dict[int, str]
    coverage_text: tuple[str, str] | None


class _DiscoveryParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.rows: list[tuple[list[str], set[str]]] = []
        self._in_row = False
        self._in_cell = False
        self._classes: set[str] = set()
        self._cells: list[str] = []
        self._parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "tr":
            values = dict(attrs)
            self._in_row = True
            self._classes = set((values.get("class") or "").split())
            self._cells = []
        elif self._in_row and tag in {"td", "th"}:
            self._in_cell = True
            self._parts = []

    def handle_data(self, data: str) -> None:
        if self._in_cell:
            self._parts.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag in {"td", "th"} and self._in_cell:
            self._cells.append(" ".join("".join(self._parts).split()))
            self._in_cell = False
        elif tag == "tr" and self._in_row:
            self.rows.append((self._cells, self._classes))
            self._in_row = False


def log(method: str, message: str) -> None:
    print(f"MGP: [prepare_solar_system_assets.py] [{method}] [{message}]", flush=True)


def resolve_data_root() -> Path:
    configured = os.getenv("TERRALAB_DATA_ROOT", "").strip()
    if configured:
        return Path(configured).expanduser().resolve(strict=False)
    appdata = Path(os.getenv("APPDATA", Path.home() / ".local" / "share"))
    pointer = appdata / "TerraLab" / "config" / "data_location.json"
    if pointer.is_file():
        payload = json.loads(pointer.read_text(encoding="utf-8"))
        raw = str(payload.get("data_root", "")).strip()
        if raw:
            return Path(raw).expanduser().resolve(strict=False)
    return (appdata / "TerraLab").resolve(strict=False)


def fetch_text(url: str, attempts: int = 3) -> str:
    for attempt in range(1, attempts + 1):
        try:
            request = urllib.request.Request(url, headers={"User-Agent": "TerraLab3D/0.1"})
            with urllib.request.urlopen(request, timeout=60) as response:
                return response.read().decode("utf-8", "replace")
        except (OSError, urllib.error.URLError):
            if attempt == attempts:
                raise
            time.sleep(attempt * 2)
    raise RuntimeError("unreachable")


def parse_checksums(text: str) -> dict[str, str]:
    return {
        name: digest.lower()
        for digest, name in re.findall(r"^([0-9a-fA-F]{32})\s+(\S+)$", text, re.MULTILINE)
    }


def digest_file(path: Path, algorithm: str) -> str:
    digest = hashlib.new(algorithm)
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(4 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def download_file(url: str, destination: Path, expected_md5: str | None = None) -> Path:
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.is_file() and (
        expected_md5 is None or digest_file(destination, "md5") == expected_md5
    ):
        log("download", f"Ja instal·lat file={destination.name} bytes={destination.stat().st_size}")
        return destination

    partial = destination.with_suffix(destination.suffix + ".part")
    for attempt in range(1, 4):
        offset = partial.stat().st_size if partial.is_file() else 0
        headers = {"User-Agent": "TerraLab3D/0.1"}
        if offset:
            headers["Range"] = f"bytes={offset}-"
        try:
            request = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(request, timeout=120) as response:
                status = getattr(response, "status", 200)
                if offset and status != 206:
                    partial.unlink(missing_ok=True)
                    offset = 0
                mode = "ab" if offset and status == 206 else "wb"
                downloaded = offset
                next_report = ((downloaded // (256 * 1024 * 1024)) + 1) * 256 * 1024 * 1024
                with partial.open(mode) as handle:
                    while True:
                        chunk = response.read(4 * 1024 * 1024)
                        if not chunk:
                            break
                        handle.write(chunk)
                        downloaded += len(chunk)
                        if downloaded >= next_report:
                            log("download", f"Progrés file={destination.name} mib={downloaded // 1048576}")
                            next_report += 256 * 1024 * 1024
            if expected_md5 is not None:
                actual = digest_file(partial, "md5")
                if actual != expected_md5:
                    partial.unlink(missing_ok=True)
                    raise ValueError(
                        f"MD5 incorrecte per {destination.name}: {actual} != {expected_md5}"
                    )
            partial.replace(destination)
            log("download", f"Instal·lat file={destination.name} bytes={destination.stat().st_size}")
            return destination
        except (OSError, urllib.error.URLError, ValueError) as exc:
            if attempt == 3:
                raise
            log("download", f"Retry file={destination.name} attempt={attempt} cause={exc}")
            time.sleep(attempt * 3)
    raise RuntimeError("unreachable")


def parse_kernel_summaries(text: str) -> dict[str, KernelSummary]:
    summaries: dict[str, KernelSummary] = {}
    for chunk in re.split(r"(?=Summary for: )", text):
        file_match = re.search(r"Summary for:\s*(\S+\.bsp)", chunk)
        if file_match is None:
            continue
        bodies: dict[int, str] = {}
        for line in chunk.splitlines():
            match = re.search(
                r"^\s*(?:(?:Body|Bodies):\s*)?(.+?)\s+\((-?\d+)\)\s+w\.r\.t\.",
                line,
            )
            if match:
                bodies[int(match.group(2))] = match.group(1).strip()
        dates = re.findall(
            r"^\s*((?:\d+ B\.C\. )?\d{1,5} [A-Z]{3} \d{2} [0-9:.]+)\s+"
            r"((?:\d+ B\.C\. )?\d{1,5} [A-Z]{3} \d{2} [0-9:.]+)\s*$",
            chunk,
            re.MULTILINE,
        )
        summaries[file_match.group(1)] = KernelSummary(
            file_name=file_match.group(1),
            body_names=bodies,
            coverage_text=dates[0] if dates else None,
        )
    return summaries


def normalized_name(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", value.lower())


def parse_discovery_catalog(text: str) -> list[dict[str, Any]]:
    parser = _DiscoveryParser()
    parser.feed(text)
    entries: list[dict[str, Any]] = []
    parent: str | None = None
    for cells, classes in parser.rows:
        if "sat-discovery-planet" in classes and cells:
            parent = next((name for name in PARENT_INFO if name in cells[0]), None)
            continue
        if parent is None or len(cells) < 3 or cells[0] == "IAU number":
            continue
        name = cells[1]
        provisional = cells[2]
        display_name = name or provisional
        parent_naif, parent_id = PARENT_INFO[parent]
        entries.append(
            {
                "iauNumber": cells[0] or None,
                "name": name or None,
                "provisionalDesignation": provisional or None,
                "displayName": display_name,
                "parentNaifId": parent_naif,
                "parentId": parent_id,
                "discoveryYear": cells[3] if len(cells) > 3 else None,
            }
        )
    return entries


def parse_physical_parameters(text: str) -> dict[int, dict[str, Any]]:
    result: dict[int, dict[str, Any]] = {}
    for row in re.findall(r"<tr[^>]*>(.*?)</tr>", text, flags=re.DOTALL | re.IGNORECASE):
        cells = []
        for value in re.findall(
            r"<td[^>]*>(.*?)(?=<td\b|</tr>|$)", row, flags=re.DOTALL | re.IGNORECASE
        ):
            clean = re.sub(r"<[^>]+>", " ", value)
            cells.append(" ".join(html.unescape(clean).split()))
        if len(cells) < 9 or not cells[2].isdigit():
            continue
        try:
            radius = float(cells[6])
        except ValueError:
            radius = None
        result[int(cells[2])] = {
            "meanRadiusKm": radius,
            "meanRadiusSigmaKm": _optional_float(cells[7]),
            "radiusReference": cells[8] or None,
        }
    return result


def _optional_float(value: str) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def image_metadata(path: Path) -> tuple[int, int, str]:
    from PIL import Image

    with Image.open(path) as image:
        return image.width, image.height, image.format or path.suffix.lstrip(".").upper()


def build_texture_manifest(planets_dir: Path, acquisition_date: str) -> dict[str, Any]:
    license_path = planets_dir / "LICENSE.txt"
    credits = license_path.read_text(encoding="utf-8", errors="replace") if license_path.is_file() else ""
    assets = []
    for path in sorted(planets_dir.iterdir()):
        definition = TEXTURE_BODY_FILES.get(path.name.lower())
        if definition is None or not path.is_file():
            continue
        body_id, naif_id, role = definition
        width, height, image_format = image_metadata(path)
        assets.append(
            {
                "bodyId": body_id,
                "naifId": naif_id,
                "role": role,
                "sourceFile": path.name,
                "resolvedPath": str(path.resolve()),
                "url": f"/planet-assets/{path.name}",
                "sha256": digest_file(path, "sha256"),
                "byteSize": path.stat().st_size,
                "width": width,
                "height": height,
                "format": image_format,
                "colorSpace": "sRGB",
                "projection": "equirectangular" if role != "rings" else "radial-strip",
                "centralMeridianDeg": None,
                "uvFlipX": False,
                "uvFlipY": False,
                "uvRotationDeg": 0,
                "textureQuality": "VISUAL_REFERENCE",
                "credits": "Solar System Scope / NASA-derived imagery",
                "license": "CC BY 4.0",
            }
        )
    return {
        "manifestVersion": f"planet-textures-{acquisition_date}",
        "generatedAtUtc": datetime.now(timezone.utc).isoformat(),
        "sourceDirectory": str(planets_dir.resolve()),
        "sourcePage": "https://www.solarsystemscope.com/textures/",
        "licenseFile": str(license_path.resolve()) if license_path.is_file() else None,
        "licenseTextSha256": digest_file(license_path, "sha256") if license_path.is_file() else None,
        "creditsPreserved": bool(credits),
        "assets": assets,
    }


def load_spice() -> Any:
    try:
        import spiceypy as spice
    except ImportError as exc:
        raise RuntimeError(
            "spiceypy no està instal·lat; executeu pip install -r tools/requirements-solar-system.txt"
        ) from exc
    return spice


def spice_coverage(spice: Any, path: Path, body_id: int) -> tuple[float, float] | None:
    window = spice.utils.support_types.SPICEDOUBLE_CELL(20_000)
    spice.spkcov(str(path), body_id, window)
    if spice.wncard(window) == 0:
        return None
    return float(spice.wnfetd(window, 0)[0]), float(spice.wnfetd(window, spice.wncard(window) - 1)[1])


def frame_and_radii(spice: Any, naif_id: int, display_name: str, et: float) -> tuple[str | None, list[float] | None]:
    frame = "MOON_ME_DE421" if naif_id == 301 else "IAU_" + re.sub(
        r"[^A-Z0-9]+", "_", display_name.upper()
    ).strip("_")
    try:
        spice.pxform(frame, "J2000", et)
    except Exception:
        frame = None
    try:
        _, radii = spice.bodvcd(naif_id, "RADII", 3)
        radii_value = [float(value) for value in radii]
    except Exception:
        radii_value = None
    return frame, radii_value


def build_catalog(
    discovery: list[dict[str, Any]],
    physical: dict[int, dict[str, Any]],
    summaries: dict[str, KernelSummary],
    kernel_paths: dict[str, Path],
    pck_path: Path,
    lsk_path: Path,
    lunar_frame_path: Path | None,
    lunar_bpc_path: Path | None,
    acquisition_date: str,
) -> dict[str, Any]:
    spice = load_spice()
    spice.kclear()
    spice.furnsh(str(lsk_path))
    spice.furnsh(str(pck_path))
    if lunar_frame_path is not None and lunar_bpc_path is not None:
        spice.furnsh(str(lunar_frame_path))
        spice.furnsh(str(lunar_bpc_path))
    et = float(spice.str2et("2026-07-09T00:00:00"))

    name_to_naif: dict[str, int] = {"moon": 301}
    body_kernels: dict[int, list[str]] = {301: ["de440s.bsp"]}
    for file_name, summary in summaries.items():
        if file_name not in kernel_paths:
            continue
        for naif_id, name in summary.body_names.items():
            name_to_naif[normalized_name(name)] = naif_id
            body_kernels.setdefault(naif_id, []).append(file_name)

    moon = {
        "iauNumber": None,
        "name": "Moon",
        "provisionalDesignation": None,
        "displayName": "Moon",
        "parentNaifId": 399,
        "parentId": "earth",
        "discoveryYear": None,
    }
    rows = [moon, *discovery]
    catalog_entries = []
    for row in rows:
        key = normalized_name(row["name"] or row["provisionalDesignation"] or "")
        naif_id = name_to_naif.get(key)
        kernels = sorted(set(body_kernels.get(naif_id, []))) if naif_id is not None else []
        coverage = []
        for kernel in kernels:
            path = kernel_paths.get(kernel)
            if path is None or naif_id is None:
                continue
            interval = spice_coverage(spice, path, naif_id)
            if interval is not None:
                coverage.append(interval)
        coverage_start = min((item[0] for item in coverage), default=None)
        coverage_end = max((item[1] for item in coverage), default=None)
        frame, pck_radii = (None, None)
        if naif_id is not None:
            frame, pck_radii = frame_and_radii(spice, naif_id, row["displayName"], et)
        physical_data = physical.get(naif_id or -1, {})
        mean_radius = physical_data.get("meanRadiusKm")
        if pck_radii is not None:
            mean_radius = (pck_radii[0] * pck_radii[1] * pck_radii[2]) ** (1.0 / 3.0)
        ephemeris_quality = "HIGH_PRECISION" if kernels else "UNAVAILABLE"
        entry = {
            **row,
            "id": (
                f"naif-{naif_id}"
                if naif_id is not None
                else f"provisional-{normalized_name(row['displayName'])}"
            ),
            "naifId": naif_id,
            "spkKernelIds": kernels,
            "spkCoverageStartET": coverage_start,
            "spkCoverageEndET": coverage_end,
            "bodyFixedFrame": frame,
            "hasOrientationModel": frame is not None,
            "orientationSource": "MOON_ME_DE421" if naif_id == 301 and frame else "IAU PCK pck00011" if frame else None,
            "radiiKm": pck_radii,
            "meanRadiusKm": mean_radius,
            "physicalParameterSource": "NAIF PCK pck00011" if pck_radii else "JPL SSD physical parameters" if mean_radius else None,
            "textureResourceId": None,
            "textureQuality": "UNAVAILABLE",
            "shapeQuality": "IAU_MODEL" if pck_radii else "MEASURED" if mean_radius else "UNAVAILABLE",
            "orientationQuality": "IAU_MODEL" if frame else "UNAVAILABLE",
            "ephemerisQuality": ephemeris_quality,
            "coverageStatusAtSnapshot": (
                "IN_RANGE"
                if coverage_start is not None and coverage_start <= et <= (coverage_end or coverage_start)
                else "OUT_OF_RANGE" if kernels else "NO_KERNEL"
            ),
        }
        catalog_entries.append(entry)
    spice.kclear()

    counts: dict[str, int] = {}
    for entry in catalog_entries:
        counts[entry["parentId"]] = counts.get(entry["parentId"], 0) + 1
    return {
        "catalogVersion": CATALOG_VERSION,
        "catalogDate": CATALOG_DATE,
        "acquiredAtUtc": f"{acquisition_date}T00:00:00Z",
        "sources": {
            "catalog": JPL_DISCOVERY_URL,
            "physicalParameters": JPL_PHYSICAL_URL,
            "kernelInventory": f"{SATELLITE_ROOT}/aa_summaries.txt",
        },
        "counts": {"total": len(catalog_entries), "byParent": counts},
        "coverage": {
            "withSpk": sum(bool(item["spkKernelIds"]) for item in catalog_entries),
            "withOrientation": sum(item["hasOrientationModel"] for item in catalog_entries),
            "withRadius": sum(item["meanRadiusKm"] is not None for item in catalog_entries),
            "withTexture": 0,
            "withoutSpk": [
                item["displayName"] for item in catalog_entries if not item["spkKernelIds"]
            ],
        },
        "satellites": catalog_entries,
    }


def kernel_type(path: Path) -> str:
    return {
        ".bsp": "SPK",
        ".tpc": "PCK",
        ".bpc": "PCK",
        ".tls": "LSK",
        ".tf": "FK",
    }.get(path.suffix.lower(), "UNKNOWN")


def build_kernel_manifest(
    installed: list[tuple[str, str, Path, str | None]],
    summaries: dict[str, KernelSummary],
    acquisition_date: str,
) -> dict[str, Any]:
    records = []
    for index, (file_name, url, path, official_md5) in enumerate(installed):
        summary = summaries.get(file_name)
        normalized = path.as_posix()
        if "/kernels/" in normalized:
            relative_path = normalized.split("/kernels/", 1)[-1]
            relative_base = "kernels"
        else:
            relative_path = "/".join(path.parts[-3:])
            relative_base = "sky"
        records.append(
            {
                "kernelId": path.stem,
                "fileName": file_name,
                "kernelType": kernel_type(path),
                "sourceUrl": url,
                "officialMd5": official_md5,
                "sha256": digest_file(path, "sha256"),
                "byteSize": path.stat().st_size,
                "coverage": list(summary.coverage_text) if summary and summary.coverage_text else None,
                "bodyIds": sorted(summary.body_names) if summary else [],
                "priority": index,
                "compatibleEphemerisFamily": "DE440" if path.suffix.lower() == ".bsp" else None,
                "installed": True,
                "relativeBase": relative_base,
                "relativePath": relative_path,
            }
        )
    generation_source = "\n".join(item["sha256"] for item in records).encode("ascii")
    return {
        "manifestVersion": f"solar-system-kernels-{acquisition_date}",
        "generatedAtUtc": datetime.now(timezone.utc).isoformat(),
        "aberrationPolicy": "LT+S",
        "inertialFrame": "J2000/ICRF",
        "earthFixedFrame": "ITRF93",
        "kernelGeneration": hashlib.sha256(generation_source).hexdigest()[:16],
        "sources": {
            "naif": f"{NAIF_ROOT}/",
            "satelliteChecksums": f"{SATELLITE_ROOT}/aa_checksums.txt",
            "planetChecksums": f"{PLANET_ROOT}/aa_checksums.txt",
        },
        "kernels": records,
    }


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)
    log("manifest", f"Escrit file={path} bytes={path.stat().st_size}")


def copy_evidence(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)
    log("evidence", f"Actualitzat file={destination}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-root", type=Path)
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--skip-downloads", action="store_true")
    parser.add_argument("--date", default=datetime.now(timezone.utc).date().isoformat())
    args = parser.parse_args()

    data_root = (args.data_root or resolve_data_root()).expanduser().resolve(strict=False)
    repo_root = args.repo_root.resolve()
    solar_root = data_root / "data" / "sky" / "solar-system"
    kernels_root = solar_root / "kernels"
    manifests_root = kernels_root / "manifests"
    planets_dir = solar_root / "planets"
    if not planets_dir.is_dir():
        raise FileNotFoundError(f"No existeix el directori de textures: {planets_dir}")

    log("start", f"data_root={data_root} repo_root={repo_root}")
    satellite_checksums = parse_checksums(fetch_text(f"{SATELLITE_ROOT}/aa_checksums.txt"))
    planet_checksums = parse_checksums(fetch_text(f"{PLANET_ROOT}/aa_checksums.txt"))
    summary_text = fetch_text(f"{SATELLITE_ROOT}/aa_summaries.txt")
    summaries = parse_kernel_summaries(summary_text)

    installed: list[tuple[str, str, Path, str | None]] = []
    for relative_dir, file_name, url in SMALL_KERNELS:
        destination = kernels_root / relative_dir / file_name
        expected = planet_checksums.get(file_name)
        if not args.skip_downloads:
            download_file(url, destination, expected)
        if destination.is_file():
            installed.append((file_name, url, destination, expected))
    for file_name in SATELLITE_KERNELS:
        url = f"{SATELLITE_ROOT}/{file_name}"
        destination = kernels_root / "spk" / "satellites" / file_name
        expected = satellite_checksums.get(file_name)
        if not args.skip_downloads:
            download_file(url, destination, expected)
        if destination.is_file():
            installed.append((file_name, url, destination, expected))

    lunar_dir = data_root / "data" / "sky" / "moon" / "orientation"
    lunar_frame = lunar_dir / "moon_080317.tf"
    lunar_bpc = lunar_dir / "moon_pa_de421_1900-2050.bpc"
    for path, source in (
        (lunar_frame, "https://naif.jpl.nasa.gov/pub/naif/generic_kernels/fk/satellites/moon_080317.tf"),
        (lunar_bpc, "https://naif.jpl.nasa.gov/pub/naif/generic_kernels/pck/moon_pa_de421_1900-2050.bpc"),
    ):
        if path.is_file():
            installed.append((path.name, source, path, None))

    kernel_paths = {file_name: path for file_name, _, path, _ in installed}
    discovery_text = fetch_text(JPL_DISCOVERY_URL)
    physical_text = fetch_text(JPL_PHYSICAL_URL)
    catalog = build_catalog(
        parse_discovery_catalog(discovery_text),
        parse_physical_parameters(physical_text),
        summaries,
        kernel_paths,
        kernels_root / "pck" / "pck00011.tpc",
        kernels_root / "lsk" / "naif0012.tls",
        lunar_frame if lunar_frame.is_file() else None,
        lunar_bpc if lunar_bpc.is_file() else None,
        args.date,
    )
    if catalog["counts"]["total"] != 461:
        raise RuntimeError(f"El catàleg no conté 461 satèl·lits: {catalog['counts']}")
    expected_counts = {
        "earth": 1, "mars": 2, "jupiter": 115, "saturn": 293,
        "uranus": 29, "neptune": 16, "pluto": 5,
    }
    if catalog["counts"]["byParent"] != expected_counts:
        raise RuntimeError(f"Recomptes inesperats: {catalog['counts']['byParent']}")

    texture_manifest = build_texture_manifest(planets_dir, args.date)
    kernel_manifest = build_kernel_manifest(installed, summaries, args.date)
    catalog_path = manifests_root / "satellite_catalog.json"
    texture_path = manifests_root / "planet_texture_manifest.json"
    kernel_path = manifests_root / "kernel_manifest.json"
    write_json(catalog_path, catalog)
    write_json(texture_path, texture_manifest)
    write_json(kernel_path, kernel_manifest)

    evidence_root = repo_root / "backend" / "src" / "terralab3d" / "data" / "solar_system"
    copy_evidence(catalog_path, evidence_root / "satellite_catalog_2026-07-09.json")
    copy_evidence(texture_path, evidence_root / "planet_texture_manifest.json")
    copy_evidence(kernel_path, evidence_root / "kernel_manifest.json")
    log(
        "complete",
        " ".join(
            (
                f"catalogats={catalog['counts']['total']}",
                f"amb_spk={catalog['coverage']['withSpk']}",
                f"amb_orientacio={catalog['coverage']['withOrientation']}",
                f"amb_radi={catalog['coverage']['withRadius']}",
                f"textures={len(texture_manifest['assets'])}",
                f"kernels={len(kernel_manifest['kernels'])}",
            )
        ),
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
