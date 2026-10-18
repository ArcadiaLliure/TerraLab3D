"""Diagnòstic espectral reproduïble del Pas 7.4, sense selecció de bandes.

Llegeix assets externs de la biblioteca de dades configurada. La sortida és
diagnòstica: ni les RSR històriques ni la convergència numèrica estableixen
un pressupost PASS/FAIL per al producte skyglow.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
from datetime import date
from pathlib import Path
from typing import Any

import numpy as np


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "backend" / "src"))

from terralab3d.domain.light_pollution.spectral_oracle import (  # noqa: E402
    DIMENSIONLESS_UNIT,
    RELATIVE_UNIT,
    SpectralCurve,
    integrate_spectral_product,
)
from terralab3d.infrastructure.app_paths import resolve_data_root  # noqa: E402
from terralab3d.infrastructure.adapters.light_pollution.viirs_rsr import (  # noqa: E402
    LocalViirsSpectralResponseRepository,
)


def _hashes(path: Path) -> tuple[str, str]:
    data = path.read_bytes()
    return hashlib.md5(data).hexdigest(), hashlib.sha256(data).hexdigest()


def _rows(path: Path) -> list[tuple[float, ...]]:
    with path.open(encoding="utf-8-sig", newline="") as stream:
        return [tuple(float(value) for value in row) for row in csv.reader(stream)]


def _curve(
    path: Path,
    source_id: str,
    column: int,
    *,
    unit: str,
    zero_outside: bool,
) -> SpectralCurve:
    rows = _rows(path)
    return SpectralCurve(
        source_id=source_id,
        wavelengths_nm=tuple(row[0] for row in rows),
        values=tuple(row[column] for row in rows),
        unit=unit,
        outside_support="zero" if zero_outside else "unavailable",
    )


def _integral(source: SpectralCurve, response: SpectralCurve, order: int = 8) -> float:
    return integrate_spectral_product(source, (response,), 380.0, 780.0, quadrature_order=order).value


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, help="Fitxer JSON UTF-8 per a l'evidència")
    args = parser.parse_args()
    data_root = resolve_data_root() / "data" / "earth" / "light-pollution"
    cie_root = data_root / "spectral-oracle" / "cie"
    manifest_path = REPO_ROOT / "docs" / "evidencies" / "pas7.4" / "cie-asset-manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    verified: dict[str, Path] = {}
    for entry in manifest["assets"]:
        path = cie_root / entry["file"]
        metadata_path = cie_root / entry["metadataFile"]
        md5, sha256 = _hashes(path)
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        published_hashes = {item["hashMethod"]: item["checksum"] for item in metadata["checksums"]}
        if (md5, sha256) != (entry["publishedMd5"], entry["sha256"]):
            raise ValueError(f"Checksum local incorrecte: {path.name}")
        if published_hashes.get("md5") != md5 or published_hashes.get("sha256") != sha256:
            raise ValueError(f"Checksum CIE publicat discrepant: {path.name}")
        if metadata["datatableInfo"]["interpolationMethod"] != "linear":
            raise ValueError(f"Interpolació CIE desconeguda: {path.name}")
        if metadata["datatableInfo"]["extrapolationMethod"] != "zero":
            raise ValueError(f"Extrapolació CIE desconeguda: {path.name}")
        if metadata["datatableInfo"]["dataQuality"] != entry["quality"]:
            raise ValueError(f"Qualitat CIE discrepant: {path.name}")
        if not any(right.get("rightsIdentifier") == manifest["license"] for right in metadata["rightsList"]):
            raise ValueError(f"Llicència CIE discrepant: {path.name}")
        verified[entry["file"]] = path

    led = verified["CIE_illum_LEDs_1nm.csv"]
    hp = verified["CIE_illum_HPs.csv"]
    l41 = verified["CIE_RefSpectrum_L41.csv"]
    photopic = _curve(
        verified["CIE_sle_photopic.csv"], "CIE_photopic_V", 1,
        unit=DIMENSIONLESS_UNIT, zero_outside=True,
    )
    xyz_y = _curve(
        verified["CIE_xyz_1931_2deg.csv"], "CIE_1931_Y", 2,
        unit=DIMENSIONLESS_UNIT, zero_outside=True,
    )
    spds = [
        *(_curve(led, f"CIE_LED_{index}", index, unit=RELATIVE_UNIT, zero_outside=True) for index in range(1, 10)),
        *(_curve(hp, f"CIE_HP{index}", index, unit=RELATIVE_UNIT, zero_outside=True) for index in range(1, 6)),
        _curve(l41, "CIE_L41", 1, unit=RELATIVE_UNIT, zero_outside=True),
    ]
    # Mescles sintètiques d'àrea radiant visible igual, sense prevalença urbana.
    unity = SpectralCurve("unity", (380.0, 780.0), (1.0, 1.0), DIMENSIONLESS_UNIT)
    for first, second, name in (
        (spds[0], spds[9], "SYNTH_LED_B1_HP1_equal_visible_area"),
        (spds[6], spds[9], "SYNTH_LED_RGB1_HP1_equal_visible_area"),
    ):
        knots = sorted(set(first.wavelengths_nm) | set(second.wavelengths_nm))
        a = np.interp(knots, first.wavelengths_nm, first.values, left=0.0, right=0.0)
        b = np.interp(knots, second.wavelengths_nm, second.values, left=0.0, right=0.0)
        area_a = _integral(first, unity)
        area_b = _integral(second, unity)
        spds.append(SpectralCurve(
            name, tuple(knots), tuple(float(v) for v in (a / area_a + b / area_b) / 2),
            RELATIVE_UNIT, "zero",
        ))

    cases: list[dict[str, Any]] = []
    for source in spds:
        results = [_integral(source, photopic, order) for order in (4, 8, 16)]
        y_result = _integral(source, xyz_y)
        cases.append({
            "source": source.source_id,
            "photopicRelativeNm": results[1],
            "quadratureOrder4Vs16Abs": abs(results[0] - results[2]),
            "quadratureOrder8Vs16Abs": abs(results[1] - results[2]),
            "ciePhotopicVsXyzYAbs": abs(results[1] - y_result),
        })

    rsr_root = data_root / "viirs-rsr"
    rsr_manifests = [
        rsr_root / "noaa-ncc" / "manifest.json",
        rsr_root / "research" / "noaa-multisat" / "prepared" / "noaa-20-diagnostic-rsr.json",
        rsr_root / "research" / "noaa-multisat" / "prepared" / "noaa-21-diagnostic-rsr.json",
    ]
    rsrs: dict[str, SpectralCurve] = {}
    rsr_provenance: list[dict[str, str]] = []
    for manifest_file in rsr_manifests:
        payload = json.loads(manifest_file.read_text(encoding="utf-8"))
        repository = LocalViirsSpectralResponseRepository(manifest_file)
        for entry in payload["responses"]:
            if entry["gainStage"] == "HGS_proxy_MGS":
                continue  # Mateixa taula MGS, proxy documentat; no és una nova RSR.
            response = repository.resolve(
                platform=entry["platform"],
                product_id=entry["productId"],
                collection=entry["collection"],
                release_id=entry["releaseId"],
                gain_stage=entry["gainStage"],
                acquisition_date=date.fromisoformat(entry["validFrom"]),
                application=entry["application"],
            )
            key = f"{entry['platform']}_{entry['gainStage']}_{entry['releaseId']}"
            rsrs[key] = SpectralCurve(
                key,
                response.wavelengths_nm,
                response.relative_response,
                DIMENSIONLESS_UNIT,
            )
            rsr_provenance.append({
                "id": key,
                "sourceUrl": entry["sourceUrl"],
                "validFrom": entry["validFrom"],
                "validThrough": entry["validThrough"],
                "evidenceClass": entry.get("evidenceClass", "diagnostic_historical"),
                "l3LinkStatus": entry.get("l3LinkStatus", "unverified"),
                "sha256": response.local_sha256,
            })

    # Diagnòstic visible 380–780 nm: no representa la banda DNB completa.
    common_start = max(380.0, *(response.wavelengths_nm[0] for response in rsrs.values()))
    common_end = min(780.0, *(response.wavelengths_nm[-1] for response in rsrs.values()))
    rsr_cases: list[dict[str, Any]] = []
    for source in (spds[0], spds[6], spds[9], spds[11], spds[14]):
        values: dict[str, float] = {}
        for key, response in rsrs.items():
            denominator = integrate_spectral_product(
                SpectralCurve("unity", (common_start, common_end), (1.0, 1.0), RELATIVE_UNIT),
                (response,), common_start, common_end,
            ).value
            numerator = integrate_spectral_product(source, (response,), common_start, common_end).value
            values[key] = numerator / denominator
        rsr_cases.append({"source": source.source_id, "commonVisibleNormalizedResponse": values})

    result = json.dumps({
        "scope": "diagnostic_only_no_bandset_candidate_no_pass_fail",
        "domainNm": [380, 780],
        "rsrCommonVisibleDomainNm": [common_start, common_end],
        "cieFilesVerified": sorted(verified),
        "cieSpdCases": cases,
        "rsrProvenance": rsr_provenance,
        "rsrVisibleOnlyCases": rsr_cases,
        "limitations": [
            "CIE SPDs are relative and approximated, not measured site emissions",
            "HP tables have 5 nm grid; sub-grid narrow lines are not recovered",
            "CIE source support ends at 780/830 nm, so DNB full-band response is not characterized",
            "All RSRs are historical or at-launch diagnostic curves, not verified 2026 Black Marble L3 responses",
            "No atmosphere, gas absorption, SQM/TESS response, or product error budget is included",
        ],
    }, ensure_ascii=False, indent=2)
    if args.output:
        args.output.write_text(result + "\n", encoding="utf-8")
    else:
        print(result)


if __name__ == "__main__":
    main()
