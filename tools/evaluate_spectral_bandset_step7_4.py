"""Avalua les bandes del Pas 7.4 amb el criteri V3 congelat prèviament.

No descarrega assets. Compara cada cas declarat individualment; els màxims no
es substitueixen per una mitjana i els temps no intervenen en la selecció.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from bisect import bisect_right
from datetime import date
from decimal import Decimal, localcontext
from pathlib import Path
from typing import Any

import numpy as np


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "backend" / "src"))

from terralab3d.domain.light_pollution.spectral_bandset import (  # noqa: E402
    STRATEGY_ID,
    build_spectral_band_set,
    integrate_band_set,
)
from terralab3d.domain.light_pollution.spectral_oracle import (  # noqa: E402
    DIMENSIONLESS_UNIT,
    RELATIVE_UNIT,
    SpectralCurve,
    integrate_spectral_product,
)
from terralab3d.infrastructure.adapters.light_pollution.viirs_rsr import (  # noqa: E402
    LocalViirsSpectralResponseRepository,
)
from terralab3d.infrastructure.app_paths import resolve_data_root  # noqa: E402


CRITERION_PATH = REPO_ROOT / "docs" / "evidencies" / "pas7.4" / "criteri-preregistrat-v1.json"
MANIFEST_PATH = REPO_ROOT / "docs" / "evidencies" / "pas7.4" / "cie-asset-manifest.json"


def _load_cie(root: Path) -> tuple[list[SpectralCurve], list[SpectralCurve]]:
    import csv

    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    rows_by_file: dict[str, list[tuple[float, ...]]] = {}
    for entry in manifest["assets"]:
        path = root / entry["file"]
        raw = path.read_bytes()
        if hashlib.md5(raw).hexdigest() != entry["publishedMd5"]:
            raise ValueError(f"MD5 CIE incorrecte: {path.name}")
        if hashlib.sha256(raw).hexdigest() != entry["sha256"]:
            raise ValueError(f"SHA-256 CIE incorrecte: {path.name}")
        with path.open(encoding="utf-8-sig", newline="") as stream:
            rows_by_file[entry["file"]] = [tuple(float(value) for value in row) for row in csv.reader(stream)]

    def curve(filename: str, column: int, name: str, unit: str) -> SpectralCurve:
        rows = rows_by_file[filename]
        return SpectralCurve(name, tuple(row[0] for row in rows), tuple(row[column] for row in rows), unit, "zero")

    spds = [
        *(curve("CIE_illum_LEDs_1nm.csv", index, f"CIE_LED_{index}", RELATIVE_UNIT) for index in range(1, 10)),
        *(curve("CIE_illum_HPs.csv", index, f"CIE_HP{index}", RELATIVE_UNIT) for index in range(1, 6)),
        curve("CIE_RefSpectrum_L41.csv", 1, "CIE_L41", RELATIVE_UNIT),
    ]
    responses = [
        curve("CIE_sle_photopic.csv", 1, "CIE_photopic_V", DIMENSIONLESS_UNIT),
        *(curve("CIE_xyz_1931_2deg.csv", index, f"CIE_XYZ_{'XYZ'[index - 1]}", DIMENSIONLESS_UNIT)
          for index in range(1, 4)),
    ]
    unity = SpectralCurve("unity", (380.0, 780.0), (1.0, 1.0), DIMENSIONLESS_UNIT)
    for first, second, name in (
        (spds[0], spds[9], "SYNTH_LED_B1_HP1_equal_visible_area"),
        (spds[6], spds[9], "SYNTH_LED_RGB1_HP1_equal_visible_area"),
    ):
        knots = sorted(set(first.wavelengths_nm) | set(second.wavelengths_nm))
        a = np.interp(knots, first.wavelengths_nm, first.values, left=0.0, right=0.0)
        b = np.interp(knots, second.wavelengths_nm, second.values, left=0.0, right=0.0)
        area_a = integrate_spectral_product(first, (unity,), 380.0, 780.0).value
        area_b = integrate_spectral_product(second, (unity,), 380.0, 780.0).value
        spds.append(SpectralCurve(name, tuple(knots), tuple(float(v) for v in (a / area_a + b / area_b) / 2), RELATIVE_UNIT, "zero"))
    for center, half_width in ((435.25, 0.5), (500.005, 0.005), (589.02, 0.05), (700.005, 0.005)):
        spds.append(SpectralCurve(
            f"SYNTH_TRIANGLE_{center}_{half_width}",
            (380.0, center - half_width, center, center + half_width, 780.0),
            (0.0, 0.0, 1.0, 0.0, 0.0), RELATIVE_UNIT,
        ))
    spds.append(SpectralCurve("SYNTH_ZERO", (380.0, 780.0), (0.0, 0.0), RELATIVE_UNIT))
    return spds, responses


def _load_diagnostic_rsr(root: Path) -> list[SpectralCurve]:
    paths = (
        root / "noaa-ncc" / "manifest.json",
        root / "research" / "noaa-multisat" / "prepared" / "noaa-20-diagnostic-rsr.json",
        root / "research" / "noaa-multisat" / "prepared" / "noaa-21-diagnostic-rsr.json",
    )
    responses = []
    for manifest_path in paths:
        repository = LocalViirsSpectralResponseRepository(manifest_path)
        for entry in json.loads(manifest_path.read_text(encoding="utf-8"))["responses"]:
            if entry["gainStage"] == "HGS_proxy_MGS":
                continue
            rsr = repository.resolve(
                platform=entry["platform"], product_id=entry["productId"],
                collection=entry["collection"], release_id=entry["releaseId"],
                gain_stage=entry["gainStage"], acquisition_date=date.fromisoformat(entry["validFrom"]),
                application=entry["application"],
            )
            responses.append(SpectralCurve(
                f"DIAGNOSTIC_{rsr.platform}_{rsr.gain_stage}_{rsr.release_id}_{rsr.local_sha256}",
                rsr.wavelengths_nm, rsr.relative_response, DIMENSIONLESS_UNIT,
            ))
    return responses


def _decimal_exact(
    source: SpectralCurve,
    responses: tuple[SpectralCurve, ...],
    start: float,
    end: float,
) -> Decimal:
    """Integra el polinomi per interval amb 50 xifres, independent de Simpson/Gauss."""
    curves = (source, *responses)
    knots = sorted({start, end} | {
        x for curve in curves for x in curve.wavelengths_nm if start < x < end
    })
    decimal_curves = [
        (tuple(Decimal(str(x)) for x in curve.wavelengths_nm),
         tuple(Decimal(str(v)) for v in curve.values), curve.outside_support)
        for curve in curves
    ]
    with localcontext() as context:
        context.prec = 50
        total = Decimal(0)
        for left_float, right_float in zip(knots, knots[1:]):
            left, right = Decimal(str(left_float)), Decimal(str(right_float))
            mid = (left + right) / 2
            polynomial = [Decimal(1)]
            for x, y, outside in decimal_curves:
                if outside == "zero" and (mid < x[0] or mid > x[-1]):
                    polynomial = [Decimal(0)]
                    break
                index = min(max(bisect_right(x, mid) - 1, 0), len(x) - 2)
                slope = (y[index + 1] - y[index]) / (x[index + 1] - x[index])
                value_at_left = y[index] + slope * (left - x[index])
                delta = slope * (right - left)
                following = [Decimal(0)] * (len(polynomial) + 1)
                for power, coefficient in enumerate(polynomial):
                    following[power] += coefficient * value_at_left
                    following[power + 1] += coefficient * delta
                polynomial = following
            total += (right - left) * sum(
                (coefficient / Decimal(power + 1) for power, coefficient in enumerate(polynomial)),
                Decimal(0),
            )
        return +total


def _uniform_simpson(
    source: SpectralCurve,
    responses: tuple[SpectralCurve, ...],
    start: float,
    end: float,
    step_nm: float,
) -> float:
    nodes = np.arange(start, end, step_nm)
    knots = np.append(nodes, end)
    left, right = knots[:-1], knots[1:]
    mid = left + (right - left) / 2
    products = [np.ones_like(left), np.ones_like(left), np.ones_like(left)]
    for curve in (source, *responses):
        for product, points in zip(products, (left, mid, right)):
            product *= np.interp(
                points, curve.wavelengths_nm, curve.values,
                left=0.0 if curve.outside_support == "zero" else None,
                right=0.0 if curve.outside_support == "zero" else None,
            )
    return math.fsum(float(x) for x in (right - left) * (products[0] + 4 * products[1] + products[2]) / 6)


def _case(
    source: SpectralCurve,
    responses: tuple[SpectralCurve, ...],
    approved_mag: float,
) -> dict[str, Any]:
    start = max([380.0, *(curve.wavelengths_nm[0] for curve in responses if curve.outside_support == "unavailable")])
    end = min([780.0, *(curve.wavelengths_nm[-1] for curve in responses if curve.outside_support == "unavailable")])
    q8 = integrate_spectral_product(source, responses, start, end, quadrature_order=8)
    q16 = integrate_spectral_product(source, responses, start, end, quadrature_order=16)
    q32 = integrate_spectral_product(source, responses, start, end, quadrature_order=32)
    d50 = _decimal_exact(source, responses, start, end)
    reference = float(d50)
    source_area = math.fsum(
        (right - left) * (v_left + v_right) / 2
        for left, right, v_left, v_right in zip(
            source.wavelengths_nm, source.wavelengths_nm[1:], source.values, source.values[1:],
        )
    )
    scale = source_area * math.prod(max(abs(v) for v in curve.values) for curve in responses)
    uncertainty = max(
        abs(q8.value - q16.value),
        abs(q16.value - q32.value),
        abs(q32.value - reference),
        q8.interval_count * math.ulp(scale),
    )
    eta = 10 ** (approved_mag / 2.5) - 1
    near_zero = 0 <= reference <= uncertainty / eta
    band_set = build_spectral_band_set(source, responses, start, end)
    candidates = {
        "uniform_simpson_5nm": _uniform_simpson(source, responses, start, end, 5.0),
        "uniform_simpson_1nm": _uniform_simpson(source, responses, start, end, 1.0),
        STRATEGY_ID: integrate_band_set(band_set, source, responses).value,
    }
    evaluations: dict[str, dict[str, float | bool | None]] = {}
    for name, candidate in candidates.items():
        if near_zero:
            absolute_error = abs(candidate - reference)
            evaluations[name] = {
                "pass": absolute_error <= uncertainty,
                "absoluteError": absolute_error,
                "equivalentMagnitudeError": None,
            }
        elif reference > 0:
            mag_error = abs(2.5 * math.log10(candidate / reference)) if candidate > 0 else None
            evaluations[name] = {
                "pass": mag_error is not None and mag_error <= approved_mag,
                "absoluteError": abs(candidate - reference),
                "equivalentMagnitudeError": mag_error,
                "invalidPositiveCandidate": candidate <= 0,
            }
        else:
            evaluations[name] = {
                "pass": False,
                "absoluteError": abs(candidate - reference),
                "equivalentMagnitudeError": None,
            }
    return {
        "source": source.source_id,
        "responses": [curve.source_id for curve in responses],
        "domainNm": [start, end],
        "reference": reference,
        "unit": q8.unit,
        "oracleQ8": q8.value,
        "oracleQ16": q16.value,
        "oracleQ32": q32.value,
        "oracleD50": str(d50),
        "oracleNumericalUncertainty": uncertainty,
        "errorLedger": {
            "quadratureQ8VsD50Absolute": abs(q8.value - reference),
            "oracleNumericalUncertaintyAbsolute": uncertainty,
            "spectralDiscretizationByCandidate": {
                name: evaluation["absoluteError"] for name, evaluation in evaluations.items()
            },
            "instrumentalRsrUncertainty": None,
            "instrumentalRsrStatus": (
                "historical_diagnostic_unquantified" if any(curve.source_id.startswith("DIAGNOSTIC_") for curve in responses)
                else "not_applicable_to_CIE_weighting"
            ),
        },
        "signalRegime": "near_zero_absolute" if near_zero else "positive_magnitude" if reference > 0 else "negative_diagnostic",
        "bandCount": band_set.band_count,
        "bandSetId": band_set.band_set_id,
        "inputSignature": band_set.input_signature,
        "candidates": evaluations,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    criterion_bytes = CRITERION_PATH.read_bytes()
    criterion = json.loads(criterion_bytes)
    if criterion["status"] != "frozen_before_candidate_evaluation":
        raise ValueError("Cal congelar el criteri abans d'avaluar candidats")
    approved_mag = criterion["metric"]["maximumInclusive"]
    root = resolve_data_root() / "data" / "earth" / "light-pollution"
    spds, cie_responses = _load_cie(root / "spectral-oracle" / "cie")
    rsrs = _load_diagnostic_rsr(root / "viirs-rsr")
    cases = [
        _case(source, (response,), approved_mag)
        for source in spds
        for response in (*cie_responses, *rsrs)
    ]
    # Productes cúbics de dues respostes: línies estretes i formes CIE diferents.
    for source in (spds[0], spds[6], spds[9], spds[15], *spds[17:21]):
        for rsr in rsrs:
            cases.append(_case(source, (cie_responses[0], rsr), approved_mag))
    summary: dict[str, Any] = {}
    for name in ("uniform_simpson_5nm", "uniform_simpson_1nm", STRATEGY_ID):
        applicable = [case for case in cases if case["signalRegime"] != "negative_diagnostic"]
        failed = [case for case in applicable if not case["candidates"][name]["pass"]]
        summary[name] = {
            "applicableCases": len(applicable),
            "failedCases": len(failed),
            "worstPositiveMagnitudeError": max(
                (case["candidates"][name]["equivalentMagnitudeError"] or 0)
                for case in applicable
                if case["signalRegime"] == "positive_magnitude"
            ),
            "firstFailedCases": [
                {"source": case["source"], "responses": case["responses"]}
                for case in failed[:10]
            ],
        }
    result = {
        "criterionId": criterion["criterionId"],
        "criterionSha256": hashlib.sha256(criterion_bytes).hexdigest(),
        "approvedMaximumMagnitude": approved_mag,
        "historicalRsrStatus": "diagnostic_only_not_black_marble_2026",
        "caseCount": len(cases),
        "summary": summary,
        "cases": cases,
    }
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
