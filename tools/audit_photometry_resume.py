"""Gate de la represa7.14: oracles, preservació i perfil nominal suficient."""

import argparse
import json
import math
import zipfile
from collections import Counter

from photometry_coordinates_step7_14_v2 import OUT, ROOT, digest, policy, write
from validate_photometry_step7_14_v2 import bind


def read(path):
    return json.loads(path.read_text("utf8"))


def diagnostics(data):
    return Counter(
        json.dumps({**d, "file": d["file"].replace("\\", "/").lower()}, sort_keys=True)
        for d in data["generalDiagnostics"]
    )


def audit():
    bind()
    p = policy()
    preserved = read(OUT / "preservacio-inicial-v2.json")
    historical_differences = [
        name
        for name, sha in preserved["previousEvidence"].items()
        if digest(ROOT / name) != sha
    ]
    source_differences = []
    for name, sha in preserved["previousSources"].items():
        path = (
            OUT / "candidat-parcial-v1" / name
            if name == ".gitattributes"
            else ROOT / name
        )
        if digest(path) != sha:
            source_differences.append(name)
    snapshot_differences = [
        name
        for name, sha in preserved["previousDocumentSnapshots"].items()
        if snapshot_digest(name) != sha
    ]
    amendment = read(OUT / "esmena-reutilitzacio-local-preregistrada-v2-1.json")
    old_candidate_preserved = all(
        digest(ROOT / name) == sha
        for name, sha in amendment["candidateSnapshots"].items()
    )
    old = read(OUT / "vinculacio-candidat-v2.json")
    new = read(OUT / "vinculacio-candidat-v3.json")
    delta = [name for name, sha in old["hashes"].items() if new["hashes"][name] != sha]
    rows = read(OUT / "coordenades-i-postprojeccions-v2.json")
    spectral = read(OUT / "pressupost-espectral-v2.json")
    qualification = read(OUT / "qualificacio-i-cobertura-v2.json")
    coverage = read(OUT / "diagnostic-cobertura-components-v2.json")
    cie_tail = read(OUT / "cota-exterior-cie-v2.json")
    hypotheses = read(OUT / "diferencies-hipotesis-coordenades-v2.json")
    coverage_policy = OUT / "criteri-diagnostic-cobertura-preregistrat-v2.json"
    costs = read(OUT / "costos-campanya-v2.json")
    columns = read(OUT / "columnes-b0-v2.json")
    old_columns = read(ROOT / "docs/evidencies/pas7.8/resultats-optical-field-v1.json")
    current_pyright = read(OUT / "pyright-global-v2.json")
    old_pyright = read(OUT.parent / "pyright-global.json")
    source_manifest = read(OUT / "manifest-dades-laboratori-v2.json")
    checks = dict(
        candidateBound=True,
        allHistoricalEvidencePreserved=len(preserved["previousEvidence"]) == 449
        and not historical_differences,
        originalScientificSourcesPreserved=not source_differences,
        originalDocumentSnapshotsPreserved=not snapshot_differences,
        interruptedCandidatePreserved=old_candidate_preserved,
        preregisteredLocalReuseOnly=set(delta)
        == {
            "backend/src/terralab3d/application/coordinate_photometry.py",
            "tools/validate_photometry_step7_14_v2.py",
        },
        primaryDataHashes=all(
            digest(OUT / r["file"]) == r["sha256"] for r in source_manifest
        ),
        coveragePolicyUnchanged=digest(coverage_policy)
        == coverage_policy.with_suffix(".sha256").read_text("ascii").strip()
        == coverage["policySha256"],
        allSixCoverageOracles=len(coverage["rows"]) == 6
        and all(r["oraclePass"] for r in coverage["rows"]),
        unmeasuredChipExteriorExplicit=all(
            r["fullPhysicalBoundMag"] is None and r["outsideChipResponse"] == "UNKNOWN"
            for r in coverage["rows"]
        ),
        correctedCiePositiveTail=cie_tail["newPhysicalLos"] == 0
        and cie_tail["topM"] == 75000
        and cie_tail["tail"]["upper_radiance"] > 0
        and cie_tail["conditionalTailMagnitudeUpper"] <= 0.001
        and cie_tail["passCriterion"],
        all55FluxControls=len(rows["fluxControls"]) == 55
        and all(
            r["passCriterion"]
            and r["relativeError"] <= p["coordinateFluxRelativeMaximum"]
            for r in rows["fluxControls"]
        ),
        all13PolynomialProjections=len(rows["postProjections"]) == 13
        and all(
            r["passCriterion"]
            and r["relativeError"] <= p["inheritedTableProjectionRelativeMaximum"]
            for r in rows["postProjections"]
        ),
        spectralBudget=spectral["caseCount"] == spectral["passed"] == 21184
        and spectral["failed"] == 0
        and spectral["maximumErrorMag"] <= p["inheritedSpectralMagnitudeMaximum"],
        spectralOracleResolved=spectral["maximumOracleRelativeRefinement"] <= 1e-6,
        noNewPhysicalLos=all(r["newPhysicalLos"] == 0 for r in costs)
        and rows["newPhysicalLos"] == 0,
        scientificCostBounded=sum(r["wallSeconds"] for r in costs)
        <= p["campaign"]["maximumScientificWallSeconds"],
        completedPhasesPass=len(costs) == 4
        and all(r["exitCode"] == 0 for r in costs[1:]),
        nominalDoesNotRequireIndividualCalibration=qualification[
            "individualCalibrationIsGlobalPrerequisite"
        ]
        is False
        and all(
            e["nominal"]["individualCalibrationRequired"] is False
            for e in qualification["instruments"]
        ),
        unknownCoverageNotZero=all(
            r["missingWeightFractionBelowElevation05deg"] > 0
            and r["noRadianceBound"]["status"] == "UNAVAILABLE"
            for r in qualification["gaussianCoverageDiagnostics"]
        ),
        b0Exact=columns["b0Regression"]["identical"]
        and columns["b0Regression"]["actualSignature"]
        == "21d3453df822b95d56aa508fee6bd9c76e712b27c63f3f03a3222e86e075b53e",
        fourColumnsExact=len(columns["cases"]) == 4
        and all(
            a["result"] == b["result"]
            for a, b in zip(columns["cases"], old_columns["cases"], strict=True)
        ),
        samePyrightDiagnostics=diagnostics(current_pyright) == diagnostics(old_pyright),
    )
    numeric = all(checks.values())
    native_missing = [e["nominal"]["missing"] for e in qualification["instruments"]]
    result = dict(
        status="BLOCKED_NOMINAL_RESPONSE_OR_COVERAGE"
        if numeric
        else "FAIL_NUMERIC_OR_REGRESSION",
        numericStatus="PASS" if numeric else "FAIL",
        scientificExitPassed=False,
        checks=checks,
        metrics=dict(
            spectral=spectral,
            maximumFluxRelativeError=max(
                r["relativeError"] for r in rows["fluxControls"]
            ),
            maximumProjectionRelativeError=max(
                r["relativeError"] for r in rows["postProjections"]
            ),
            maximumCoordinateConventionChangeMag=max(
                abs(r["coordinateChangeMag"])
                for r in rows["postProjections"]
                if r["coordinateChangeMag"] is not None
            ),
            postProjectionWallSeconds=[
                r["postWallSeconds"] for r in rows["postProjections"]
            ],
            scientificWallSecondsIncludingInterruptedAttempt=math.fsum(
                r["wallSeconds"] for r in costs
            ),
            historicalEvidenceCount=len(preserved["previousEvidence"]),
            historicalEvidenceDifferences=historical_differences,
            sourceDifferences=source_differences,
            conditionalComponentCoverageMagnitudeUpper=[
                r["conditionalReferenceMagnitudeUpperWithinChip"]
                for r in coverage["rows"]
            ],
            additionalCoverageCalculationWallSeconds=coverage["measuredWallSeconds"],
            correctedCieConditionalTailMagnitudeUpper=cie_tail[
                "conditionalTailMagnitudeUpper"
            ],
            additionalTailCalculationWallSeconds=cie_tail[
                "measuredCalculationWallSeconds"
            ],
            coordinateHypothesisDiagnostic=hypotheses["summary"],
            additionalHypothesisComparisonWallSeconds=hypotheses[
                "measuredCalculationWallSeconds"
            ],
            pyrightSummary=current_pyright["summary"],
        ),
        nominalMissing=native_missing,
        individualCalibrationIsGlobalPrerequisite=False,
        totalNominalNumericalErrorBoundMag=None,
        blockingReasons=[
            "Resposta nominal SQM/TESS amb suport/cues i convenció de λ encara sense acreditar en un perfil complet.",
            "El camp CIE escalar i els dominis angulars7.13 no són un camp espectral complet per integrar SQM/TESS. Cal cobertura o cota suficient, sense exigir una nova homologació angular general.",
        ],
        resolved=[
            "Conversió explícita aire/buit CIE2019 amb jacobià de densitats i referència AB coherent en buit.",
            "Model nominal AB separat de calibratge individual, fosc/guany natius i observacions.",
        ],
        qualifications=[
            "PASS sobre finestres conegudes i polinomis retinguts; hipòtesis de λ no identifiquen la convenció real del laboratori.",
            "La correcció de V(λ) no reconverteix la SPD ni reescriu els resultats antics.",
            "Cap calibratge C, Bortle, homologació observacional o ampliació COESA/DEM/àrea.",
        ],
        nextStep="7.14_pending_partial_blocked;7.15_not_started",
    )
    write(OUT / "gate-represa-v2.json", result)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return numeric


def verify_manifest():
    data = read(OUT / "manifest-final-represa-v2.json")
    differences = [
        name
        for section in ["sourceHashes", "documentHashes", "evidenceHashes"]
        for name, sha in data[section].items()
        if not (ROOT / name).is_file() or digest(ROOT / name) != sha
    ]
    print(
        json.dumps(dict(unchanged=not differences, differences=differences), indent=2)
    )
    return not differences


def snapshot_digest(name):
    path = ROOT / name
    if path.exists():
        return digest(path)
    index = read(OUT / "index-instantanies-docs-v1.json")
    archive_path = OUT / index["archive"]
    assert digest(archive_path) == index["archiveSha256"]
    import hashlib

    with zipfile.ZipFile(archive_path) as archive:
        return hashlib.sha256(
            archive.read(index["entries"][name]["member"])
        ).hexdigest()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--numeric-only", action="store_true")
    parser.add_argument("--verify-manifest", action="store_true")
    args = parser.parse_args()
    if args.verify_manifest:
        raise SystemExit(0 if verify_manifest() else 1)
    passed = audit()
    raise SystemExit(0 if passed and args.numeric_only else 1)
