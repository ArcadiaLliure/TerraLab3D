"""Gate preregistrat 7.12, files persistides abans/després de cada càlcul."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import platform
import time
from dataclasses import asdict, replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from transport_gate_fixtures_step7_12 import POLICY, ROOT, primary, vertical
from terralab3d.domain.light_pollution.atmospheric_tail import conditional_tail_bound
from terralab3d.domain.light_pollution.propagation_kernel import PropagationKernel
from terralab3d.domain.light_pollution.radiometric_gate import assess_transport
from terralab3d.domain.light_pollution.reference_single_scattering import (
    solve_reference_b1,
)
from terralab3d.domain.light_pollution.reference_spectral_transport import (
    solve_reference_spectral,
)
from terralab3d.domain.light_pollution.reference_variable_spectral import (
    solve_reference_variable_spectral,
)
from terralab3d.domain.light_pollution.transport_profiling import TransportProfiler

EXPECTED_POLICY_SHA = "6cfa6601f02dabeb1a3462638e980959c11a12164433738689efb31e92cdb442"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path, data):
    path.write_text(
        json.dumps(
            data,
            indent=2,
            ensure_ascii=False,
            allow_nan=False,
            default=lambda v: v.isoformat() if isinstance(v, datetime) else asdict(v),
        )
        + "\n",
        encoding="utf-8",
    )


def binding(output):
    assert digest(POLICY) == EXPECTED_POLICY_SHA, "El criteri congelat ha canviat"
    policy = json.loads(POLICY.read_text(encoding="utf-8"))
    paths = sorted(
        (ROOT / "backend/src/terralab3d/domain/light_pollution").glob("*.py")
    )
    paths += [
        ROOT
        / "backend/src/terralab3d/infrastructure/adapters/atmosphere/standard_optics.py",
        Path(__file__).resolve(),
        ROOT / "tools/transport_gate_fixtures_step7_12.py",
    ]
    current = {str(p.relative_to(ROOT)).replace("\\", "/"): digest(p) for p in paths}
    path = output / "vinculacio-candidat-v1.json"
    if path.exists():
        data = json.loads(path.read_text(encoding="utf-8"))
        assert data["codeHashes"] == current, (
            "Candidat modificat: conserveu la campanya i creeu una vinculació nova"
        )
    else:
        # Aquesta persistència precedeix qualsevol avaluació de radiància.
        inputs = {}
        for spec in policy["primaryCases"]:
            req = primary(spec)
            inputs[spec["id"]] = asdict(req)
        write(
            path,
            dict(
                policySha256=EXPECTED_POLICY_SHA,
                boundAtUtc=datetime.now(timezone.utc).isoformat(),
                python=platform.python_version(),
                codeHashes=current,
                primaryInputs=inputs,
            ),
        )
    return policy


def reference(req, refinement):
    assert req.optical_field
    source, direction = req.sources[0], req.directions.directions[0]
    kwargs = dict(
        path_order=refinement["pathGL"],
        area_order=refinement["areaGL"],
        relative_tolerance=refinement["losEpsrel"],
        terrain=req.terrain,
    )
    if req.scattering:
        return solve_reference_b1(
            source,
            req.observer,
            direction.azimuth_deg,
            direction.elevation_deg,
            req.optical_field,
            req.scattering.band,
            req.options.top_m,
            **kwargs,
        )
    assert req.spectral
    kwargs["spectral_order"] = refinement["spectralGL"]
    args = (
        source,
        req.observer,
        req.optical_field,
        req.spectral,
        direction.azimuth_deg,
        direction.elevation_deg,
        req.options.top_m,
    )
    if all(
        len(set(t.profile.pressure_pa)) == len(set(t.profile.temperature_k)) == 1
        for t in req.optical_field.tiles
    ):
        kwargs.pop("path_order")
        return solve_reference_spectral(*args, **kwargs)
    return solve_reference_variable_spectral(*args, **kwargs)


def measured(req) -> dict[str, Any]:
    profiler = TransportProfiler()
    start, cpu = time.perf_counter(), time.process_time()
    result = PropagationKernel().evaluate(req, profiler=profiler)
    return dict(
        value=result.rays[0].integral,
        wallSeconds=time.perf_counter() - start,
        cpuSeconds=time.process_time() - cpu,
        inputSignature=result.input_signature,
        unit=result.integral_unit,
        counters=asdict(result.counters),
        profiling=profiler.to_dict(),
    )


def gate(output, policy):
    for spec in policy["primaryCases"]:
        path = output / (spec["id"] + ".json")
        row: dict[str, Any] = (
            json.loads(path.read_text(encoding="utf-8"))
            if path.exists()
            else dict(
                case=spec, policySha256=EXPECTED_POLICY_SHA, runtime=[], references=[]
            )
        )
        if "decision" in row:
            continue
        req = primary(spec)
        for i in range(len(row["runtime"]), 2):
            print("runtime", spec["id"], i, flush=True)
            row["runtime"].append(measured(req))
            write(path, row)
        for r in policy["referenceRefinements"][len(row["references"]) :]:
            print("reference", spec["id"], r, flush=True)
            start = time.perf_counter()
            result = reference(req, r)
            row["references"].append(
                dict(
                    settings=r,
                    result=asdict(result),
                    wallSeconds=time.perf_counter() - start,
                )
            )
            write(path, row)
        refs = tuple(r["result"]["value"] for r in row["references"])
        errors = tuple(r["result"]["los_error_estimate"] for r in row["references"])
        row["decision"] = asdict(
            assess_transport(
                row["runtime"][0]["value"],
                refs,
                errors,
                relative_limit=policy["metric"]["maximumInclusive"],
                reference_resolution=policy["metric"][
                    "referenceUncertaintyMaximumRelative"
                ],
            )
        )
        row["repeatExact"] = row["runtime"][0]["value"] == row["runtime"][1]["value"]
        write(path, row)
        print("decision", spec["id"], row["decision"], flush=True)


def ceiling(output, policy):
    path = output / "convergencia-vertical.json"
    rows = json.loads(path.read_text(encoding="utf-8")) if path.exists() else []
    study = policy["verticalStudy"]
    for name in study["fixtures"]:
        for mode in study["modes"]:
            req = vertical(name, mode)
            for top in study["topsM"]:
                if any(
                    r["fixture"] == name and r["mode"] == mode and r["topM"] == top
                    for r in rows
                ):
                    continue
                print("ceiling", name, mode, top, flush=True)
                run = measured(
                    replace(req, options=replace(req.options, top_m=float(top)))
                )
                row: dict[str, Any] = dict(
                    fixture=name, mode=mode, topM=top, runtime=run
                )
                if top == study["tailTopM"]:
                    assert req.optical_field
                    pressure = req.optical_field.tiles[0].profile.pressure_pa[-1]
                    config = req.scattering or req.spectral
                    assert config
                    bound = conditional_tail_bound(
                        req.sources[0],
                        req.observer,
                        req.directions.directions[0],
                        float(top),
                        pressure,
                        config,
                    )
                    row["conditionalTail"] = asdict(bound)
                    row["tailMagnitudeUpper"] = 2.5 * math.log10(
                        1 + bound.upper_radiance / run["value"]
                    )
                    row["tailBudgetPass"] = (
                        row["tailMagnitudeUpper"] <= study["tailMaximumMagnitude"]
                    )
                rows.append(row)
                write(path, rows)
                print("ceiling-value", run["value"], run["wallSeconds"], flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--part", choices=("bind", "gate", "ceiling"), required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    protocol = binding(args.output)
    if args.part == "gate":
        gate(args.output, protocol)
    if args.part == "ceiling":
        ceiling(args.output, protocol)
