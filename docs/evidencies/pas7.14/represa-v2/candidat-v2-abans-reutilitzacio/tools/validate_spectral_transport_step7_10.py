"""Oracle espectral fi independent i registre d'errors del Pas 7.10.

La referència integra moments del transport als intervals comuns de les
corbes lineals. GL8/16/32 es parteix també als 40.001 nusos gasosos originals;
no interpola el transport resultant ni usa els pesos Simpson del candidat.
"""

from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import json
import math
import time
from dataclasses import replace
from pathlib import Path

import numpy as np
from scipy.special import roots_legendre

from benchmark_skyglow_spectral import fixture
from terralab3d.domain.light_pollution.source_model import DefinedSpectrum
from terralab3d.domain.light_pollution.spectral_oracle import DIMENSIONLESS_UNIT, RELATIVE_UNIT, SpectralCurve
from terralab3d.domain.light_pollution.spectral_transport import SpectralOperator
from terralab3d.infrastructure.adapters.atmosphere.gas_catalog import load_ozone_lut
from terralab3d.infrastructure.adapters.light_pollution.spectral_library import load_spectral_library


def cases():
    lib = load_spectral_library()
    spectra = list(lib.spectra.values())
    spectra.extend(lib.kelvin_spectrum(k) for k in (2800., 3000., 4000., 5000., 6500.))
    for first in ("LED-B1", "LED-RGB1"):
        for basis in ("radiant_flux", "photopic_flux"):
            spectra.append(lib.mix(f"{first}-HP1-{basis}", ((first, .5), ("HP1", .5)), basis))
    for center, half in ((435.25, .5), (500.005, .005), (589.02, .05), (700.005, .005)):
        spectra.append(DefinedSpectrum(f"triangle-{center}", "Fixture definida de 7.4; no línia física reconstruïda", "CC0-1.0", (380., center - half, center, center + half, 780.), (0., 0., 1., 0., 0.)))
    responses = {name: SpectralCurve(name, lib.cmf_wavelengths, tuple(values), DIMENSIONLESS_UNIT, "zero") for name, values in zip("XYZ", lib.cmf_xyz)}
    responses["V"] = SpectralCurve("V", lib.photopic_wavelengths, lib.photopic_values, DIMENSIONLESS_UNIT, "zero")
    weights = [(r,) for r in responses.values()] + [(responses[k], responses["V"]) for k in "XYZ"]
    return spectra, weights


def operators():
    return [{"id": f"{kind}-T{t}-mu{mu}-a{alpha}-N{column:g}", "kind": kind, "temperatureK": t, "mu": mu, "alpha": alpha, "ozoneColumnM2": column, "airColumnM2": 5e29, "aerosolPathM": 20000.} for kind in ("gas_only", "rayleigh_only", "aerosol_only", "combined") for t in (223., 288.15) for mu in (-1., 0., 1.) for alpha in (0., 1.3, 2.) for column in (0., 1e22, 1e23, 1e24)]


def coefficients(w: np.ndarray, lut, temperature: float):
    # Fórmules científiques compartides; implementació NumPy independent del
    # candidat, inclosa la convenció equivalent amb rho en lloc de delta.
    z = (1000 / w) ** 2
    sigma = 3.9993e-32 * z ** 2 / (1 - .01069 * z - .00006681 * z ** 2)
    nr = (.7041 + 315.90 / (157.39 - z) + 8.4127 / (50.429 - z)) * 1e-4
    king = sigma * 3 * 2.686763e25 ** 2 * (w * 1e-9) ** 4 / (32 * np.pi ** 3 * nr ** 2)
    rho = 6 * (king - 1) / (7 * king + 3)
    i = min(np.searchsorted(lut.temperatures_k, temperature, side="right") - 1, len(lut.temperatures_k) - 2)
    f = (temperature - lut.temperatures_k[i]) / (lut.temperatures_k[i + 1] - lut.temperatures_k[i])
    ozone = (1 - f) * np.interp(w, lut.wavelengths_nm, lut.cross_sections_m2[i]) + f * np.interp(w, lut.wavelengths_nm, lut.cross_sections_m2[i + 1])
    return sigma, rho, ozone


def transfer(w: np.ndarray, params: dict, values) -> np.ndarray:
    sigma, rho, ozone = values
    mu = params["mu"]
    phase = 3 / (8 * np.pi) * ((1 + rho) + (1 - rho) * mu ** 2) / (2 + rho)
    aer = 1e-5 * (w / 550.) ** (-params["alpha"])
    hg = (1 - .65 ** 2) / (4 * np.pi * (1 + .65 ** 2 - 1.3 * mu) ** 1.5)
    ray_gamma = 101325. / (1.380649e-23 * 288.15) * sigma * phase
    aer_gamma = aer * .9 * hg
    if params["kind"] == "gas_only":
        return np.exp(-params["ozoneColumnM2"] * ozone)
    if params["kind"] == "rayleigh_only":
        return ray_gamma * np.exp(-params["airColumnM2"] * sigma)
    if params["kind"] == "aerosol_only":
        return aer_gamma * np.exp(-params["aerosolPathM"] * aer)
    return (ray_gamma + aer_gamma) * np.exp(-params["airColumnM2"] * sigma - params["aerosolPathM"] * aer - params["ozoneColumnM2"] * ozone)


def run(output: Path):
    start = time.perf_counter()
    spectra, responses = cases()
    coarse = np.array(sorted({380., 780.} | {w for s in spectra for w in s.wavelengths_nm if 380 < w < 780} | {w for rr in responses for r in rr for w in r.wavelengths_nm if 380 < w < 780}))
    left, right = coarse[:-1], coarse[1:]
    coefficient_rows, labels, candidates, bounds = [], [], [], []
    req = fixture(1)
    cfg = req.spectral
    assert cfg is not None
    for spectrum in spectra:
        source_curve = SpectralCurve(spectrum.spectrum_id, spectrum.wavelengths_nm, tuple(x / spectrum.raw_integral_nm for x in spectrum.relative_power), RELATIVE_UNIT, "zero")
        for rr in responses:
            poly = np.ones((len(left), 1))
            for curve in (source_curve, *rr):
                inside = ((left + right) / 2 >= curve.wavelengths_nm[0]) & ((left + right) / 2 <= curve.wavelengths_nm[-1])
                a = np.where(inside, np.interp(left, curve.wavelengths_nm, curve.values), 0.)
                b = np.where(inside, np.interp(right, curve.wavelengths_nm, curve.values), 0.)
                new = np.zeros((len(left), poly.shape[1] + 1))
                new[:, :-1] += poly * a[:, None]
                new[:, 1:] += poly * (b - a)[:, None]
                poly = new
            coefficient_rows.append(np.pad(poly, ((0, 0), (0, 4 - poly.shape[1]))).ravel())
            labels.append((spectrum.spectrum_id, "*".join(r.source_id for r in rr)))
            candidates.append(SpectralOperator(replace(req.sources[0], spectrum=spectrum), replace(cfg, responses=rr)))
            bounds.append(float(np.trapezoid(np.interp(coarse, source_curve.wavelengths_nm, source_curve.values, left=0, right=0), coarse)) * math.prod(max(r.values) for r in rr))
    # Cas nul exacte heretat: regla absoluta, sense logaritme ni SPD fictícia.
    labels.append(("SYNTH_ZERO", "V"))
    coefficient_rows.append(np.zeros_like(coefficient_rows[0]))
    bounds.append(0.)
    coeff = np.array(coefficient_rows)
    params = operators()
    refs = {}
    raw = load_ozone_lut(fine=True)
    lut = load_ozone_lut()
    common = np.array(sorted(set(coarse) | set(raw.wavelengths_nm)))
    peak_transfers = np.zeros(len(params))
    for kind, table, orders in (("raw", raw, (8, 16, 32)), ("lut", lut, (32,))):
        for order in orders:
            x, weights = roots_legendre(order)
            a, b = common[:-1], common[1:]
            w = ((a + b)[:, None] / 2 + (b - a)[:, None] / 2 * x).ravel()
            qweights = ((b - a)[:, None] / 2 * np.broadcast_to(weights, (len(a), order))).ravel()
            idx = np.minimum(np.searchsorted(coarse, w, side="right") - 1, len(left) - 1)
            t = (w - left[idx]) / (right[idx] - left[idx])
            data = {temp: coefficients(w, table, temp) for temp in (223., 288.15)}
            moments = []
            for j, p in enumerate(params):
                tr = transfer(w, p, data[p["temperatureK"]])
                if kind == "raw":
                    peak_transfers[j] = max(peak_transfers[j], float(tr.max()))
                z = tr * qweights
                moments.append(np.column_stack([np.bincount(idx, weights=z * t ** power, minlength=len(left)) for power in range(4)]).ravel())
            refs[(kind, order)] = coeff @ np.array(moments).T
            print("Oracle", kind, order, len(w), flush=True)
    cand = np.zeros((len(labels), len(params)))
    for i, op in enumerate(candidates):
        data = {temp: coefficients(op.wavelengths, lut, temp) for temp in (223., 288.15)}
        for j, p in enumerate(params):
            cand[i, j] = float(op.weights @ transfer(op.wavelengths, p, data[p["temperatureK"]]))
    reference = refs[("raw", 32)]
    lut_ref = refs[("lut", 32)]
    uncertainty = np.maximum(np.abs(refs[("raw", 8)] - refs[("raw", 16)]), np.abs(refs[("raw", 16)] - reference))
    scale = np.array(bounds)[:, None] * peak_transfers[None, :]
    uncertainty = np.maximum(uncertainty, (len(common) - 1) * np.spacing(scale))
    eta = 10 ** (.01 / 2.5) - 1
    near = reference <= uncertainty / eta
    with np.errstate(divide="ignore", invalid="ignore"):
        error_mag = np.where(near, 0., np.abs(2.5 * np.log10(cand / reference)))
        lut_mag = np.where(near, 0., np.abs(2.5 * np.log10(lut_ref / reference)))
        quadrature_mag = np.where(near, 0., np.abs(2.5 * np.log10(cand / lut_ref)))
    passed = np.where(near, np.abs(cand - reference) <= uncertainty, error_mag <= .01)
    output.mkdir(parents=True, exist_ok=True)
    csvpath = output / "casos-pressupost-espectral.csv.gz"
    with gzip.open(csvpath, "wt", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream)
        writer.writerow(["spd", "response", "operator", "candidate", "reference_raw", "reference_lut", "u_reference", "error_mag", "lut_error_mag", "simpson_error_mag", "near_zero", "pass"])
        for i, (s, r) in enumerate(labels):
            for j, p in enumerate(params):
                writer.writerow([s, r, p["id"], cand[i, j], reference[i, j], lut_ref[i, j], uncertainty[i, j], error_mag[i, j], lut_mag[i, j], quadrature_mag[i, j], bool(near[i, j]), bool(passed[i, j])])
    worst = np.unravel_index(int(np.argmax(error_mag)), error_mag.shape)
    summary = {"protocolId": "TL3D-SKY-7.10-v2", "criterionId": "TL3D-SKY-V3-SPECTRAL-001", "maximumInclusiveMag": .01, "spectra": [s.spectrum_id for s in spectra], "responseFamilies": ["*".join(r.source_id for r in rr) for rr in responses], "operators": params, "caseCount": int(passed.size), "passed": int(passed.sum()), "failed": int((~passed).sum()), "maximumErrorMag": float(error_mag.max()), "maximumLutErrorMag": float(lut_mag.max()), "maximumSimpsonErrorMag": float(quadrature_mag.max()), "maximumOracleRelativeRefinement": float(np.max(np.divide(uncertainty, reference, out=np.zeros_like(reference), where=~near))), "nearZeroCases": int(near.sum()), "worst": {"spdResponse": labels[worst[0]], "operator": params[worst[1]], "candidate": float(cand[worst]), "reference": float(reference[worst]), "uReference": float(uncertainty[worst])}, "bandCounts": sorted({op.band_set.band_count for op in candidates}), "candidateStrategy": candidates[0].band_set.strategy_id, "caseFileSha256": hashlib.sha256(csvpath.read_bytes()).hexdigest(), "durationSeconds": time.perf_counter() - start, "limitations": ["Dominis prescrits, no homologació atmosfèrica o H", "GL32 fi de funcions no polinòmiques; Decimal D50 anterior resta només aplicable al producte de corbes lineals", "No reconstrueix estructura no tabulada; seccions eficaces publicades tenen incertesa física separada del pressupost numèric", "Aquest gate espectral no és el gate de transport de 7.12"]}
    (output / "pressupost-espectral.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({k: summary[k] for k in ("caseCount", "passed", "failed", "maximumErrorMag", "maximumLutErrorMag", "maximumSimpsonErrorMag", "durationSeconds")}), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    run(parser.parse_args().output)
