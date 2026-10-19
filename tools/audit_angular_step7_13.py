"""Decisió de7.13: una fallada angular no es transforma en PASS de transport."""

import argparse
import json
import math
import time
from collections import Counter
from pathlib import Path

from plot_dome_step7_13 import decode
from validate_angular_step7_13 import digest, verify_binding
from validate_transport_gate_step7_12 import write

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs/evidencies/pas7.13"


def audit():
    original = json.loads((OUT / "preservacio-inicial.json").read_text(encoding="utf8"))
    differences = [p for p, sha in original["files"].items() if digest(ROOT / p) != sha]
    binding = json.loads(
        (OUT / "campanya-cambra-preregistrada-v1.json").read_text(encoding="utf8")
    )
    verify_binding(binding)
    previous = json.loads(
        (
            ROOT / "docs/evidencies/pas7.12/campanya-v1/vinculacio-candidat-v1.json"
        ).read_text(encoding="utf8")
    )
    changed_kernel = [
        p for p, sha in previous["codeHashes"].items() if digest(ROOT / p) != sha
    ]
    cases = json.loads(
        (OUT / "resultats-angulars-cambra.json").read_text(encoding="utf8")
    )["cases"]
    records = []
    decisions = []
    for case in cases:
        if "profile" not in case:
            continue
        raw = json.loads(
            (OUT / (case["name"].lower().replace("_", "-") + ".json")).read_text(
                encoding="utf8"
            )
        )["rows"]
        indexed = {(r["azimuthDeg"], r["elevationDeg"]): r for r in raw}
        decisions += [r["transportDecision"] for r in raw]
        vertical = [
            r["angularMagnitudeError"]
            for r in case["errors"]
            if r["azimuthDeg"] in (90, 270) and r["angularMagnitudeError"] is not None
        ]
        oracle_errors = [
            abs(
                2.5
                * math.log10(
                    r["reconstructed"]
                    / indexed[r["azimuthDeg"], r["elevationDeg"]]["references"][-1][
                        "result"
                    ]["value"]
                )
            )
            for r in case["errors"]
            if r["reconstructed"] is not None
            and r["reconstructed"] > 0
            and r["direct"] > 0
        ]
        field = decode(case["profile"])
        start = time.perf_counter()
        for i in range(10000):
            field.evaluate((i * 0.37) % 360, 0.5 + (i % 895) / 10)
        records.append(
            dict(
                name=case["name"],
                points=len(raw),
                maximumGuardedTransportError=max(
                    r["transportDecision"]["guarded_relative_error"] or 0 for r in raw
                ),
                maximumVerticalCompressionMag=max(vertical),
                maximumAngularCompressionMag=case["maximumAngularMagnitudeError"],
                maximumReconstructionVsSGREFMag=max(oracle_errors),
                profileJsonUtf8Bytes=len(
                    json.dumps(case["profile"], ensure_ascii=False).encode("utf8")
                ),
                reconstruction10000QueriesSeconds=time.perf_counter() - start,
                status="PASS_ANGULAR_SAMPLED"
                if case["angularPass"]
                else "FAIL_ANGULAR",
            )
        )
    for part in ("standard", "terrain"):
        rows = json.loads(
            (OUT / f"control-{part}-resultats.json").read_text(encoding="utf8")
        )
        decisions += [r["transportDecision"] for r in rows]
    terrain = json.loads(
        (OUT / "control-terrain-resultats.json").read_text(encoding="utf8")
    )
    standard = json.loads(
        (OUT / "control-standard-resultats.json").read_text(encoding="utf8")
    )
    cost = json.loads((OUT / "decisio-cost-standard.json").read_text(encoding="utf8"))
    policy = json.loads(
        (OUT / "criteri-angular-preregistrat-v1.json").read_text(encoding="utf8")
    )
    angular_pass = all(case.get("angularPass", False) for case in cases)
    # Un control local no acredita la campanya COESA registrada de quatre escenaris.
    standard_complete = cost["standardCampaignLaunched"] and len(standard) >= 1200
    transport_pass = all(d["status"] == "PASS" for d in decisions)
    complete = angular_pass and standard_complete and transport_pass
    report = dict(
        status=(
            "PASS_SAMPLED_DOMAIN"
            if complete
            else "FAIL_ANGULAR_AND_INCOMPLETE_STANDARD_DOMAIN"
            if not angular_pass
            else "INCOMPLETE_STANDARD_DOMAIN"
        ),
        stepCompleted=complete,
        criterion="criteri-angular-preregistrat-v1.json",
        angularBudgetMag=policy["metric"]["angularMagnitudeMaximum"],
        cases=records,
        transportDecisionCounts=dict(Counter(d["status"] for d in decisions)),
        terrainExactZeros=sum(r["runtime"]["value"] == 0 for r in terrain),
        terrainPoints=len(terrain),
        standardPoints=len(standard),
        conditionalStandardTailMagnitudeUpper=standard[0]["tailMagnitudeUpper"],
        historicalEvidenceCount=len(original["files"]),
        historicalDifferences=differences,
        previousKernelCodeChanged=changed_kernel,
        reasons=[
            "Les9elevacions fallen el pressupost vertical0,01mag.",
            "L’azimut lineal cada45° falla fins a2,689mag.",
            "La malla COESA75km completa no s’ha executat per cost estimat70h.",
            "El DEM±20km no cobreix totes les LOS0,5°; dades absents no són transparència.",
        ],
        nextStep="7.13_refinement_and_explicit_domain;7.14_not_started",
        observationallyValidated=False,
    )
    assert not differences and not changed_kernel
    write(OUT / "gate-angular-final.json", report)
    print(
        json.dumps(
            {k: v for k, v in report.items() if k != "cases"},
            ensure_ascii=False,
            indent=2,
        )
    )
    return complete


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--strict", action="store_true", help="Retorna1 si el gate no passa"
    )
    args = parser.parse_args()
    passed = audit()
    if args.strict and not passed:
        raise SystemExit(1)
