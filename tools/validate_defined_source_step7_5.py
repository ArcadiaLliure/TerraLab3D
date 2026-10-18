"""Contrasta SourceModel S amb taules CIE verificades, sense observacions L3.

Els watts de les fixtures són definicions d'entrada, no estimacions d'una
ciutat. Aquest script només llegeix assets de la biblioteca configurada.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import sys
from pathlib import Path

import numpy as np


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "backend" / "src"))

from terralab3d.domain.light_pollution.source_model import (  # noqa: E402
    AngularEmissionProfile,
    AzimuthalAngularEmissionProfile,
    DefinedSpectrum,
    EmissionAmplitude,
    GeodeticPosition,
    PointSourceGeometry,
    RectangularAreaGeometry,
    SourceModel,
    SourceModelEnsemble,
    mix_defined_spectra,
)
from terralab3d.infrastructure.app_paths import resolve_data_root  # noqa: E402


MANIFEST_PATH = REPO_ROOT / "docs/evidencies/pas7.4/cie-asset-manifest.json"


def _load_cie_spectrum(entry: dict[str, str], root: Path, column: int, spectrum_id: str) -> DefinedSpectrum:
    path = root / entry["file"]
    raw = path.read_bytes()
    if hashlib.md5(raw).hexdigest() != entry["publishedMd5"]:
        raise ValueError(f"MD5 publicat incorrecte: {entry['file']}")
    if hashlib.sha256(raw).hexdigest() != entry["sha256"]:
        raise ValueError(f"SHA-256 local incorrecte: {entry['file']}")
    with path.open(encoding="utf-8-sig", newline="") as stream:
        rows = [tuple(float(value) for value in row) for row in csv.reader(stream)]
    return DefinedSpectrum(
        spectrum_id=spectrum_id,
        evidence_reference=entry["sourcePage"],
        license="CC BY-SA 4.0 (manifest CIE 7.4)",
        wavelengths_nm=tuple(row[0] for row in rows),
        relative_power=tuple(row[column] for row in rows),
        asset_sha256=entry["sha256"],
        origin_kind="published_table",
    )


def _angular_integral(profile: AngularEmissionProfile | AzimuthalAngularEmissionProfile) -> float:
    nodes, weights = np.polynomial.legendre.leggauss(96)
    cosines = (nodes + 1) / 2
    azimuths = (nodes + 1) * 180
    total = math.fsum(
        float(weight_mu * weight_az) * profile.density_per_sr(
            math.degrees(math.acos(float(cosine))), float(azimuth),
        )
        for cosine, weight_mu in zip(cosines, weights)
        for azimuth, weight_az in zip(azimuths, weights)
    )
    return total * math.pi / 2


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    entries = {entry["file"]: entry for entry in manifest["assets"]}
    root = resolve_data_root() / "data/earth/light-pollution/spectral-oracle/cie"
    led = _load_cie_spectrum(entries["CIE_illum_LEDs_1nm.csv"], root, 1, "CIE_LED_B1_reference")
    discharge = _load_cie_spectrum(entries["CIE_illum_HPs.csv"], root, 1, "CIE_HP1_reference")
    mixture = mix_defined_spectra("LED_B1_HP1_equal_shape", ((led, 1.0), (discharge, 1.0)), "fixture 7.5")
    axial = AngularEmissionProfile("axial_uniform_fixture", "fixture analítica 7.5", (0.0, 90.0), (1.0, 1.0))
    anisotropic = AzimuthalAngularEmissionProfile(
        "azimuth_fixture", "fixture analítica 7.5", axial,
        (0.0, 90.0, 180.0, 270.0, 360.0), (1.0, 2.0, 1.0, 0.0, 1.0),
    )
    position = GeodeticPosition(41.38, 2.17, 25.0)
    point = SourceModel(
        "defined_point_cie_led_b1", "v1", "fixture CIE relativa + 1 W ascendent definit",
        PointSourceGeometry(position), led, axial,
        EmissionAmplitude(1.0, "W", "defined_absolute", "fixture d'entrada: 1 W definit"),
    )
    area = SourceModel(
        "defined_area_cie_mix", "v1", "fixture CIE relativa + escala paramètrica",
        RectangularAreaGeometry(position, 10.0, 20.0), mixture, anisotropic,
        EmissionAmplitude(1.0, "relative", "parametric", "fixture d'escenari", "P_area"),
    )
    ensemble = SourceModelEnsemble("two_defined_alternatives", (point, area))
    result = {
        "schemaVersion": 1,
        "domain": "S_DEFINED_SOURCE_ONLY",
        "cieManifest": str(MANIFEST_PATH.relative_to(REPO_ROOT)).replace("\\", "/"),
        "externalAssets": [
            {"file": entry["file"], "sha256": entry["sha256"], "publishedMd5": entry["publishedMd5"]}
            for entry in (entries["CIE_illum_LEDs_1nm.csv"], entries["CIE_illum_HPs.csv"])
        ],
        "spectra": [
            {
                "spectrumId": spectrum.spectrum_id,
                "knots": len(spectrum.wavelengths_nm),
                "independentNormalizedIntegral": float(np.trapezoid(
                    [spectrum.density_per_nm(wavelength) for wavelength in spectrum.wavelengths_nm],
                    spectrum.wavelengths_nm,
                )),
                "inputIsRelative": True,
            }
            for spectrum in (led, discharge, mixture)
        ],
        "angularIndependentIntegral": {
            "axial": _angular_integral(axial),
            "anisotropic": _angular_integral(anisotropic),
        },
        "models": [
            {"sourceModelId": model.source_model_id, "sourceMode": model.source_mode,
             "absoluteCalibrationStatus": model.amplitude.absolute_calibration_status,
             "spectralFluxUnit": model.spectral_flux(500.0).unit}
            for model in ensemble.alternatives
        ],
        "assertionBoundary": "CIE shapes and fixture geometry/power only; no VIIRS, L3, city, atmospheric transport or product accuracy",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
