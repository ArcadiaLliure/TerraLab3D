"""Deriva CSV i mètriques dels registres temporals, sense repetir mesures."""

from __future__ import annotations

import argparse
import csv
import json
import os
from pathlib import Path

import numpy as np


def summarize(root: Path):
    data = json.loads((root / "resultats-b0-b1-b2-b4.json").read_text(encoding="utf-8"))
    assert "summary" in data, "La campanya encara no ha acabat"
    rows = []
    stages = (
        "geometry",
        "atmospheric_sampling",
        "transmissions",
        "quadrature",
        "spectral_integration",
    )
    for run in data["runs"]:
        row = {
            "mode": run["mode"],
            "iteration": run["iteration"],
            "wall_ms": run["wallMs"],
            "cpu_ms": run["cpuMs"],
            **run["counters"],
            "rss_bytes": run["memory"][0],
            "process_peak_rss_bytes": run["memory"][1],
            **{
                stage + "_ms": run["profiling"]["exclusiveMs"][stage]
                for stage in stages
            },
        }
        row["unclassified_and_timer_overhead_ms"] = run["wallMs"] - sum(
            run["profiling"]["exclusiveMs"].values()
        )
        rows.append(row)
    with (root / "passades-b0-b1-b2-b4.csv").open(
        "w", newline="", encoding="utf-8"
    ) as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    result = {
        "sourceFile": "resultats-b0-b1-b2-b4.json",
        "seed": "0x544C3344534B5947",
        "modelVersion": "single-scattering-spectral-direct-v1",
        "datasetFixtureVersion": "B1_positions_7.9;B2_B4_CIE_LED_B3;O3_prescribed_4e-8",
        "logicalCpuCountQueriedAfterCampaign": os.cpu_count(),
        "ramBytesAtCampaignStart": data["hardware"]["memory"][2],
        "thermalThrottling": "not_exposed",
        "gpu": "not_used",
        "timingDefinition": {
            "geometry": "rays, LOS partition, optical path intersections and spectral angular geometry",
            "atmospheric_sampling": "OpticalField.sample and direct homogeneous P/T retrieval",
            "transmissions": "extinction, phases and exponentials; B1 includes legacy angular arithmetic",
            "quadrature": "GK plus node dispatch and bookkeeping outside classified child stages",
            "spectral_integration": "source/response/rule preparation and spectral sums; includes LUT spectral interpolation at setup",
            "remainder": "request identities, result construction, timer accounting and other untimed setup",
        },
        "modes": {},
    }
    for mode, latency in data["summary"].items():
        selected = [r for r in rows if r["mode"] == mode]
        result["modes"][mode] = {
            **latency,
            "meanStageMs": {
                stage: float(np.mean([r[stage + "_ms"] for r in selected]))
                for stage in stages
            },
            "meanRemainderMs": float(
                np.mean([r["unclassified_and_timer_overhead_ms"] for r in selected])
            ),
            "meanWallMs": float(np.mean([r["wall_ms"] for r in selected])),
            "losPerSecondAtMedian": 900000 / latency["p50Ms"],
            "peakProcessRssBytes": max(r["process_peak_rss_bytes"] for r in selected),
        }
    result["medianRatios"] = {
        "B2_over_B1": result["modes"]["B2"]["p50Ms"] / result["modes"]["B1"]["p50Ms"],
        "B4_over_B2": result["modes"]["B4"]["p50Ms"] / result["modes"]["B2"]["p50Ms"],
        "B4_over_B1": result["modes"]["B4"]["p50Ms"] / result["modes"]["B1"]["p50Ms"],
    }
    (root / "resum-cost-etapes.json").write_text(
        json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(json.dumps(result["modes"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", required=True, type=Path)
    summarize(parser.parse_args().root)
