"""Auditoria7.14v3: recerca, candidats intactes i regressions, sense noves LOS."""

from __future__ import annotations

import argparse
from contextlib import redirect_stdout
import hashlib
import io
import json
from pathlib import Path
import zipfile

import audit_photometry_resume as legacy_v2
import audit_photometry_step7_14 as legacy_v1
from terralab3d.domain.instrument_qualification import (
    InstrumentEvidence,
    qualify_instrument,
)

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs/evidencies/pas7.14/represa-v3"


def read(path: Path):
    return json.loads(path.read_text("utf8"))


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_immutable(path: Path, data) -> None:
    raw = json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False) + "\n"
    if path.exists():
        assert path.read_text("utf8") == raw, "Cal conservar i versionar el resultat"
    else:
        path.write_text(raw, encoding="utf8", newline="\n")


def replay_legacy(module, filename: str) -> bool:
    # Només redirigeix la destinació del resultat. Les entrades i totes les
    # comprovacions/hash del candidat original són exactament les mateixes.
    original = module.write

    def redirected(path, data):
        if module is legacy_v1 and path.name == "delta-tipatge-v3-v4.json":
            assert data == read(path)
            write_immutable(OUT / "delta-tipatge-heretat-repetit-v3.json", data)
            return
        expected = (
            "gate-projeccions-v1.json"
            if module is legacy_v1
            else "gate-represa-v2.json"
        )
        assert path.name == expected
        write_immutable(OUT / filename, data)

    try:
        module.write = redirected
        with redirect_stdout(io.StringIO()):
            return module.audit()
    finally:
        module.write = original


def audit():
    initial = read(OUT / "preservacio-inicial-v3.json")
    policy_path = OUT / "criteri-diagnostic-preregistrat-v3.json"
    policy = read(policy_path)
    policy_hash = digest(policy_path)
    assert policy_hash == policy_path.with_suffix(".sha256").read_text("ascii").strip()
    registry = read(OUT / "perfils-candidats-i-mancances-v3.json")
    sources = read(OUT / "registre-recerca-v3.json")
    known_ids = {r["id"] for r in sources["sources"]}
    qualifications = []
    for row in registry["candidates"]:
        assert set(row["sourceIds"]) <= known_ids
        evidence = InstrumentEvidence(
            profile_id=row["id"],
            provenance="; ".join(row["sourceIds"]),
            spectral_response_known=row["spectral_response_known"],
            wavelength_basis_known=row["wavelength_basis_known"],
            spectral_coverage_bounded=row["spectral_coverage_bounded"],
            angular_model_known=row["angular_model_known"],
            angular_coverage_bounded=row["angular_coverage_bounded"],
        )
        nominal = qualify_instrument(
            evidence, target="nominal_ab", absolute_source_scale=True
        )
        relative = qualify_instrument(
            evidence, target="nominal_ab", absolute_source_scale=False
        )
        qualifications.append(
            dict(
                model=row["model"],
                nominal=nominal,
                relativeC=relative,
                requiredData=row["missing"],
            )
        )
    perf = read(OUT / "cost-projeccio-v3.json")
    columns = read(OUT / "columnes-b0-v3.json")
    old_columns = read(ROOT / "docs/evidencies/pas7.8/resultats-optical-field-v1.json")
    regressions = read(OUT / "regressions-v3.json")
    archive = OUT / initial["snapshotArchive"]
    with zipfile.ZipFile(archive) as z:
        documents_preserved = digest(archive) == initial[
            "snapshotArchiveSha256"
        ] and all(
            hashlib.sha256(z.read(name)).hexdigest() == sha
            for name, sha in initial["snapshotMembers"].items()
        )
    metadata_index = read(OUT / "index-metadades-v3.json")
    metadata_archive = OUT / metadata_index["archive"]
    with zipfile.ZipFile(metadata_archive) as z:
        metadata_preserved = digest(metadata_archive) == metadata_index[
            "sha256"
        ] and all(
            hashlib.sha256(z.read(name)).hexdigest() == sha
            for name, sha in metadata_index["members"].items()
        )
    # Aquestes fonts inclouen tot el kernel, les coordenades i les projeccions.
    checks = dict(
        previous576EvidencePreserved=len(initial["previousEvidence"]) == 576
        and all(
            digest(ROOT / p) == sha for p, sha in initial["previousEvidence"].items()
        ),
        previous99SourcesUnchanged=len(initial["previousSources"]) == 99
        and all(
            digest(ROOT / p) == sha for p, sha in initial["previousSources"].items()
        ),
        originalDocumentsArchived=documents_preserved,
        consultationMetadataPreserved=metadata_preserved,
        historicalV1NumericGate=replay_legacy(
            legacy_v1, "gate-numeric-v1-repetit-v3.json"
        ),
        historicalV2NumericGate=replay_legacy(
            legacy_v2, "gate-numeric-v2-repetit-v3.json"
        ),
        projectionOraclesAndExactFrozenValues=len(perf["cases"]) == 13
        and all(
            r["passCriterion"] and r["exactlyMatchesFrozenResult"]
            for r in perf["cases"]
        ),
        inheritedBudgetsIntact=policy["inheritedCriteria"]["spectralMaximumMag"] == 0.01
        and policy["inheritedCriteria"]["combinedMaximumMag"] == 0.01
        and policy["inheritedCriteria"]["coverageAllocationMag"] == 0.001,
        noNewPhysicalLos=perf["physicalTransportEvaluations"] == 0,
        costBounded=perf["calculationWallSeconds"]
        < policy["campaign"]["maximumScientificSeconds"],
        noRuntimeOptimization=perf["runtimeChanged"] is False,
        regressionsPass=all(
            r["exitCode"] == r["expectedExitCode"] for r in regressions
        ),
        backend540Pass="540 passed"
        in (OUT / "pytest-backend-v3.txt").read_text("utf8"),
        b0Exact=columns["b0Regression"]["identical"]
        and columns["b0Regression"]["actualSignature"]
        == "21d3453df822b95d56aa508fee6bd9c76e712b27c63f3f03a3222e86e075b53e",
        fourColumnsExact=len(columns["cases"]) == 4
        and all(
            a["result"] == b["result"]
            for a, b in zip(columns["cases"], old_columns["cases"], strict=True)
        ),
        nominalDoesNotRequireDeviceCalibration=all(
            q["nominal"]["individualCalibrationRequired"] is False
            for q in qualifications
        ),
        relativeCNotPromoted=all(
            q["relativeC"]["status"] == "unavailable" for q in qualifications
        ),
        noUnknownCoverageAsZero=registry["coverage"]["unknownRegionRadianceIsZero"]
        is False
        and registry["coverage"]["fullSceneContributionBound"] is None,
        protectedPlanningUnchanged=all(
            digest(ROOT / p) == sha
            for p, sha in initial["previousDocuments"].items()
            if "/pas7.14-" not in p and ("/tasques/" in p or "21-estrategia" in p)
        ),
    )
    numeric = all(checks.values())
    complete_nominals = {
        q["nominal"]["profileId"]
        for q in qualifications
        if q["nominal"]["status"] == "nominal_model"
    }
    # Una qualificació futura amb dades noves necessita campanya i gate versionats.
    assert not complete_nominals, (
        "Canvi d’evidència: preregistrar una nova homologació nominal abans de decidir"
    )
    result = dict(
        ownerStep="7.14",
        numericStatus="PASS" if numeric else "FAIL",
        scientificExitPassed=False,
        status="BLOCKED_NOMINAL_RESPONSE_OR_COVERAGE"
        if numeric
        else "FAIL_NUMERIC_OR_REGRESSION",
        policySha256=policy_hash,
        checks=checks,
        qualifications=qualifications,
        newSpectralInstrumentHomologation=None,
        totalNominalNumericalErrorBoundMag=None,
        spectralNumericalMaximumMag=0.01,
        scientificCostSeconds=perf["calculationWallSeconds"],
        physicalTransportEvaluations=0,
        nextStep="7.14_pending_partial_blocked;7.15_not_started",
    )
    write_immutable(OUT / "gate-represa-v3.json", result)
    print(
        json.dumps(
            dict(
                status=result["status"],
                numericStatus=result["numericStatus"],
                checks=checks,
            ),
            ensure_ascii=False,
            indent=2,
        )
    )
    return numeric


def verify_manifest() -> bool:
    manifest = read(OUT / "manifest-final-represa-v3.json")
    differences = [
        p
        for key in ["sourceHashes", "documentHashes", "evidenceHashes"]
        for p, sha in manifest[key].items()
        if not (ROOT / p).is_file() or digest(ROOT / p) != sha
    ]
    print(
        json.dumps(dict(unchanged=not differences, differences=differences), indent=2)
    )
    return not differences


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--numeric-only", action="store_true")
    parser.add_argument("--verify-manifest", action="store_true")
    args = parser.parse_args()
    if args.verify_manifest:
        raise SystemExit(0 if verify_manifest() else 1)
    passed = audit()
    raise SystemExit(0 if passed and args.numeric_only else 1)
