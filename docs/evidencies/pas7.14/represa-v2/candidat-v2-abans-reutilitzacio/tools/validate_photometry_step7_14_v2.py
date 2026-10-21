"""Controls preregistrats de coordenades i postprocessament7.14, cap LOS nova."""

from __future__ import annotations

import argparse
import csv
import json
import math
import time
from dataclasses import asdict, replace

import numpy as np
from scipy.integrate import quad
from scipy.optimize import brentq

from photometry_coordinates_step7_14_v2 import (
    OUT,
    ROOT,
    POLICY_SHA,
    cie_standard_air,
    digest,
    policy,
    write,
)
from photometry_fixtures_step7_14 import profiles
from project_skyglow_photometry import spectral_payload
import validate_spectral_transport_step7_10 as harness
from terralab3d.application.coordinate_photometry import project_coordinate_band
from terralab3d.domain.instrument_qualification import (
    InstrumentEvidence,
    missing_coverage_error,
    qualify_instrument,
)
from terralab3d.domain.light_pollution.spectral_oracle import (
    RELATIVE_UNIT,
    SpectralCurve,
)
from terralab3d.domain.wavelength_coordinates import CoordinateCurve


def bind():
    policy()
    paths = [
        ROOT / p
        for p in (
            "backend/src/terralab3d/domain/wavelength_coordinates.py",
            "backend/src/terralab3d/domain/instrument_qualification.py",
            "backend/src/terralab3d/application/coordinate_photometry.py",
            "backend/tests/test_photometric_coordinates_step7_14_v2.py",
            "tools/validate_spectral_transport_step7_10.py",
        )
    ]
    paths += sorted((ROOT / "tools").glob("*step7_14_v2.py"))
    paths += [
        OUT.parent / "transport-i-projeccions.json",
        OUT.parent / "models-resposta-referencia.json",
        OUT / "manifest-dades-laboratori-v2.json",
    ]
    data = dict(
        policySha256=POLICY_SHA,
        hashes={p.relative_to(ROOT).as_posix(): digest(p) for p in paths},
    )
    p = OUT / "vinculacio-candidat-v2.json"
    if p.exists():
        assert json.loads(p.read_text("utf8")) == data, (
            "Candidat canviat: conservar i versionar"
        )
    else:
        write(p, data)


def independent_air(v):
    # Oracle amb aritmètica estesa i formulació de Ciddor independent del candidat.
    w = np.longdouble(v)
    s = np.longdouble(1000000) / (w * w)
    n = 1 + (
        np.longdouble(5792105) / (np.longdouble("238.0185") - s)
        + np.longdouble(167917) / (np.longdouble("57.362") - s)
    ) * np.longdouble("1e-8")
    return float(w / n)


def controls():
    bind()
    p = policy()
    start = time.perf_counter()
    rows = []
    for spectrum in harness.cases()[0]:
        native = SpectralCurve(
            spectrum.spectrum_id,
            spectrum.wavelengths_nm,
            spectrum.relative_power,
            RELATIVE_UNIT,
            "zero",
        )
        coordinate = CoordinateCurve(native, "standard_air_450ppm_nm", "density")
        table = coordinate.linearized_vacuum(
            peak_fraction=p["linearizedCurveAbsoluteMaximumFractionOfPeak"]
        )
        actual = sum(
            (b - a) * (ya + yb) / 2
            for a, b, ya, yb in zip(
                table.wavelengths_nm,
                table.wavelengths_nm[1:],
                table.values,
                table.values[1:],
            )
        )
        reference = spectrum.raw_integral_nm
        error = abs(actual / reference - 1)
        rows.append(
            dict(
                spectrumId=spectrum.spectrum_id,
                scenarioBasis="standard_air_450ppm_nm explicit; no requalifica el catàleg heretat",
                originalKnots=len(native.values),
                vacuumKnots=len(table.values),
                nativeIntegral=reference,
                vacuumIntegral=actual,
                relativeError=error,
                passCriterion=error <= p["coordinateFluxRelativeMaximum"],
            )
        )
    post = []
    response = cie_standard_air()
    source_rows = json.loads(
        (OUT.parent / "transport-i-projeccions.json").read_text("utf8")
    )
    independent_breaks = [
        brentq(lambda v: independent_air(v) - a, a, a + 1, xtol=1e-12)
        for a in response.curve.wavelengths_nm
    ]
    for old in source_rows:
        begin = time.perf_counter()
        retained = spectral_payload(old["captured"])
        sample = retained.spectral_samples[0]
        projected = project_coordinate_band(
            sample,
            response,
            input_radiance_basis="vacuum_nm",
            domain_nm=(sample.knots_nm[0], sample.knots_nm[-1]),
        )
        project_time = time.perf_counter() - begin
        x = np.array(sample.knots_nm)
        y = np.array(sample.radiance_per_nm).reshape(-1, 3)

        def integrand(w):
            i = min(np.searchsorted(x, w, side="right") - 1, len(x) - 2)
            t = (w - x[i]) / (x[i + 1] - x[i])
            a, m, b = y[i]
            density = (
                a * (2 * t - 1) * (t - 1) + 4 * m * t * (1 - t) + b * t * (2 * t - 1)
            )
            return float(
                density
                * np.interp(
                    independent_air(w),
                    response.curve.wavelengths_nm,
                    response.curve.values,
                    left=0,
                    right=0,
                )
            )

        breaks = sorted(
            set(sample.knots_nm) | {w for w in independent_breaks if x[0] < w < x[-1]}
        )
        oracle = math.fsum(
            quad(integrand, a, b, epsabs=1e-30, epsrel=1e-11)[0]
            for a, b in zip(breaks, breaks[1:])
        )
        relative = (
            abs(projected.signal.value / oracle - 1)
            if oracle
            else 0.0
            if projected.signal.value == 0
            else None
        )
        legacy = old["results"][0]["signal"]["value"]
        post.append(
            dict(
                name=old["name"],
                coordinateProjection=asdict(projected),
                oracle=oracle,
                relativeError=relative,
                passCriterion=relative is not None
                and relative <= p["inheritedTableProjectionRelativeMaximum"],
                legacyCie=legacy,
                coordinateChangeMag=-2.5 * math.log10(projected.signal.value / legacy)
                if min(projected.signal.value, legacy) > 0
                else None,
                postWallSeconds=project_time,
            )
        )
    write(
        OUT / "coordenades-i-postprojeccions-v2.json",
        dict(
            fluxControls=rows,
            postProjections=post,
            wallSeconds=time.perf_counter() - start,
            newPhysicalLos=0,
            scope="Conservació del canvi de variable i projecció del polinomi existent; no nou transport ni nova homologació angular.",
        ),
    )


def spectral():
    bind()
    p = policy()
    original_spectra = harness.cases()[0]
    original_parameters = harness.operators()
    curves = []
    for profile in profiles():
        for basis in ("vacuum_nm", "standard_air_450ppm_nm"):
            coordinate = CoordinateCurve(profile.curve, basis, "response")
            curve = coordinate.linearized_vacuum(
                peak_fraction=p["linearizedCurveAbsoluteMaximumFractionOfPeak"]
            )
            curves.append(
                replace(
                    curve,
                    source_id=curve.source_id + ":KNOWN-SUPPORT-WINDOW-HYPOTHESIS",
                    outside_support="zero",
                )
            )
    selected = [
        v
        for v in original_parameters
        if v["mu"] in (-1.0, 1.0)
        and v["alpha"] in (0.0, 2.0)
        and v["ozoneColumnM2"] in (0.0, 1e24)
    ]
    assert len(selected) == 64
    harness.cases = lambda: (original_spectra, [(c,) for c in curves])
    harness.operators = lambda: selected
    folder = OUT / "espectral-v2"
    assert not folder.exists(), "Conservar la campanya i versionar la repetició"
    folder.mkdir()
    write(folder / "entrades-resposta-v2.json", [asdict(c) for c in curves])
    harness.run(folder)
    result = json.loads((folder / "pressupost-espectral.json").read_text("utf8"))
    write(
        OUT / "pressupost-espectral-v2.json",
        {
            k: result[k]
            for k in [
                "caseCount",
                "passed",
                "failed",
                "maximumErrorMag",
                "maximumLutErrorMag",
                "maximumSimpsonErrorMag",
                "maximumOracleRelativeRefinement",
                "durationSeconds",
            ]
        },
    )


def qualification():
    bind()
    p = policy()
    # Les hipòtesis de coordenades no s’usen com si identifiquessin el laboratori.
    sqm = InstrumentEvidence(
        "SQM-CM500-nominal-components",
        "Cinzano2005 + fabricant TSL237/CM500; diferenciar SQM ample de SQM-L",
        True,
        False,
        False,
        True,
        False,
    )
    tess = InstrumentEvidence(
        "TESS-W-batch-specific-optics",
        "LICA2026; respostes/filtres i FOV disponibles, però sense cota exterior ni convenció espectral explícita",
        True,
        False,
        False,
        True,
        False,
    )
    result = []
    for e in (sqm, tess):
        result.append(
            dict(
                profile=asdict(e),
                nominal=qualify_instrument(
                    e, target="nominal_ab", absolute_source_scale=True
                ),
                native=qualify_instrument(
                    e, target="native_magnitude", absolute_source_scale=True
                ),
            )
        )
    fov = []
    for width in (17.0, 20.0, 84.0):

        def f(theta):
            return math.exp(
                -4 * math.log(2) * (theta / math.radians(width)) ** 2
            ) * math.sin(theta)

        total = quad(f, 0, math.pi / 2, epsabs=1e-40, epsrel=1e-10)[0]
        missing = (
            quad(f, math.radians(89.5), math.pi / 2, epsabs=1e-80, epsrel=1e-10)[0]
            / total
        )
        fov.append(
            dict(
                nominalGaussianFwhmDeg=width,
                scope="Prescripció nominal exacta al zenit, no ajust ni mesura de les ales reals",
                missingWeightFractionBelowElevation05deg=missing,
                noRadianceBound=missing_coverage_error(
                    known_signal=1.0,
                    missing_weight_fraction=missing,
                    missing_radiance_upper=None,
                    magnitude_maximum=p["coverageMagnitudeMaximum"],
                ),
                exampleWithExplicitBound=missing_coverage_error(
                    known_signal=1.0,
                    missing_weight_fraction=missing,
                    missing_radiance_upper=1.0,
                    magnitude_maximum=p["coverageMagnitudeMaximum"],
                ),
            )
        )
    primary = []
    for path in sorted((OUT / "fonts-primaries/report/tessw").glob("*.csv")):
        data = list(csv.DictReader(path.open(encoding="utf8")))
        primary.append(
            dict(
                file=path.relative_to(OUT).as_posix(),
                samples=len(data),
                wavelengthRangeNm=[
                    float(data[0]["Wavelength"]),
                    float(data[-1]["Wavelength"]),
                ],
                frequencyAtEndpointsHz=[
                    float(data[0]["Mean freq"]),
                    float(data[-1]["Mean freq"]),
                ],
                meaning="Freqüència i dispersió mesurades; no són per si soles responsivitat radiomètrica corregida pel fosc i il·luminació.",
            )
        )
    fov_data = []
    for path in sorted((OUT / "fonts-primaries/report/fov").glob("*.csv")):
        data = list(csv.DictReader(path.open(encoding="utf8")))
        columns = {
            key: [float(r[key]) for r in data if r.get(key, "").strip()]
            for key in data[0]
            if key.startswith(("Angle", "Dark")) and "(mag)" not in key
        }
        fov_data.append(
            dict(
                file=path.relative_to(OUT).as_posix(),
                ranges={k: [min(v), max(v)] for k, v in columns.items() if v},
                meaning="Dos talls angulars i controls amb font apagada; no funció hemisfèrica completa ni fosc transferible a altres assaigs.",
            )
        )
    write(
        OUT / "qualificacio-i-cobertura-v2.json",
        dict(
            instruments=result,
            gaussianCoverageDiagnostics=fov,
            primarySpectralData=primary,
            primaryAngularData=fov_data,
            status="BLOCKED_NOMINAL_RESPONSE_OR_COVERAGE",
            individualCalibrationIsGlobalPrerequisite=False,
            newPhysicalLos=0,
        ),
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--part",
        required=True,
        choices=["bind", "controls", "spectral", "qualification"],
    )
    args = parser.parse_args()
    {
        "bind": bind,
        "controls": controls,
        "spectral": spectral,
        "qualification": qualification,
    }[args.part]()
