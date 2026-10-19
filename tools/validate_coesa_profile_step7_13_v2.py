"""Control PCHIP de camp COESA variable, prospectiu i limitat a set LOS."""

import json
import math
import time
from dataclasses import asdict, replace
from pathlib import Path

from angular_fixtures_step7_13 import fixture
from validate_adaptive_dome_step7_13_v2 import OUT, binding, digest, policy
from validate_transport_gate_step7_12 import measured, reference, write
from terralab3d.domain.light_pollution.atmospheric_tail import conditional_tail_bound
from terralab3d.domain.light_pollution.dome_profile import DomeProfile
from terralab3d.domain.light_pollution.geometric_transport import ViewDirection
from terralab3d.domain.light_pollution.propagation_kernel import DirectionSet
from terralab3d.domain.light_pollution.radiometric_gate import assess_transport
from terralab3d.domain.light_pollution.adaptive_dome import magnitude_error


def run():
    binding()
    parent = policy()
    registered = OUT / "criteri-perfil-coesa-preregistrat-v2.json"
    assert (
        digest(registered)
        == registered.with_suffix(".sha256").read_text(encoding="ascii").strip()
    )
    p = json.loads(registered.read_text(encoding="utf8"))
    cost = sum(
        json.loads(
            (OUT / (n.lower().replace("_", "-") + "-camp.json")).read_text(
                encoding="utf8"
            )
        )["wallSeconds"]
        for n in parent["fixtures"]
    )
    cost += sum(
        json.loads((OUT / f"temps-{name}.json").read_text(encoding="utf8"))[
            "wallSeconds"
        ]
        for name in ("holdout", "controls")
    )
    assert (
        cost + p["costEstimateSeconds"]
        <= parent["cost"]["maximumScientificCampaignWallSeconds"]
    ), "Campanya desproporcionada"
    request = fixture(p["fixture"])
    write(
        OUT / "vinculacio-perfil-coesa.json",
        dict(
            policySha256=digest(registered),
            codeSha256=digest(Path(__file__)),
            fullInput=asdict(request),
            costBeforeSeconds=cost,
            estimateSeconds=p["costEstimateSeconds"],
        ),
    )
    start = time.perf_counter()

    def req(e):
        return replace(
            request,
            directions=DirectionSet(
                (ViewDirection("coesa-profile", p["azimuthDeg"], e),)
            ),
        )

    train_path = OUT / "perfil-coesa-entrenament.json"
    train = (
        json.loads(train_path.read_text(encoding="utf8")) if train_path.exists() else []
    )
    for e in p["trainingElevationsDeg"][len(train) :]:
        train.append(dict(elevationDeg=e, runtime=measured(req(e))))
        write(train_path, train)
        print("coesa-node", e, train[-1]["runtime"]["wallSeconds"], flush=True)
    values = tuple(r["runtime"]["value"] for r in train)
    profile = DomeProfile(
        p["azimuthDeg"],
        tuple(float(e) for e in p["trainingElevationsDeg"]),
        values,
        min(values) * 1e-15,
    )
    frozen_path = OUT / "perfil-coesa-congelat.json"
    if not frozen_path.exists():
        write(frozen_path, asdict(profile))
    frozen = digest(frozen_path)
    result_path = OUT / "perfil-coesa-holdout.json"
    rows = (
        json.loads(result_path.read_text(encoding="utf8"))["rows"]
        if result_path.exists()
        else []
    )
    for e in p["independentElevationsDeg"][len(rows) :]:
        assert digest(frozen_path) == frozen
        r = req(e)
        run_result = measured(r)
        refs = [asdict(reference(r, level)) for level in parent["referenceLevels"]]
        decision = assess_transport(
            run_result["value"],
            tuple(v["value"] for v in refs),
            tuple(v["los_error_estimate"] for v in refs),
            relative_limit=p["transportRelativeMaximum"],
            reference_resolution=p["referenceRelativeMaximum"],
        )
        predicted = profile.evaluate(e)
        guarded = max(
            magnitude_error(
                predicted, decision.reference - decision.reference_uncertainty
            ),
            magnitude_error(
                predicted, decision.reference + decision.reference_uncertainty
            ),
        )
        assert r.optical_field and r.spectral
        bound = conditional_tail_bound(
            r.sources[0],
            r.observer,
            r.directions.directions[0],
            75000.0,
            r.optical_field.tiles[0].profile.pressure_pa[-1],
            r.spectral,
        )
        tail_mag = 2.5 * math.log10(
            1
            + bound.upper_radiance
            / (decision.reference - decision.reference_uncertainty)
        )
        error = magnitude_error(predicted, run_result["value"])
        rows.append(
            dict(
                elevationDeg=e,
                runtime=run_result,
                references=refs,
                transportDecision=asdict(decision),
                reconstructed=predicted,
                compressionErrorMag=error,
                guardedReconstructionErrorMag=guarded,
                conditionalTail=asdict(bound),
                tailMagnitudeUpper=tail_mag,
                angularPass=guarded <= p["angularMagnitudeMaximum"]
                and error <= p["angularMagnitudeMaximum"],
            )
        )
        write(
            result_path,
            dict(
                frozenProfileSha256=frozen, policySha256=digest(registered), rows=rows
            ),
        )
        print("coesa-holdout", e, decision.status, guarded, flush=True)
    total = time.perf_counter() - start
    write(
        OUT / "temps-perfil-coesa.json",
        dict(
            wallSeconds=total,
            serialExecution=True,
            costBeforeSeconds=cost,
            measuredCampaignSeconds=cost + total,
            estimateSeconds=p["costEstimateSeconds"],
        ),
    )
    assert cost + total <= parent["cost"]["maximumScientificCampaignWallSeconds"]
    return all(
        r["angularPass"]
        and r["transportDecision"]["status"] == "PASS"
        and r["tailMagnitudeUpper"] <= p["tailMaximumMagnitude"]
        for r in rows
    )


if __name__ == "__main__":
    raise SystemExit(0 if run() else 1)
