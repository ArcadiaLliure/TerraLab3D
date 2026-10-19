"""Campanya aparellada 7.11, aïllada d'altres feines numèriques."""

from __future__ import annotations

import argparse
from dataclasses import asdict, replace
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import platform
import random
import time

import numpy as np

from benchmark_skyglow_b0 import cpu_model, memory_snapshot
from terrain_fixtures_step7_11 import request, mountain_surface
from terralab3d.domain.light_pollution.geometric_transport import ViewDirection
from terralab3d.domain.light_pollution.propagation_kernel import (
    DirectionSet,
    PropagationKernel,
)
from terralab3d.domain.light_pollution.transport_profiling import TransportProfiler


def run(output: Path):
    protocol = json.loads(
        (output / "protocol-visibilitat-v1.json").read_text(encoding="utf8")
    )
    p = protocol["performance"]
    requests = {}
    for mode in p["modes"]:
        base = request(mode)
        base = replace(
            base,
            sources=tuple(
                replace(base.sources[0], source_model_id=f"S-{i}")
                for i in range(p["sources"])
            ),
            directions=DirectionSet(
                tuple(ViewDirection(f"e-{e}", 90, e) for e in p["elevationsDeg"])
            ),
        )
        for terrain in ("none", "flat", "mountain"):
            requests[f"{mode}/{terrain}"] = replace(
                base,
                terrain=None
                if terrain == "none"
                else mountain_surface(0.0)
                if terrain == "flat"
                else base.terrain,
            )
    source_paths = list(
        Path("backend/src/terralab3d/domain/light_pollution").glob("*.py")
    ) + [Path(__file__), Path("tools/terrain_fixtures_step7_11.py")]
    result = {
        "protocol": protocol,
        "timeUtc": datetime.now(timezone.utc).isoformat(),
        "hardware": {
            "cpu": cpu_model(),
            "python": platform.python_version(),
            "os": platform.platform(),
            "numpy": np.__version__,
        },
        "codeHashes": {
            str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in source_paths
        },
        "warmups": [],
        "measurements": [],
        "summary": {},
        "noOtherNumericalJob": True,
        "fixtures": "ten distinct source IDs at same5km location;90LOS; not historical900LOS distribution",
    }
    kernel = PropagationKernel()
    rng = random.Random(p["seed"])
    for phase, n in (("warmups", p["warmups"]), ("measurements", p["measurements"])):
        for iteration in range(n):
            order = list(requests)
            rng.shuffle(order)
            for label in order:
                profiler = TransportProfiler()
                start = time.perf_counter()
                value = kernel.evaluate(requests[label], profiler=profiler)
                elapsed = time.perf_counter() - start
                row = {
                    "case": label,
                    "iteration": iteration,
                    "seconds": elapsed,
                    "profile": profiler.to_dict(),
                    "counters": asdict(value.counters),
                    "signature": value.input_signature,
                    "radiances": [r.integral for r in value.rays],
                    "unit": value.integral_unit,
                    "terrainWork": value.terrain_metadata["work"]
                    if value.terrain_metadata
                    else None,
                }
                result[phase].append(row)
                output.joinpath("rendiment-b0-b1-b2-b4.json").write_text(
                    json.dumps(result, ensure_ascii=False, indent=2), encoding="utf8"
                )
                print(phase, iteration, label, round(elapsed, 3), flush=True)
    for label in requests:
        rows = [r for r in result["measurements"] if r["case"] == label]
        times = [r["seconds"] for r in rows]
        result["summary"][label] = {
            "n": len(rows),
            "p50Seconds": float(np.median(times)),
            "p95Seconds": float(np.percentile(times, 95)),
            "meanExclusiveSeconds": {
                stage: float(
                    np.mean([r["profile"]["exclusiveMs"][stage] / 1000 for r in rows])
                )
                for stage in rows[0]["profile"]["exclusiveMs"]
            },
        }
    result["memory"] = memory_snapshot()
    result["areaMeasurements"] = []
    result["areaSummary"] = {}
    area_protocol = protocol["areaPerformance"]
    area_requests = {
        f"{mode}/{terrain}": replace(
            request(mode, area=True),
            terrain=None if terrain == "none" else mountain_surface(),
        )
        for mode in ("B1", "B4")
        for terrain in ("none", "mountain")
    }
    for phase, n in (("warmup", 1), ("measurement", area_protocol["measurements"])):
        for iteration in range(n):
            labels = list(area_requests)
            rng.shuffle(labels)
            for label in labels:
                profile = TransportProfiler()
                start = time.perf_counter()
                value = kernel.evaluate(area_requests[label], profiler=profile)
                row = {
                    "case": label,
                    "phase": phase,
                    "iteration": iteration,
                    "seconds": time.perf_counter() - start,
                    "profile": profile.to_dict(),
                    "value": value.rays[0].integral,
                    "terrainWork": value.terrain_metadata["work"]
                    if value.terrain_metadata
                    else None,
                }
                result["areaMeasurements"].append(row)
                output.joinpath("rendiment-b0-b1-b2-b4.json").write_text(
                    json.dumps(result, ensure_ascii=False, indent=2), encoding="utf8"
                )
                print(
                    "area",
                    phase,
                    iteration,
                    label,
                    round(row["seconds"], 3),
                    flush=True,
                )
    for label in area_requests:
        rows = [
            r
            for r in result["areaMeasurements"]
            if r["case"] == label and r["phase"] == "measurement"
        ]
        result["areaSummary"][label] = {
            "n": len(rows),
            "p50Seconds": float(np.median([r["seconds"] for r in rows])),
            "meanOcclusionSeconds": float(
                np.mean([r["profile"]["exclusiveMs"]["occlusion"] / 1000 for r in rows])
            ),
        }
    result["memory"] = memory_snapshot()
    output.joinpath("rendiment-b0-b1-b2-b4.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf8"
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    run(parser.parse_args().output)
