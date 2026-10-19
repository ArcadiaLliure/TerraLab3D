"""Campanya adaptativa v2 serial: construcció, congelació i holdout separat."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import time
from dataclasses import asdict, replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from angular_fixtures_step7_13 import fixture
from transport_gate_fixtures_step7_12 import ROOT, primary
from validate_transport_gate_step7_12 import measured, reference, write
from terralab3d.application.adaptive_dome_sampling import sample_adaptive_dome
from terralab3d.domain.light_pollution.adaptive_dome import (
    AdaptiveDomeField,
    AdaptiveSettings,
    magnitude_error,
)
from terralab3d.domain.light_pollution.atmospheric_tail import conditional_tail_bound
from terralab3d.domain.light_pollution.dome_profile import DomeProfile
from terralab3d.domain.light_pollution.geometric_transport import ViewDirection
from terralab3d.domain.light_pollution.propagation_kernel import DirectionSet
from terralab3d.domain.light_pollution.radiometric_gate import assess_transport

OUT = ROOT / "docs/evidencies/pas7.13/adaptatiu-v2"
EXPECTED_POLICY = "1b75bda8a311b65eecaecfb3f47ebdef51406f690935e2c12f836040b8f42b3f"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def policy() -> Any:
    path = OUT / "criteri-adaptatiu-preregistrat-v2.json"
    assert digest(path) == EXPECTED_POLICY
    return json.loads(path.read_text(encoding="utf8"))


def binding() -> Any:
    p = policy()
    paths = sorted(
        (ROOT / "backend/src/terralab3d/domain/light_pollution").glob("*.py")
    )
    paths += [
        ROOT / "backend/src/terralab3d/application/adaptive_dome_sampling.py",
        ROOT / "tools/angular_fixtures_step7_13.py",
        Path(__file__).resolve(),
    ]
    current = {f.relative_to(ROOT).as_posix(): digest(f) for f in paths}
    path = OUT / "vinculacio-candidat-v2.json"
    if path.exists():
        data = json.loads(path.read_text(encoding="utf8"))
        assert data["codeHashes"] == current, (
            "Candidat canviat: cal versió de campanya nova"
        )
        return data
    data = dict(
        boundAtUtc=datetime.now(timezone.utc).isoformat(),
        policySha256=EXPECTED_POLICY,
        codeHashes=current,
        fullInputs={name: asdict(fixture(name)) for name in p["fixtures"]},
    )
    write(path, data)
    return data


def decode(data: Any) -> AdaptiveDomeField:
    profiles = tuple(
        DomeProfile(
            row["azimuthDeg"],
            tuple(row["elevationSamplesDeg"]),
            tuple(row["radianceSamples"]),
            row["epsilonRadiance"],
            tuple(row["blockedIntervals"]),
        )
        for row in data["profiles"]
    )
    return AdaptiveDomeField(
        profiles,
        data["radianceUnit"],
        data["provenance"],
        data["revision"],
        data["topM"],
        tuple(data["blockedAzimuthIntervals"]),
        data["directOnly"],
    )


def build(names: list[str]) -> None:
    p = policy()
    binding()
    for name in names:
        path = OUT / (name.lower().replace("_", "-") + "-camp.json")
        if path.exists():
            continue
        start, cpu = time.perf_counter(), time.process_time()

        def progress(n, az, el):
            if n % 100 == 0:
                row = dict(
                    name=name,
                    samples=n,
                    lastAzimuthDeg=az,
                    lastElevationDeg=el,
                    wallSeconds=time.perf_counter() - start,
                )
                write(OUT / "progres-construccio.json", row)
                print(row, flush=True)

        result = sample_adaptive_dome(
            fixture(name),
            settings=AdaptiveSettings(),
            maximum_wall_seconds=p["cost"]["maximumBuildWallSecondsPerFixture"],
            checkpoint=progress,
        )
        data = dict(
            name=name,
            frozenAtUtc=datetime.now(timezone.utc).isoformat(),
            policySha256=EXPECTED_POLICY,
            field=result.field.to_dict(),
            samples=result.samples,
            sampleCount=len(result.samples),
            azimuthProfiles=len(result.field.profiles),
            verticalKnots=sum(len(v.elevations_deg) for v in result.field.profiles),
            maximumVerticalProbeErrorMag=result.maximum_vertical_probe_error_mag,
            maximumAzimuthProbeErrorMag=result.maximum_azimuth_probe_error_mag,
            azimuthIterations=result.azimuth_iterations,
            wallSeconds=time.perf_counter() - start,
            cpuSeconds=time.process_time() - cpu,
        )
        write(path, data)
        print(
            "frozen",
            name,
            data["sampleCount"],
            data["azimuthProfiles"],
            data["wallSeconds"],
            flush=True,
        )


def holdout(names: list[str]) -> None:
    p = policy()
    binding()
    points_path = OUT / "punts-independents-preregistrats.json"
    assert digest(points_path) == p["holdoutSha256"]
    points = json.loads(points_path.read_text(encoding="utf8"))[
        "pointsAzimuthElevationDeg"
    ]
    for name in names:
        field_path = OUT / (name.lower().replace("_", "-") + "-camp.json")
        data = json.loads(field_path.read_text(encoding="utf8"))
        field = decode(data["field"])
        used = {(a, e) for a, e, v in data["samples"]}
        assert not (used & {tuple(v) for v in points}), (
            "Holdout utilitzat per ajustar refinament"
        )
        path = OUT / (name.lower().replace("_", "-") + "-holdout.json")
        rows = (
            json.loads(path.read_text(encoding="utf8"))["rows"] if path.exists() else []
        )
        frozen = digest(field_path)
        for i, (az, el) in enumerate(points):
            if i < len(rows):
                continue
            assert digest(field_path) == frozen, "Camp modificat durant el holdout"
            req = replace(
                fixture(name),
                directions=DirectionSet(
                    (ViewDirection("independent-holdout", az, el),)
                ),
            )
            run = measured(req)
            refs = []
            for level in p["referenceLevels"]:
                start = time.perf_counter()
                ref = reference(req, level)
                refs.append(
                    dict(result=asdict(ref), wallSeconds=time.perf_counter() - start)
                )
            decision = assess_transport(
                run["value"],
                tuple(r["result"]["value"] for r in refs),
                tuple(r["result"]["los_error_estimate"] for r in refs),
                relative_limit=p["transportRelativeMaximum"],
                reference_resolution=p["referenceRelativeMaximum"],
            )
            reconstructed = field.evaluate(az, el)
            error = magnitude_error(reconstructed, run["value"])
            lower, upper = (
                decision.reference - decision.reference_uncertainty,
                decision.reference + decision.reference_uncertainty,
            )
            guarded = (
                max(
                    magnitude_error(reconstructed, lower),
                    magnitude_error(reconstructed, upper),
                )
                if lower > 0
                else error
            )
            rows.append(
                dict(
                    azimuthDeg=az,
                    elevationDeg=el,
                    runtime=run,
                    references=refs,
                    transportDecision=asdict(decision),
                    reconstructed=reconstructed,
                    compressionErrorMag=error if math.isfinite(error) else None,
                    guardedReconstructionErrorMag=guarded
                    if math.isfinite(guarded)
                    else None,
                    angularPass=guarded <= p["angularMagnitudeMaximum"]
                    and error <= p["angularMagnitudeMaximum"],
                )
            )
            write(
                path,
                dict(
                    name=name,
                    frozenFieldSha256=frozen,
                    holdoutSha256=p["holdoutSha256"],
                    rows=rows,
                ),
            )
            if len(rows) % 50 == 0:
                print(
                    "holdout",
                    name,
                    len(rows),
                    "failures",
                    sum(not r["angularPass"] for r in rows),
                    flush=True,
                )


def controls() -> None:
    p = policy()
    binding()
    specs = [dict(s, group="coesa") for s in p["coesaControls"]]
    specs += [
        dict(
            fixture="S_B4_chamber_mountain_point_5km",
            azimuthDeg=a,
            elevationDeg=e,
            group="terrain",
        )
        for a in p["terrainControls"]["azimuthsDeg"]
        for e in p["terrainControls"]["elevationsDeg"]
    ]
    specs += [
        dict(
            fixture=p["areaControls"]["fixture"],
            azimuthDeg=a,
            elevationDeg=e,
            group="area",
        )
        for a, e in p["areaControls"]["directionsDeg"]
    ]
    path = OUT / "controls-domini.json"
    rows = json.loads(path.read_text(encoding="utf8")) if path.exists() else []
    for spec in specs[len(rows) :]:
        if spec["group"] == "area":
            req = primary(
                dict(
                    mode="B4",
                    standard=False,
                    area=True,
                    distanceM=5000,
                    elevationDeg=90,
                    terrain="none",
                )
            )
            chamber = fixture("S_B4_chamber_point_5km")
            req = replace(
                req,
                optical_field=chamber.optical_field,
                spectral=chamber.spectral,
                options=chamber.options,
            )
        else:
            req = fixture(spec["fixture"])
        req = replace(
            req,
            directions=DirectionSet(
                (
                    ViewDirection(
                        "domain-control", spec["azimuthDeg"], spec["elevationDeg"]
                    ),
                )
            ),
        )
        # Les entrades completes dels controls es persisteixen abans de la radiància.
        write(OUT / "control-en-curs-input.json", dict(spec=spec, request=asdict(req)))
        run = measured(req)
        refs = [asdict(reference(req, level)) for level in p["referenceLevels"]]
        decision = assess_transport(
            run["value"],
            tuple(r["value"] for r in refs),
            tuple(r["los_error_estimate"] for r in refs),
            relative_limit=p["transportRelativeMaximum"],
            reference_resolution=p["referenceRelativeMaximum"],
        )
        row: dict[str, Any] = dict(
            spec=spec,
            fullInput=asdict(req),
            runtime=run,
            references=refs,
            transportDecision=asdict(decision),
        )
        if spec["group"] == "coesa":
            assert req.optical_field and req.spectral
            tail = conditional_tail_bound(
                req.sources[0],
                req.observer,
                req.directions.directions[0],
                75000.0,
                req.optical_field.tiles[0].profile.pressure_pa[-1],
                req.spectral,
            )
            row["conditionalTail"] = asdict(tail)
            row["tailMagnitudeUpper"] = 2.5 * math.log10(
                1
                + tail.upper_radiance
                / (decision.reference - decision.reference_uncertainty)
            )
        rows.append(row)
        write(path, rows)
        print("control", spec, decision.status, flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--part", choices=("bind", "build", "holdout", "controls"), required=True
    )
    parser.add_argument("--case", choices=policy()["fixtures"])
    args = parser.parse_args()
    names = [args.case] if args.case else policy()["fixtures"]
    if args.part == "bind":
        binding()
    elif args.part == "build":
        build(names)
    elif args.part == "holdout":
        holdout(names)
    else:
        controls()
