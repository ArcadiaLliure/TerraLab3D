"""Tancament dur del gate congelat; un resultat incomplet/fallit retorna error."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from dataclasses import asdict
from pathlib import Path

from transport_gate_fixtures_step7_12 import POLICY, ROOT, primary, vertical
from validate_transport_gate_step7_12 import EXPECTED_POLICY_SHA, reference, write
from terralab3d.domain.light_pollution.atmospheric_tail import conditional_tail_bound
from terralab3d.domain.light_pollution.radiometric_gate import assess_transport


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def decision(candidate, refs, policy):
    return asdict(
        assess_transport(
            candidate,
            tuple(r["result"]["value"] for r in refs),
            tuple(r["result"]["los_error_estimate"] for r in refs),
            relative_limit=policy["metric"]["maximumInclusive"],
            reference_resolution=policy["metric"][
                "referenceUncertaintyMaximumRelative"
            ],
        )
    )


def tail_references(root, policy):
    path = root / "referencies-cua-exterior.json"
    rows = read(path) if path.exists() else []
    for name in policy["verticalStudy"]["fixtures"]:
        for mode in policy["verticalStudy"]["modes"]:
            row = next(
                (r for r in rows if r["fixture"] == name and r["mode"] == mode), None
            )
            if row is None:
                row = dict(fixture=name, mode=mode, references=[])
                rows.append(row)
            req = vertical(name, mode)
            for refinement in policy["referenceRefinements"][len(row["references"]) :]:
                print("tail-reference", name, mode, refinement, flush=True)
                result = reference(req, refinement)
                row["references"].append(
                    dict(settings=refinement, result=asdict(result))
                )
                write(path, rows)


def audit(root, policy):
    campaign = root / "campanya-v1"
    manifest = read(campaign / "vinculacio-candidat-v1.json")
    assert manifest["policySha256"] == EXPECTED_POLICY_SHA
    assert all(
        hashlib.sha256((ROOT / p).read_bytes()).hexdigest() == h
        for p, h in manifest["codeHashes"].items()
    ), "El candidat ja no coincideix amb la vinculació"
    cases = []
    primary_tails = []
    for spec in policy["primaryCases"]:
        row = read(campaign / (spec["id"] + ".json"))
        assert row["case"] == spec
        actual = decision(row["runtime"][0]["value"], row["references"], policy)
        assert actual == row["decision"]
        cases.append(dict(case=spec["id"], **actual, repeatExact=row["repeatExact"]))
        if spec["standard"]:
            req = primary(spec)
            assert req.optical_field
            config = req.scattering or req.spectral
            assert config
            bound = conditional_tail_bound(
                req.sources[0],
                req.observer,
                req.directions.directions[0],
                req.options.top_m,
                req.optical_field.tiles[0].profile.pressure_pa[-1],
                config,
            )
            lower = actual["reference"] - actual["reference_uncertainty"]
            assert lower > 0
            magnitude = 2.5 * math.log10(1 + bound.upper_radiance / lower)
            primary_tails.append(
                dict(
                    case=spec["id"],
                    bound=asdict(bound),
                    lowerFiniteReference=lower,
                    tailMagnitudeUpper=magnitude,
                    tailBudgetPass=magnitude
                    <= policy["verticalStudy"]["tailMaximumMagnitude"],
                )
            )
    vertical_rows = read(campaign / "convergencia-vertical.json")
    study = policy["verticalStudy"]
    keys = {(r["fixture"], r["mode"], r["topM"]) for r in vertical_rows}
    expected = {
        (n, m, h)
        for n in study["fixtures"]
        for m in study["modes"]
        for h in study["topsM"]
    }
    assert keys == expected and len(vertical_rows) == len(expected), (
        "Campanya vertical incompleta o duplicada"
    )
    tails = []
    refs = read(root / "referencies-cua-exterior.json")
    for row in vertical_rows:
        if row["topM"] != study["tailTopM"]:
            continue
        reference_row = next(
            r
            for r in refs
            if r["fixture"] == row["fixture"] and r["mode"] == row["mode"]
        )
        result = decision(row["runtime"]["value"], reference_row["references"], policy)
        lower = result["reference"] - result["reference_uncertainty"]
        assert lower > 0
        upper = row["conditionalTail"]["upper_radiance"]
        magnitude = 2.5 * math.log10(1 + upper / lower)
        tails.append(
            dict(
                fixture=row["fixture"],
                mode=row["mode"],
                upperTailRadiance=upper,
                lowerFiniteReference=lower,
                tailMagnitudeUpper=magnitude,
                tailBudgetPass=upper > 0 and magnitude <= study["tailMaximumMagnitude"],
                finiteTransportDecision=result,
            )
        )
    spectral = read(root / "cota-lut-refinada-i-pressupost.json")["rows"]
    conservation = read(root / "regressions-i-preservacio.json")
    history_ok = all(
        hashlib.sha256((ROOT / p).read_bytes()).hexdigest() == h
        for p, h in conservation["historicalEvidenceHashes"].items()
    )
    checks = dict(
        primaryTransport=all(r["status"] == "PASS" and r["repeatExact"] for r in cases),
        positiveConditionalTail=all(r["tailBudgetPass"] for r in tails)
        and all(r["tailBudgetPass"] for r in primary_tails),
        finiteVerticalReferences=all(
            r["finiteTransportDecision"]["status"] == "PASS" for r in tails
        ),
        spectralBudget=all(
            r["combinedNumericalMagnitudeBound"] <= r["spectralBudgetMag"]
            for r in spectral
        ),
        historicalEvidenceExact=history_ok,
        b0Exact=conservation["b0Regression"]["identical"],
        columnsExact=all(conservation["opticalColumnResultsExact"]),
        pyrightNoNewDiagnostics=conservation["pyrightDiagnosticMultisetExact"],
    )
    passed = all(checks.values())
    result = dict(
        status="PASS_NUMERIC_CONDITIONAL_DOMAIN" if passed else "FAIL",
        policySha256=EXPECTED_POLICY_SHA,
        checks=checks,
        cases=cases,
        verticalCaseCount=len(vertical_rows),
        tails=tails,
        primaryConditionalTails=primary_tails,
        spectralCases=spectral,
        observationalValidation=False,
        nextStepStarted=False,
        scope="Fixtures registrades, camp/font/malla prescrits; cua condicionada d'aire sec. No prova uniforme de tota l'atmosfera o de tota ciutat.",
    )
    write(root / "resultat-gate-transport.json", result)
    print(result["status"], checks, flush=True)
    return 0 if passed else 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--part", choices=("tail", "final"), required=True)
    args = parser.parse_args()
    assert hashlib.sha256(POLICY.read_bytes()).hexdigest() == EXPECTED_POLICY_SHA
    protocol = read(POLICY)
    if args.part == "tail":
        tail_references(args.root, protocol)
    else:
        raise SystemExit(audit(args.root, protocol))
