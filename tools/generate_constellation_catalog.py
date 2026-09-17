"""Regenera el catàleg empaquetat de constel·lacions del Pas 23.

La xarxa només s'utilitza durant la regeneració explícita. El runtime carrega el
JSON inclòs al paquet i valida la seva versió i cardinalitat.
"""

from __future__ import annotations

import hashlib
import json
import math
import urllib.request
from pathlib import Path

import numpy as np
from astropy.coordinates import FK5, ICRS, SkyCoord
from astropy.time import Time
import astropy.units as u


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "backend/src/terralab3d/infrastructure/catalogs/constellations.v1.json"
COMMIT = "7e720a3de062059d4c5400a379146a601d9010e0"
BASE_URL = f"https://raw.githubusercontent.com/ofrohn/d3-celestial/{COMMIT}/data"
SOURCE_URLS = {
    "lines": f"{BASE_URL}/constellations.lines.json",
    "names": f"{BASE_URL}/constellations.json",
}
SOURCE_SHA256 = {
    "lines": "294f66bef5d5cf50b1e17f16d2efa1d97a15131612c68dd935adef6e7373e13c",
    "names": "ab4ae692027cbc042c0d6791a84456a65eb7c55656107fd00c58ff6e55d4d8b2",
}
MAX_ARC_STEP_DEG = 1.0
IAU_CONSTELLATION_IDS = frozenset(
    "And Ant Aps Aql Aqr Ara Ari Aur Boo CMa CMi CVn Cae Cam Cap Car Cas Cen Cep Cet "
    "Cha Cir Cnc Col Com CrA CrB Crt Cru Crv Cyg Del Dor Dra Equ Eri For Gem Gru Her "
    "Hor Hya Hyi Ind LMi Lac Leo Lep Lib Lup Lyn Lyr Men Mic Mon Mus Nor Oct Oph Ori "
    "Pav Peg Per Phe Pic PsA Psc Pup Pyx Ret Scl Sco Sct Ser Sex Sge Sgr Tau Tel TrA "
    "Tri Tuc UMa UMi Vel Vir Vol Vul".split()
)


def _download(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": "TerraLab3D-catalog-generator/1"})
    with urllib.request.urlopen(request, timeout=30) as response:
        return response.read()


def _icrs_direction(ra_deg: float, dec_deg: float) -> np.ndarray:
    source = SkyCoord(
        ra=(ra_deg % 360.0) * u.deg,
        dec=dec_deg * u.deg,
        frame=FK5(equinox=Time("J2000")),
    ).transform_to(ICRS())
    ra = source.ra.to_value(u.rad)
    dec = source.dec.to_value(u.rad)
    return np.asarray((math.cos(dec) * math.cos(ra), math.cos(dec) * math.sin(ra), math.sin(dec)))


def _coordinate(direction: np.ndarray) -> list[float]:
    unit = direction / np.linalg.norm(direction)
    return [
        round(math.degrees(math.atan2(float(unit[1]), float(unit[0]))) % 360.0, 8),
        round(math.degrees(math.asin(float(np.clip(unit[2], -1.0, 1.0)))), 8),
    ]


def _slerp(a: np.ndarray, b: np.ndarray, fraction: float) -> np.ndarray:
    dot = float(np.clip(np.dot(a, b), -1.0, 1.0))
    angle = math.acos(dot)
    if angle < 1e-12:
        return a.copy()
    scale = math.sin(angle)
    return (math.sin((1.0 - fraction) * angle) / scale) * a + (math.sin(fraction * angle) / scale) * b


def _sample_stroke(raw_stroke: list[list[float]]) -> tuple[list[list[float]], list[np.ndarray]]:
    directions = [_icrs_direction(float(point[0]), float(point[1])) for point in raw_stroke]
    sampled: list[np.ndarray] = []
    for index, (start, end) in enumerate(zip(directions, directions[1:])):
        angle_deg = math.degrees(math.acos(float(np.clip(np.dot(start, end), -1.0, 1.0))))
        segment_count = max(1, math.ceil(angle_deg / MAX_ARC_STEP_DEG))
        if index == 0:
            sampled.append(start)
        sampled.extend(_slerp(start, end, step / segment_count) for step in range(1, segment_count + 1))
    if len(directions) == 1:
        sampled = directions
    return [_coordinate(direction) for direction in sampled], sampled


def build_catalog(lines_bytes: bytes, names_bytes: bytes) -> dict[str, object]:
    lines = json.loads(lines_bytes)
    names = json.loads(names_bytes)
    line_features = lines.get("features", [])
    name_features = names.get("features", [])
    if len(line_features) != 89 or len(name_features) != 89:
        raise ValueError("d3-celestial ha de contenir 89 figures font abans de fusionar Serpens")

    entries: dict[str, dict[str, object]] = {}
    samples_by_id: dict[str, list[np.ndarray]] = {}
    for source_index, (line_feature, name_feature) in enumerate(zip(line_features, name_features, strict=True)):
        abbreviation = str(line_feature["id"])
        if abbreviation != str(name_feature["id"]):
            raise ValueError(f"fonts desalineades a l'índex {source_index}")
        source_name = str(name_feature["properties"]["name"])
        component_id = "main"
        if abbreviation == "Ser":
            component_id = "caput" if "Caput" in source_name else "cauda"
        rank = int(line_feature["properties"]["rank"])
        strokes: list[list[list[float]]] = []
        component_samples: list[np.ndarray] = []
        for raw_stroke in line_feature["geometry"]["coordinates"]:
            stroke, samples = _sample_stroke(raw_stroke)
            strokes.append(stroke)
            component_samples.extend(samples)
        entry = entries.setdefault(
            abbreviation,
            {
                "id": abbreviation,
                "name": "Serpens" if abbreviation == "Ser" else str(name_feature["properties"]["la"]),
                "frame": "ICRS",
                "center": None,
                "angularRadiusDeg": None,
                "visualComponents": [],
            },
        )
        entry["visualComponents"].append(
            {"componentId": component_id, "sourceName": source_name, "rank": rank, "strokes": strokes}
        )
        samples_by_id.setdefault(abbreviation, []).extend(component_samples)

    if set(entries) != IAU_CONSTELLATION_IDS:
        missing = sorted(IAU_CONSTELLATION_IDS - set(entries))
        extra = sorted(set(entries) - IAU_CONSTELLATION_IDS)
        raise ValueError(f"identitats IAU invàlides: absents={missing}; sobrants={extra}")

    for abbreviation, entry in entries.items():
        samples = samples_by_id[abbreviation]
        centre = np.sum(samples, axis=0)
        norm = float(np.linalg.norm(centre))
        if norm <= 1e-12:
            raise ValueError(f"centre vectorial degenerat per {abbreviation}")
        centre /= norm
        entry["center"] = _coordinate(centre)
        entry["angularRadiusDeg"] = round(
            max(math.degrees(math.acos(float(np.clip(np.dot(centre, sample), -1.0, 1.0)))) for sample in samples),
            8,
        )

    return {
        "schemaVersion": 1,
        "catalogVersion": f"d3-celestial-{COMMIT[:12]}-icrs-v1",
        "source": {
            "project": "d3-celestial",
            "commit": COMMIT,
            "sourceFrame": "FK5_J2000",
            "frame": "ICRS",
            "maxArcStepDeg": MAX_ARC_STEP_DEG,
            "files": [
                {"url": SOURCE_URLS["lines"], "sha256": hashlib.sha256(lines_bytes).hexdigest()},
                {"url": SOURCE_URLS["names"], "sha256": hashlib.sha256(names_bytes).hexdigest()},
            ],
        },
        "constellations": [entries[key] for key in sorted(entries)],
    }


def main() -> None:
    lines_bytes = _download(SOURCE_URLS["lines"])
    names_bytes = _download(SOURCE_URLS["names"])
    downloaded = {"lines": lines_bytes, "names": names_bytes}
    for source_name, source_bytes in downloaded.items():
        actual_hash = hashlib.sha256(source_bytes).hexdigest()
        if actual_hash != SOURCE_SHA256[source_name]:
            raise ValueError(
                f"hash inesperat per {source_name}: {actual_hash}; "
                f"s'esperava {SOURCE_SHA256[source_name]}"
            )
    catalog = build_catalog(lines_bytes, names_bytes)
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(
        json.dumps(catalog, ensure_ascii=False, indent=2, sort_keys=False) + "\n",
        encoding="utf-8",
    )
    print(f"Catàleg generat: {OUTPUT} ({len(catalog['constellations'])} constel·lacions)")


if __name__ == "__main__":
    main()
