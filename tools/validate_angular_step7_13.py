"""Campanya angular directa limitada per cost; cap cache de transport ni calibratge."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import time
from dataclasses import asdict, replace
from datetime import datetime, timezone
from typing import Any

from angular_fixtures_step7_13 import fixture
from transport_gate_fixtures_step7_12 import ROOT
from validate_transport_gate_step7_12 import measured, reference, write
from terralab3d.domain.light_pollution.dome_profile import DomeField, DomeProfile
from terralab3d.domain.light_pollution.geometric_transport import ViewDirection
from terralab3d.domain.light_pollution.propagation_kernel import DirectionSet
from terralab3d.domain.light_pollution.radiometric_gate import assess_transport

OUT = ROOT / "docs/evidencies/pas7.13"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_binding(binding):
    for name, sha in binding["codeHashes"].items():
        if name == "tools/validate_angular_step7_13.py":
            # Runner original arxivat; revisió de resum/tipatge, sense reavaluar radiàncies.
            assert digest(OUT / "candidat-v1/validate_angular_step7_13.py") == sha
        else:
            assert digest(ROOT / name) == sha, "Candidat numèric de campanya modificat"


def policy():
    path = OUT / "criteri-angular-preregistrat-v1.json"
    assert (
        digest(path)
        == "139ad4d4305f7185556cbc98c5102f2dedf901e28105adcc303b7c72c1bca571"
    )
    return json.loads(path.read_text(encoding="utf8"))


def prepare():
    p = policy()
    pilot = json.loads((OUT / "pilot-cambra-cost.json").read_text(encoding="utf8"))
    names = [n.replace("standard", "chamber") for n in p["fixtures"]]
    paths = list((ROOT / "backend/src/terralab3d/domain/light_pollution").glob("*.py"))
    paths += [
        ROOT / "tools/angular_fixtures_step7_13.py",
        ROOT / "tools/validate_angular_step7_13.py",
    ]
    # Fitxer nou abans d'avaluar cap residual candidat/oracle de la campanya.
    data = dict(
        registeredAtUtc=datetime.now(timezone.utc).isoformat(),
        parentCriterionSha256=digest(OUT / "criteri-angular-preregistrat-v1.json"),
        reason="Domini de control numèric addicional assequible, no substitueix el camp COESA requerit. Cambra P/T/O3 constants fins a75km; no atmosfera física fins a l'infinit ni cua nul·la.",
        fixtures=names,
        fullInputs={n: asdict(fixture(n)) for n in names},
        codeHashes={
            str(f.relative_to(ROOT)).replace("\\", "/"): digest(f) for f in paths
        },
        rayUpperCount=1272,
        wallEstimateSeconds=1272
        * (pilot["runtimeSeconds"] + 3 * pilot["referenceFineSeconds"]),
        estimateLimitations="Pilot únic; muntanya i altres SPD poden costar més. Checkpoint per raig i límit prospectiu7200s de campanya.",
        metrics=p["metric"],
        transportDomainQualification="Finite75km chamber; standard domain remains separate",
    )
    path = OUT / "campanya-cambra-preregistrada-v1.json"
    if path.exists():
        old = json.loads(path.read_text(encoding="utf8"))
        verify_binding(old)
    else:
        write(path, data)
    return json.loads(path.read_text(encoding="utf8"))


def run():
    p, binding = policy(), prepare()
    samples = [
        (a, e) for a in p["initialAzimuthsDeg"] for e in p["initialElevationsDeg"]
    ]
    oracle = [
        (a, e)
        for a in p["oracleVerticalAzimuthsDeg"]
        for e in p["oracleVerticalElevationsDeg"]
    ]
    oracle += [
        (a, e)
        for a in p["oracleOffGrid"]["azimuthsDeg"]
        for e in p["oracleOffGrid"]["elevationsDeg"]
    ]
    points = list(dict.fromkeys(samples + oracle))
    start = time.perf_counter()
    for name in binding["fixtures"]:
        base = fixture(name)
        path = OUT / (name.lower().replace("_", "-") + ".json")
        data = (
            json.loads(path.read_text(encoding="utf8"))
            if path.exists()
            else dict(name=name, rows=[])
        )
        done = {(r["azimuthDeg"], r["elevationDeg"]) for r in data["rows"]}
        for az, el in points:
            if (az, el) in done:
                continue
            if time.perf_counter() - start > 7200:
                raise RuntimeError(
                    "Pressupost de campanya exhaurit; cap resultat pendent és PASS"
                )
            req = replace(
                base, directions=DirectionSet((ViewDirection("angular", az, el),))
            )
            run_result = measured(req)
            refs = []
            for level in p["referenceLevels"]:
                t = time.perf_counter()
                ref = reference(req, level)
                refs.append(
                    dict(result=asdict(ref), wallSeconds=time.perf_counter() - t)
                )
            decision = assess_transport(
                run_result["value"],
                tuple(r["result"]["value"] for r in refs),
                tuple(r["result"]["los_error_estimate"] for r in refs),
                relative_limit=p["metric"]["transportRelativeMaximum"],
                reference_resolution=p["metric"]["referenceRelativeMaximum"],
            )
            data["rows"].append(
                dict(
                    azimuthDeg=az,
                    elevationDeg=el,
                    runtime=run_result,
                    references=refs,
                    transportDecision=asdict(decision),
                )
            )
            write(path, data)
            if len(data["rows"]) % 25 == 0:
                print(name, len(data["rows"]), "/", len(points), flush=True)
    summarize()


def summarize():
    p = policy()
    binding = json.loads(
        (OUT / "campanya-cambra-preregistrada-v1.json").read_text(encoding="utf8")
    )
    verify_binding(binding)
    summary: dict[str, Any] = dict(
        criterionSha256=digest(OUT / "criteri-angular-preregistrat-v1.json"), cases=[]
    )
    for name in binding["fixtures"]:
        path = OUT / (name.lower().replace("_", "-") + ".json")
        if not path.exists():
            summary["cases"].append(
                dict(
                    name=name,
                    status="UNAVAILABLE_DEM_COVERAGE",
                    angularPass=False,
                    transportCounts={},
                    maximumAngularMagnitudeError=None,
                )
            )
            continue
        data = json.loads(path.read_text(encoding="utf8"))
        indexed = {(r["azimuthDeg"], r["elevationDeg"]): r for r in data["rows"]}
        profiles = []
        for az in p["initialAzimuthsDeg"]:
            b = tuple(
                indexed[az, e]["runtime"]["value"] for e in p["initialElevationsDeg"]
            )
            pos = [v for v in b if v > 0]
            profiles.append(
                DomeProfile(
                    az,
                    tuple(p["initialElevationsDeg"]),
                    b,
                    min(pos) * 1e-15 if pos else 1e-300,
                )
            )
        # La versió sense màscara és només diagnòstica per quantificar l'error;
        # amb DEM no és una reconstrucció admissible per al consumidor.
        field = DomeField(
            tuple(profiles),
            data["rows"][0]["runtime"]["unit"],
            "Fixture prescrita "
            + name
            + "; resposta CIE-V del kernel, sense constant fotomètrica",
            0,
            75000.0,
            "mountain" in name,
        )
        candidate = replace(field, direct_only=False)
        errors = []
        for (az, el), row in indexed.items():
            reconstructed = candidate.evaluate(az, el)
            actual = row["runtime"]["value"]
            delta = (
                None
                if reconstructed is None or actual == 0
                else abs(2.5 * math.log10(reconstructed / actual))
                if reconstructed > 0
                else None
            )
            errors.append(
                dict(
                    azimuthDeg=az,
                    elevationDeg=el,
                    direct=actual,
                    reconstructed=reconstructed,
                    absoluteError=None
                    if reconstructed is None
                    else abs(reconstructed - actual),
                    angularMagnitudeError=delta,
                    zeroLeak=actual == 0
                    and reconstructed is not None
                    and reconstructed != 0,
                    delivered=field.evaluate(az, el),
                )
            )
        positive_errors = [
            r["angularMagnitudeError"]
            for r in errors
            if r["angularMagnitudeError"] is not None
        ]
        record = dict(
            name=name,
            samples=len(data["rows"]),
            profile=field.to_dict(),
            transportCounts={
                s: sum(r["transportDecision"]["status"] == s for r in data["rows"])
                for s in ("PASS", "FAIL", "REFERENCE_UNRESOLVED")
            },
            maximumAngularMagnitudeError=max(positive_errors, default=None),
            angularPass=bool(positive_errors)
            and max(positive_errors) <= p["metric"]["angularMagnitudeMaximum"]
            and not any(r["zeroLeak"] for r in errors),
            exactZeros=sum(r["direct"] == 0 for r in errors),
            requiresDirect=sum(r["delivered"] is None for r in errors),
            errors=errors,
            runtimeSeconds=sum(r["runtime"]["wallSeconds"] for r in data["rows"]),
            referenceSeconds=sum(
                q["wallSeconds"] for r in data["rows"] for q in r["references"]
            ),
        )
        summary["cases"].append(record)
    write(OUT / "resultats-angulars-cambra.json", summary)
    print(
        [
            (
                c["name"],
                c["transportCounts"],
                c["maximumAngularMagnitudeError"],
                c["angularPass"],
            )
            for c in summary["cases"]
        ],
        flush=True,
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--part", choices=("prepare", "run", "summary"), required=True)
    args = parser.parse_args()
    if args.part == "prepare":
        print(prepare()["wallEstimateSeconds"])
    elif args.part == "run":
        run()
    else:
        summarize()
