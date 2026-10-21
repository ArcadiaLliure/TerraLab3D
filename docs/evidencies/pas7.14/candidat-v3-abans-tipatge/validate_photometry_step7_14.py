"""Campanya preregistrada: espectres retinguts, SG-REF i disponibilitat física."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import time
from dataclasses import asdict, replace

import numpy as np
from scipy.integrate import quad

from angular_fixtures_step7_13 import fixture
from photometry_fixtures_step7_14 import OUT, ROOT, profiles
from transport_gate_fixtures_step7_12 import primary
from validate_transport_gate_step7_12 import reference, write
from terralab3d.application.photometric_projections import (
    project_retained,
    retain_spectrum,
)
from terralab3d.domain.light_pollution.atmospheric_tail import conditional_tail_bound
from terralab3d.domain.light_pollution.geometric_transport import ViewDirection
from terralab3d.domain.light_pollution.propagation_kernel import DirectionSet
from terralab3d.domain.light_pollution.radiometric_gate import assess_transport
from terralab3d.domain.photometric_projection import (
    GaussianFov,
    average_fov,
    project_band,
    sensor_magnitude,
)

EXPECTED_POLICY = "5275ed470d376bfe28565413dff3a1ef24ac63d7e41436869bad76573dd5614c"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def policy():
    path = OUT / "criteri-projeccions-preregistrat-v1.json"
    assert digest(path) == EXPECTED_POLICY
    return json.loads(path.read_text("utf8"))


def cases():
    result = []
    for name in policy()["chamberFixtures"]:
        stem = name.lower().replace("_", "-")
        old = json.loads(
            (OUT.parent / "pas7.13/adaptatiu-v2" / (stem + "-holdout.json")).read_text(
                "utf8"
            )
        )
        for index in policy()["angularIndicesFromFrozenHoldout"]:
            row = old["rows"][index]
            req = replace(
                fixture(name),
                directions=DirectionSet(
                    (
                        ViewDirection(
                            f"registered-{index}",
                            row["azimuthDeg"],
                            row["elevationDeg"],
                        ),
                    )
                ),
            )
            result.append((f"{name}-{index}", req, row["runtime"]["value"]))
    mountain = fixture("S_B4_chamber_mountain_point_5km")
    for elevation in (23.61, 23.89):
        req = replace(
            mountain,
            directions=DirectionSet((ViewDirection("terrain", 90.2, elevation),)),
        )
        result.append((f"S-mountain-{elevation}", req, None))
    area = primary(
        dict(
            mode="B4",
            standard=False,
            area=True,
            distanceM=5000,
            elevationDeg=47.3,
            terrain="none",
        )
    )
    chamber = fixture("S_B4_chamber_point_5km")
    area = replace(
        area,
        optical_field=chamber.optical_field,
        spectral=chamber.spectral,
        options=chamber.options,
        directions=DirectionSet((ViewDirection("area", 270.7, 47.3),)),
    )
    result.append(("S-area400m", area, None))
    old_profile = json.loads(
        (OUT.parent / "pas7.13/adaptatiu-v2/perfil-coesa-holdout.json").read_text(
            "utf8"
        )
    )
    coesa = replace(
        fixture("S_B4_standard_point_5km"),
        directions=DirectionSet((ViewDirection("coesa", 270.7, 52.19),)),
    )
    old_cie = next(
        r["runtime"]["value"] for r in old_profile["rows"] if r["elevationDeg"] == 52.19
    )
    result.append(("S-COESA75km-52.19", coesa, old_cie))
    return result


def bind():
    paths = [
        ROOT / "backend/src/terralab3d/domain/photometric_projection.py",
        ROOT / "backend/src/terralab3d/application/photometric_projections.py",
        ROOT / "backend/tests/test_photometric_projection_step7_14.py",
        *sorted((ROOT / "backend/src/terralab3d/domain/light_pollution").glob("*.py")),
        ROOT / "tools/validate_photometry_step7_14.py",
        ROOT / "tools/photometry_fixtures_step7_14.py",
        ROOT / "tools/prepare_photometry_sources_step7_14.py",
    ]
    data = dict(
        policySha256=EXPECTED_POLICY,
        codeHashes={p.relative_to(ROOT).as_posix(): digest(p) for p in paths},
        responseDataSha256=digest(OUT / "models-resposta-referencia.json"),
        inputs={name: asdict(req) for name, req, _ in cases()},
    )
    # La identitat inclou l’entrada wire: JSON converteix tuples en llistes.
    # Canonicalitzar abans de comparar evita una falsa mutació del candidat.
    data = json.loads(json.dumps(data, default=lambda value: value.isoformat()))
    path = OUT / "vinculacio-candidat-v3.json"
    if path.exists():
        old = json.loads(path.read_text("utf8"))
        assert old == data, (
            "Candidat canviat: conservar la versió i preregistrar-ne una altra"
        )
    else:
        write(path, data)
    return data


def polynomial_oracle(samples, response, domain):
    """GL8 sobre el polinomi quadràtic del panell, sense pesos Simpson."""
    nodes, weights = np.polynomial.legendre.leggauss(8)
    values = np.array(samples.radiance_per_nm).reshape(-1, 3)
    lo, hi = domain
    total = []
    for i, (a, b) in enumerate(zip(samples.knots_nm, samples.knots_nm[1:])):
        if a < lo or b > hi:
            continue
        t = (nodes + 1) / 2
        y = values[i]
        density = (
            2 * (t - 0.5) * (t - 1) * y[0]
            - 4 * t * (t - 1) * y[1]
            + 2 * t * (t - 0.5) * y[2]
        )
        wavelength = a + (b - a) * t
        r = np.interp(
            wavelength,
            response.curve.wavelengths_nm,
            response.curve.values,
            left=0,
            right=0,
        )
        total.append(float((b - a) / 2 * np.dot(weights, density * r)))
    return math.fsum(total)


def transport():
    p = policy()
    bind()
    responses = profiles()
    path = OUT / "transport-i-projeccions.json"
    rows = json.loads(path.read_text("utf8")) if path.exists() else []
    start = time.perf_counter()
    spent = sum(r["totalWallSeconds"] for r in rows)
    for name, req, historical_cie in cases()[len(rows) :]:
        estimate = 455 if "COESA" in name else 12
        assert spent + estimate <= p["cost"]["maximumScientificWallSeconds"], (
            "Campanya desproporcionada; no reduir precisió"
        )
        write(
            OUT / "estimacio-proper-control.json",
            dict(
                case=name,
                spentSeconds=spent,
                estimateSeconds=estimate,
                limitSeconds=p["cost"]["maximumScientificWallSeconds"],
            ),
        )
        begin = time.perf_counter()
        cpu = time.process_time()
        captured = retain_spectrum(req, responses)
        capture_wall = time.perf_counter() - begin
        samples = captured.spectral_samples[0]
        signal_rows = []
        for response in responses:
            lo = max(req.spectral.wavelength_start_nm, response.curve.wavelengths_nm[0])
            hi = min(req.spectral.wavelength_end_nm, response.curve.wavelengths_nm[-1])
            band = project_band(samples, response, domain_nm=(lo, hi))
            oracle = polynomial_oracle(samples, response, (lo, hi))
            table_relative = (
                abs(band.value - oracle) / abs(oracle)
                if oracle
                else 0
                if band.value == 0
                else math.inf
            )
            ref_req = replace(
                req,
                spectral=replace(
                    req.spectral,
                    responses=(response.curve,),
                    wavelength_start_nm=lo,
                    wavelength_end_nm=hi,
                ),
            )
            begin_ref = time.perf_counter()
            refs = [asdict(reference(ref_req, level)) for level in p["referenceLevels"]]
            ref_wall = time.perf_counter() - begin_ref
            decision = assess_transport(
                band.value,
                tuple(r["value"] for r in refs),
                tuple(r["los_error_estimate"] for r in refs),
                relative_limit=p["transportRelativeMaximum"],
                reference_resolution=p["referenceRelativeMaximum"],
            )
            error_mag = (
                abs(2.5 * math.log10(band.value / decision.reference))
                if band.value > 0 and decision.reference > 0
                else 0
                if band.value == decision.reference == 0
                else None
            )
            row = dict(
                responseId=response.response_id,
                domainNm=(lo, hi),
                signal=asdict(band),
                polynomialOracle=oracle,
                tableRelativeError=table_relative,
                references=refs,
                referenceWallSeconds=ref_wall,
                transportDecision=asdict(decision),
                equivalentMagnitudeError=error_mag,
                referenceMagnitude=sensor_magnitude(
                    band, response, allow_reference=True
                )
                if response.kind != "CIE"
                else None,
            )
            if "COESA" in name:
                bound = conditional_tail_bound(
                    req.sources[0],
                    req.observer,
                    req.directions.directions[0],
                    75000.0,
                    req.optical_field.tiles[0].profile.pressure_pa[-1],
                    ref_req.spectral,
                )
                row["conditionalTail"] = asdict(bound)
                row["tailMagnitudeUpper"] = 2.5 * math.log10(
                    1
                    + bound.upper_radiance
                    / (decision.reference - decision.reference_uncertainty)
                )
            signal_rows.append(row)
        begin_projection = time.perf_counter()
        projections = project_retained(
            captured, responses, expected_revision=req.revision
        )
        projection_wall = time.perf_counter() - begin_projection
        total = time.perf_counter() - begin
        spent += total
        row = dict(
            name=name,
            fullInput=asdict(req),
            captured=asdict(captured),
            kernelWallSeconds=capture_wall,
            postProjectionWallSeconds=projection_wall,
            cpuSeconds=time.process_time() - cpu,
            totalWallSeconds=total,
            results=signal_rows,
            projections=projections,
            historicalCieValue=historical_cie,
        )
        if historical_cie is not None:
            current = signal_rows[0]["signal"]["value"]
            row["relativeChangeVersusHistoricalCie"] = (
                abs(current / historical_cie - 1)
                if historical_cie
                else 0
                if current == 0
                else None
            )
        rows.append(row)
        write(path, rows)
        print(
            name,
            round(capture_wall, 3),
            [r["transportDecision"]["status"] for r in signal_rows],
            flush=True,
        )
        assert spent <= p["cost"]["maximumScientificWallSeconds"], (
            "Pressupost real exhaurit"
        )
    write(
        OUT / "temps-transport.json",
        dict(
            measuredScientificSeconds=spent,
            phaseWallSeconds=time.perf_counter() - start,
            runtimeLos=len(rows),
            serial=True,
        ),
    )


def fov_controls():
    p = policy()
    bind()
    start = time.perf_counter()
    rows = []
    for width in (17.0, 20.0):
        f = GaussianFov(
            f"nominal-Gaussian-{width:g}deg",
            width,
            "Bará/Tapia/Zamorano2019, model nominal prescrit",
        )
        sigma = math.radians(width)

        def density(t):
            return math.exp(-4 * math.log(2) * (t / sigma) ** 2) * math.sin(t)

        norm = quad(density, 0, math.pi / 2, epsabs=1e-14, epsrel=1e-12)[0]
        moment = (
            quad(
                lambda t: density(t) * math.cos(t) ** 2,
                0,
                math.pi / 2,
                epsabs=1e-14,
                epsrel=1e-12,
            )[0]
            / norm
        )
        for az, el in ((0.0, 90.0), (89.3, 60.0), (275.1, 32.0)):
            pointing = ViewDirection("analytic", az, el)
            u = pointing.enu
            ez2 = u[2] ** 2 * moment + (1 - u[2] ** 2) * (1 - moment) / 2
            een = u[0] * u[1] * (3 * moment - 1) / 2
            oracle = 1 + 0.5 * ez2 + 0.2 * een

            def field(a, e):
                a, e = math.radians(a), math.radians(e)
                return (
                    1
                    + 0.5 * math.sin(e) ** 2
                    + 0.2 * math.cos(e) ** 2 * math.sin(a) * math.cos(a)
                )

            results = [
                average_fov(
                    field, f, pointing, complete_forward_hemisphere=True, order=n
                )
                for n in (32, 64, 128)
            ]
            error = abs(2.5 * math.log10(results[-1] / oracle))
            rows.append(
                dict(
                    fov=f.model_id,
                    azimuthDeg=az,
                    elevationDeg=el,
                    values=results,
                    oracle=oracle,
                    errorMagnitude=error,
                    passCriterion=error <= p["angularMagnitudeMaximum"],
                )
            )
    write(
        OUT / "controls-FOV.json",
        dict(
            rows=rows,
            wallSeconds=time.perf_counter() - start,
            scope="Camps analítics complets; cap homologació angular física addicional",
        ),
    )
    print("FOV", max(r["errorMagnitude"] for r in rows), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--part", choices=("bind", "transport", "fov"), required=True)
    part = parser.parse_args().part
    if part == "bind":
        bind()
    elif part == "transport":
        transport()
    else:
        fov_controls()
