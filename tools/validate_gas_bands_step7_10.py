"""T_eff per banda/SPD contra l'O3 original, amb regla de Jensen explícita."""

from __future__ import annotations

import argparse
import csv
import gzip
import json
from dataclasses import replace
from pathlib import Path

import numpy as np
from scipy.special import roots_legendre

from benchmark_skyglow_spectral import fixture
from validate_spectral_transport_step7_10 import cases, coefficients
from terralab3d.domain.light_pollution.gas_absorption import effective_band_transmission
from terralab3d.domain.light_pollution.spectral_oracle import SpectralCurve, DIMENSIONLESS_UNIT
from terralab3d.domain.light_pollution.spectral_transport import SpectralOperator
from terralab3d.infrastructure.adapters.atmosphere.gas_catalog import load_ozone_lut


def run(output: Path):
    req = fixture(1)
    assert req.spectral
    raw = load_ozone_lut(fine=True)
    cfg = replace(req.spectral, responses=(SpectralCurve("unity", (380., 780.), (1., 1.), DIMENSIONLESS_UNIT),))
    assert cfg.gas is not None
    summary = {"protocolId": "TL3D-SKY-7.10-Teff-v1", "maximumInclusiveMag": .01, "weighting": "source SPD only, per band, no response or scattering collapsed into T_eff", "caseCount": 0, "failed": 0, "unlitBandCases": 0, "maximumErrorMag": 0., "maximumAbsoluteError": 0., "maximumReferenceRefinement": 0., "minimumJensenDifference": 1., "maximumJensenDifference": 0., "jensenRoundoffAllowance": 50 * np.finfo(float).eps, "cases": []}
    with gzip.open(output / "casos-teff-per-banda.csv.gz", "wt", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(["SPD", "temperature_K", "column_m^-2", "left_nm", "right_nm", "candidate_Teff", "fine_Teff", "error_mag", "jensen_difference"])
        for spectrum in cases()[0]:
            op = SpectralOperator(replace(req.sources[0], spectrum=spectrum), cfg)
            knots = np.array(op.band_set.knots_nm)
            sw = op.weights.reshape(-1, 3)
            denominator = sw.sum(axis=1)
            lit = denominator > 0
            joint = np.array(sorted(set(raw.wavelengths_nm) | set(knots)))
            refs = {}
            for order in (8, 16, 32):
                x, weights = roots_legendre(order)
                a, b = joint[:-1], joint[1:]
                waves = ((a + b)[:, None] / 2 + (b - a)[:, None] / 2 * x).ravel()
                qw = ((b - a)[:, None] / 2 * np.broadcast_to(weights, (len(a), order))).ravel()
                qw *= np.interp(waves, spectrum.wavelengths_nm, spectrum.relative_power, left=0., right=0.) / spectrum.raw_integral_nm
                index = np.minimum(np.searchsorted(knots, waves, side="right") - 1, len(knots) - 2)
                den = np.bincount(index, weights=qw, minlength=len(denominator))
                if np.any((den > 0) != lit):
                    raise ValueError("Banda buida incompatible entre oracle i candidat")
                for temperature in (223., 288.15):
                    sigma = coefficients(waves, raw, temperature)[2]
                    for column in (0., 1e22, 1e23, 1e24):
                        num = np.bincount(index, weights=qw * np.exp(-column * sigma), minlength=len(den))
                        refs[(order, temperature, column)] = np.divide(num, den, out=np.full_like(den, np.nan), where=lit)
            for temperature in (223., 288.15):
                weights_t = cfg.gas.luts[0].temperature_weights(temperature)
                sigma = np.sum(weights_t[:, None] * op.gas_matrices[0], axis=0)
                for column in (0., 1e22, 1e23, 1e24):
                    tau = (column * sigma).reshape(-1, 3)
                    actual = effective_band_transmission(sw, tau)
                    reference = refs[(32, temperature, column)]
                    error_mag = np.abs(2.5 * np.log10(actual[lit] / reference[lit]))
                    diff = np.abs(actual[lit] - reference[lit])
                    refinement = np.maximum(np.abs(refs[(8, temperature, column)] - refs[(16, temperature, column)]), np.abs(refs[(16, temperature, column)] - reference))[lit]
                    mean_tau = np.divide((sw * tau).sum(axis=1), denominator, out=np.zeros_like(denominator), where=lit)
                    jensen = actual[lit] - np.exp(-mean_tau[lit])
                    count = int(lit.sum())
                    summary["caseCount"] += count
                    summary["failed"] += int(np.sum(error_mag > .01))
                    summary["unlitBandCases"] += int((~lit).sum())
                    summary["maximumErrorMag"] = max(summary["maximumErrorMag"], float(error_mag.max()))
                    summary["maximumAbsoluteError"] = max(summary["maximumAbsoluteError"], float(diff.max()))
                    summary["maximumReferenceRefinement"] = max(summary["maximumReferenceRefinement"], float(refinement.max()))
                    summary["minimumJensenDifference"] = min(summary["minimumJensenDifference"], float(jensen.min()))
                    summary["maximumJensenDifference"] = max(summary["maximumJensenDifference"], float(jensen.max()))
                    summary["cases"].append({"spd": spectrum.spectrum_id, "temperatureK": temperature, "columnM2": column, "bands": count, "maximumErrorMag": float(error_mag.max()), "maximumReferenceRefinement": float(refinement.max())})
                    for i, error, jd in zip(np.flatnonzero(lit), error_mag, jensen):
                        writer.writerow([spectrum.spectrum_id, temperature, column, knots[i], knots[i + 1], actual[i], reference[i], error, jd])
            print("T_eff", spectrum.spectrum_id, flush=True)
    summary["jensenConsistentWithinRoundoff"] = bool(summary["minimumJensenDifference"] >= -summary["jensenRoundoffAllowance"])
    (output / "teff-per-banda.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print({k: v for k, v in summary.items() if k != "cases"}, flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    run(parser.parse_args().output)
