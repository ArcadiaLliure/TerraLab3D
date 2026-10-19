"""Gate v2 de reconstrucció: punts independents, costos, cua i preservació."""

from __future__ import annotations

import json
from collections import Counter

from validate_adaptive_dome_step7_13_v2 import (
    OUT,
    ROOT,
    binding,
    decode,
    digest,
    policy,
)
from validate_transport_gate_step7_12 import write

PROFILE_POLICY_SHA256 = (
    "ef3592046ddda218375d97a0788db2242d765de79ee10045fd5a29e97763ced1"
)


def audit():
    p = policy()
    binding()
    preservation = json.loads(
        (OUT / "preservacio-inicial.json").read_text(encoding="utf8")
    )
    differences = [
        name
        for name, sha in preservation["files"].items()
        if digest(ROOT / name) != sha
    ]
    cases = []
    decisions = []
    expected_points = {
        tuple(v)
        for v in json.loads(
            (OUT / "punts-independents-preregistrats.json").read_text(encoding="utf8")
        )["pointsAzimuthElevationDeg"]
    }
    for name in p["fixtures"]:
        stem = name.lower().replace("_", "-")
        built = json.loads((OUT / (stem + "-camp.json")).read_text(encoding="utf8"))
        holdout = json.loads(
            (OUT / (stem + "-holdout.json")).read_text(encoding="utf8")
        )
        assert digest(OUT / (stem + "-camp.json")) == holdout["frozenFieldSha256"]
        assert holdout["holdoutSha256"] == p["holdoutSha256"]
        samples = {(a, e) for a, e, v in built["samples"]}
        tested = {(r["azimuthDeg"], r["elevationDeg"]) for r in holdout["rows"]}
        field = decode(built["field"])
        replay = all(
            field.evaluate(r["azimuthDeg"], r["elevationDeg"]) == r["reconstructed"]
            for r in holdout["rows"]
        )
        independent = not (samples & tested)
        complete = tested == expected_points and len(holdout["rows"]) == len(
            expected_points
        )
        angular = complete and all(
            r["angularPass"]
            and r["reconstructed"] is not None
            and r["compressionErrorMag"] is not None
            and r["guardedReconstructionErrorMag"] is not None
            and 0 <= r["compressionErrorMag"] <= p["angularMagnitudeMaximum"]
            and 0 <= r["guardedReconstructionErrorMag"] <= p["angularMagnitudeMaximum"]
            for r in holdout["rows"]
        )
        limits = (
            built["sampleCount"] == len(samples) == len(built["samples"])
            and built["sampleCount"] <= p["cost"]["maximumSamplesPerFixture"]
            and built["azimuthProfiles"] <= p["cost"]["maximumAzimuthProfiles"]
            and built["wallSeconds"] <= p["cost"]["maximumBuildWallSecondsPerFixture"]
            and built["maximumVerticalProbeErrorMag"]
            <= p["algorithm"]["internalMagnitudeMaximum"]
            and built["maximumAzimuthProbeErrorMag"]
            <= p["algorithm"]["internalMagnitudeMaximum"]
        )
        decisions += [r["transportDecision"] for r in holdout["rows"]]
        cases.append(
            dict(
                name=name,
                independent=independent,
                complete=complete,
                angularPass=angular,
                reconstructionReplayed=replay,
                budgetsPass=limits,
                sampleCount=built["sampleCount"],
                azimuthProfiles=built["azimuthProfiles"],
                verticalKnots=built["verticalKnots"],
                buildWallSeconds=built["wallSeconds"],
                buildCpuSeconds=built["cpuSeconds"],
                maximumCompressionErrorMag=max(
                    (
                        r["compressionErrorMag"]
                        for r in holdout["rows"]
                        if r["compressionErrorMag"] is not None
                    ),
                    default=None,
                ),
                maximumGuardedReconstructionErrorMag=max(
                    (
                        r["guardedReconstructionErrorMag"]
                        for r in holdout["rows"]
                        if r["guardedReconstructionErrorMag"] is not None
                    ),
                    default=None,
                ),
                maximumGuardedTransportError=max(
                    r["transportDecision"]["guarded_relative_error"] or 0
                    for r in holdout["rows"]
                ),
                holdoutRuntimeWallSeconds=sum(
                    r["runtime"]["wallSeconds"] for r in holdout["rows"]
                ),
                holdoutReferenceWallSeconds=sum(
                    v["wallSeconds"] for r in holdout["rows"] for v in r["references"]
                ),
                fieldJsonBytes=len(
                    json.dumps(built["field"], ensure_ascii=False).encode("utf8")
                ),
            )
        )
    controls = json.loads((OUT / "controls-domini.json").read_text(encoding="utf8"))
    decisions += [r["transportDecision"] for r in controls]
    groups = dict(Counter(r["spec"]["group"] for r in controls))
    control_complete = groups == dict(coesa=3, terrain=12, area=3)
    coesa = [r for r in controls if r["spec"]["group"] == "coesa"]
    profile_policy_path = OUT / "criteri-perfil-coesa-preregistrat-v2.json"
    assert digest(profile_policy_path) == PROFILE_POLICY_SHA256
    profile_policy = json.loads(profile_policy_path.read_text(encoding="utf8"))
    profile_binding = json.loads(
        (OUT / "vinculacio-perfil-coesa.json").read_text(encoding="utf8")
    )
    assert profile_binding["policySha256"] == PROFILE_POLICY_SHA256
    assert profile_binding["codeSha256"] == digest(
        ROOT / "tools/validate_coesa_profile_step7_13_v2.py"
    )
    profile_result = json.loads(
        (OUT / "perfil-coesa-holdout.json").read_text(encoding="utf8")
    )
    assert profile_result["frozenProfileSha256"] == digest(
        OUT / "perfil-coesa-congelat.json"
    )
    assert profile_result["policySha256"] == digest(
        OUT / "criteri-perfil-coesa-preregistrat-v2.json"
    )
    profile_rows = profile_result["rows"]
    profile_training = json.loads(
        (OUT / "perfil-coesa-entrenament.json").read_text(encoding="utf8")
    )
    frozen_profile = json.loads(
        (OUT / "perfil-coesa-congelat.json").read_text(encoding="utf8")
    )
    profile_complete = (
        len(profile_rows) == 3
        and {r["elevationDeg"] for r in profile_rows}
        == set(profile_policy["independentElevationsDeg"])
        and not (
            set(profile_policy["trainingElevationsDeg"])
            & set(profile_policy["independentElevationsDeg"])
        )
        and [r["elevationDeg"] for r in profile_training]
        == profile_policy["trainingElevationsDeg"]
        and frozen_profile["radiances"]
        == [r["runtime"]["value"] for r in profile_training]
        and frozen_profile["elevations_deg"] == profile_policy["trainingElevationsDeg"]
    )
    decisions += [r["transportDecision"] for r in profile_rows]
    tail_pass = (
        len(coesa) == 3
        and len(profile_rows) == 3
        and all(
            0 < r["conditionalTail"]["upper_radiance"]
            and r["tailMagnitudeUpper"] <= p["tailMaximumMag"]
            for r in coesa + profile_rows
        )
    )
    transport_pass = all(d["status"] == "PASS" for d in decisions)
    phase_times = {
        name: json.loads((OUT / f"temps-{name}.json").read_text(encoding="utf8"))
        for name in ("holdout", "controls", "perfil-coesa")
    }
    cost = sum(c["buildWallSeconds"] for c in cases) + sum(
        v["wallSeconds"] for v in phase_times.values()
    )
    checks = dict(
        angular=all(c["angularPass"] for c in cases),
        reconstructionReplayed=all(c["reconstructionReplayed"] for c in cases),
        independent=all(c["independent"] for c in cases),
        constructionBudgets=all(c["budgetsPass"] for c in cases),
        transport=transport_pass,
        controlsComplete=control_complete,
        coesaVerticalProfile=profile_complete
        and all(
            r["angularPass"]
            and 0
            <= r["guardedReconstructionErrorMag"]
            <= profile_policy["angularMagnitudeMaximum"]
            for r in profile_rows
        ),
        conditionalTail=tail_pass,
        historicalEvidence=not differences,
        measuredCostBelowCampaignLimit=cost
        <= p["cost"]["maximumScientificCampaignWallSeconds"],
        serialScientificPhases=all(v["serialExecution"] for v in phase_times.values()),
        scientificSubprocessesCompleted=all(
            v.get("exitCode", 0) == 0 for v in phase_times.values()
        ),
    )
    passed = all(checks.values())
    result = dict(
        status="PASS_REGISTERED_ANGULAR_DOMAIN" if passed else "FAIL_OR_INCOMPLETE",
        angularMagnitudeMaximum=p["angularMagnitudeMaximum"],
        checks=checks,
        cases=cases,
        transportDecisionCounts=dict(Counter(d["status"] for d in decisions)),
        controlGroups=groups,
        maximumConditionalTailMag=max(
            r["tailMagnitudeUpper"] for r in coesa + profile_rows
        ),
        coesaProfileMaximumGuardedErrorMag=max(
            r["guardedReconstructionErrorMag"] for r in profile_rows
        ),
        coesaProfileDomain=profile_policy["scope"],
        terrainExactZeros=sum(
            r["runtime"]["value"] == 0
            for r in controls
            if r["spec"]["group"] == "terrain"
        ),
        historicalEvidenceCount=len(preservation["files"]),
        historicalDifferences=differences,
        measuredScientificWallSeconds=cost,
        phaseTimes=phase_times,
        holdoutReferenceAndSetupWallUpperSeconds=phase_times["holdout"]["wallSeconds"]
        - sum(c["holdoutRuntimeWallSeconds"] for c in cases),
        holdoutSetupAndSerializationWallSeconds=phase_times["holdout"]["wallSeconds"]
        - sum(
            c["holdoutRuntimeWallSeconds"] + c["holdoutReferenceWallSeconds"]
            for c in cases
        ),
        domain=p["domain"],
        observationallyValidated=False,
        coesaAngularCompressionCertified=False,
        demAngularInterpolationCertified=False,
        areaAngularCompressionCertified=False,
        nextStepExecutionStarted=False,
    )
    write(OUT / "gate-adaptatiu-v2.json", result)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return passed


if __name__ == "__main__":
    raise SystemExit(0 if audit() else 1)
