"""Audita dades arxivades, regressions i disponibilitat; no executa transport."""

from __future__ import annotations

import argparse
import json
import math
from collections import Counter

from photometry_fixtures_step7_14 import OUT, ROOT
from validate_photometry_step7_14 import EXPECTED_POLICY, bind, digest
from validate_transport_gate_step7_12 import write

SPECTRAL_POLICY_SHA = "b8542bc0b89df953995dd2fd0a8a594a2955892c82b64c3d58b17b105b8393d0"


def read(path):
    return json.loads(path.read_text(encoding="utf8"))


def diagnostics(data):
    return Counter(
        json.dumps({**d, "file": d["file"].replace("\\", "/").lower()}, sort_keys=True)
        for d in data["generalDiagnostics"]
    )


def verify_manifest():
    manifest = read(OUT / "manifest-codi-docs-evidencies-v1.json")
    differences = [
        path
        for category in ("sourceHashes", "documentHashes", "evidenceHashes")
        for path, sha in manifest[category].items()
        if not (ROOT / path).is_file() or digest(ROOT / path) != sha
    ]
    print(
        json.dumps(dict(unchanged=not differences, differences=differences), indent=2)
    )
    return not differences


def audit():
    current = bind()
    measured = read(OUT / "vinculacio-candidat-v3.json")
    changes = [
        p
        for p, sha in measured["codeHashes"].items()
        if current["codeHashes"][p] != sha
    ]
    expected_changes = {
        "backend/tests/test_photometric_projection_step7_14.py",
        "tools/validate_photometry_step7_14.py",
        "tools/prepare_photometry_sources_step7_14.py",
    }
    snapshot_checks = {
        p: digest(OUT / "candidat-v3-abans-tipatge" / p.rsplit("/", 1)[-1])
        == measured["codeHashes"][p]
        for p in changes
    }
    typing_delta = dict(
        measuredCandidate="v3",
        currentCandidate="v4",
        differences=changes,
        originalSnapshotsMatchMeasuredHashes=snapshot_checks,
        numericRuntimeUnchanged=set(changes) == expected_changes,
        sameInputs=current["inputs"] == measured["inputs"],
        sameResponseData=current["responseDataSha256"]
        == measured["responseDataSha256"],
        meaning="Anotacions/narrowing de proves i eines i nom de vinculació; cap canvi al runtime numèric mesurat.",
    )
    write(OUT / "delta-tipatge-v3-v4.json", typing_delta)
    policy = read(OUT / "criteri-projeccions-preregistrat-v1.json")
    spectral_policy = read(OUT / "criteri-espectral-sensors-preregistrat-v1.json")
    rows = read(OUT / "transport-i-projeccions.json")
    results = [r for row in rows for r in row["results"]]
    fov = read(OUT / "controls-FOV.json")
    spectral = read(OUT / "pressupost-espectral-sensors-v1.json")
    spectral_binding = read(OUT / "espectral-v1/vinculacio-espectral-v1.json")
    source_manifest = read(OUT / "fonts-manifest.json")
    preserved = read(OUT / "preservacio-inicial.json")["files"]
    differences = [p for p, sha in preserved.items() if digest(ROOT / p) != sha]
    columns = read(OUT / "columnes-b0.json")
    old_columns = read(ROOT / "docs/evidencies/pas7.8/resultats-optical-field-v1.json")
    exact_columns = [
        a["result"] == b["result"]
        for a, b in zip(columns["cases"], old_columns["cases"], strict=True)
    ]
    pyright = read(OUT / "pyright-global.json")
    old_pyright = read(ROOT / "docs/evidencies/pas7.13/pyright-global.json")
    archived = read(OUT / "verificacio-historica-713.json")
    zero = next(r for r in rows if r["name"] == "S-mountain-23.61")
    coesa = next(r for r in rows if "COESA" in r["name"])
    costs = read(OUT / "costos-campanya.json")
    wall = sum(c["wallSeconds"] for c in costs)
    checks = dict(
        unchangedProjectionPolicy=digest(
            OUT / "criteri-projeccions-preregistrat-v1.json"
        )
        == EXPECTED_POLICY,
        unchangedSpectralPolicy=digest(
            OUT / "criteri-espectral-sensors-preregistrat-v1.json"
        )
        == SPECTRAL_POLICY_SHA,
        sameSpectralCandidate=spectral_binding["policySha256"] == SPECTRAL_POLICY_SHA
        and spectral_binding["codeSha256"]
        == digest(ROOT / "tools/validate_sensor_spectral_budget_step7_14.py")
        and spectral_binding["oracleHarnessSha256"]
        == digest(ROOT / "tools/validate_spectral_transport_step7_10.py")
        and spectral_binding["responseModelsSha256"]
        == digest(OUT / "models-resposta-referencia.json"),
        scientificSourceHashes=all(
            digest(OUT / "fonts" / row["file"]) == row["sha256"]
            for row in source_manifest
        ),
        sameMeasuredRuntime=typing_delta["numericRuntimeUnchanged"]
        and all(snapshot_checks.values())
        and typing_delta["sameInputs"]
        and typing_delta["sameResponseData"],
        spectralCount=spectral["caseCount"] == spectral["passed"] == 10624
        and spectral["failed"] == 0,
        spectralBudget=spectral["maximumErrorMag"]
        <= spectral_policy["magnitudeMaximum"],
        spectralOracleResolved=spectral["maximumOracleRelativeRefinement"]
        <= spectral_policy["oracleRelativeResolutionMaximum"],
        allRegisteredTransport=len(rows) == 13
        and len(results) == 39
        and all(r["transportDecision"]["status"] == "PASS" for r in results),
        tableProjection=all(
            r["tableRelativeError"] <= policy["tableProjectionRelativeMaximum"]
            for r in results
        ),
        physicalZeros=all(r["signal"]["value"] == 0 for r in zero["results"]),
        analyticFov=len(fov["rows"]) == 6
        and all(
            r["passCriterion"]
            and r["errorMagnitude"] <= policy["angularMagnitudeMaximum"]
            for r in fov["rows"]
        ),
        positiveConditionalTail=all(
            r["conditionalTail"]["upper_radiance"] > 0
            and 0 < r["tailMagnitudeUpper"] < 0.001
            for r in coesa["results"]
        ),
        noAdditionalTransport=all(
            r["projections"]["physicalTransportEvaluations"] == 0 for r in rows
        ),
        cNeverAbsolute=all(
            x["projection"]["status"] in {"relative", "unavailable"}
            for r in rows
            if r["name"].startswith("C_")
            for x in r["projections"]["projections"]
        ),
        noPrematureNativeSensor=all(
            x["projection"]["status"] == "unavailable"
            for r in rows
            for x in r["projections"]["projections"]
            if x["projection"]["kind"] != "PHOTOPIC_LUMINANCE"
            and x["projection"]["kind"] != "RELATIVE_PHOTOPIC_SIGNAL"
        ),
        sameFourColumns=len(exact_columns) == 4 and all(exact_columns),
        sameB0=columns["b0Regression"]["identical"]
        and columns["b0Regression"]["actualSignature"]
        == "21d3453df822b95d56aa508fee6bd9c76e712b27c63f3f03a3222e86e075b53e",
        samePyrightDiagnosticMultiset=diagnostics(pyright) == diagnostics(old_pyright),
        allHistoricalEvidencePreserved=len(preserved) == 319 and not differences,
        archived713AuditsPass=all(r["exitCode"] == 0 for r in archived["audits"])
        and archived["temporaryWorktreeRemoved"],
        boundedCampaign=wall <= policy["cost"]["maximumScientificWallSeconds"]
        and len(rows) <= policy["cost"]["maximumRuntimeLos"],
    )
    metrics = dict(
        transportCases=len(rows),
        transportComparisons=len(results),
        maximumGuardedTransportRelative=max(
            r["transportDecision"]["guarded_relative_error"] or 0 for r in results
        ),
        maximumTransportErrorMag=max(
            r["equivalentMagnitudeError"] or 0 for r in results
        ),
        maximumTableRelativeError=max(r["tableRelativeError"] for r in results),
        maximumHistoricalCieRelativeChange=max(
            r.get("relativeChangeVersusHistoricalCie", 0) for r in rows
        ),
        maximumFovErrorMag=max(r["errorMagnitude"] for r in fov["rows"]),
        spectral=spectral,
        coesaTailMagnitudeUpper=[r["tailMagnitudeUpper"] for r in coesa["results"]],
        coesaKernelWallSeconds=coesa["kernelWallSeconds"],
        postProjectionWallSeconds=dict(
            minimum=min(r["postProjectionWallSeconds"] for r in rows),
            maximum=max(r["postProjectionWallSeconds"] for r in rows),
            mean=math.fsum(r["postProjectionWallSeconds"] for r in rows) / len(rows),
        ),
        scientificWallSecondsIncludingFailedSetup=wall,
        historicalEvidenceCount=len(preserved),
        historicalEvidenceDifferences=differences,
        pyrightSummary=pyright["summary"],
    )
    numeric_pass = all(checks.values())
    result = dict(
        status="BLOCKED_SENSOR_PROFILES"
        if numeric_pass
        else "FAIL_NUMERIC_OR_REGRESSION",
        numericStatus="PASS" if numeric_pass else "FAIL",
        scientificExitPassed=False,
        checks=checks,
        metrics=metrics,
        blockingReasons=[
            "SQM: suport finit acabat en resposta no nul·la; cua i calibratge/FOV emparellats no acreditats.",
            "TESS-W: fosc, FOV emparellat, resposta exterior i calibratge conjunt no acreditats.",
            "DomeProfile CIE escalar i cobertura angular7.13 insuficients per al FOV espectral complet; cap renormalització parcial.",
            "Convenció aire/buit heretada pendent de qualificació física versionada.",
        ],
        scope="PASS de problemes tabulats/fixtures registrades; cap homologació instrumental, observacional, angular COESA general, DEM o fonts extenses addicional.",
        nextStep="7.14_pending_blocked;7.15_not_started",
    )
    write(OUT / "gate-projeccions-v1.json", result)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return numeric_pass


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--numeric-only", action="store_true")
    parser.add_argument("--verify-manifest", action="store_true")
    args = parser.parse_args()
    if args.verify_manifest:
        raise SystemExit(0 if verify_manifest() else 1)
    passed = audit()
    # El criteri científic complet segueix bloquejat; el mode numèric és explícit.
    raise SystemExit(0 if passed and args.numeric_only else 1)
