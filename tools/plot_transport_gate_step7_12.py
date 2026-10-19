"""Figures científiques del gate; consumeix mesures, no les genera."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


def run(root):
    campaign = root / "campanya-v1"
    policy = json.loads(
        (root / "criteri-transport-preregistrat-v1.json").read_text(encoding="utf-8")
    )
    cases = [
        json.loads((campaign / (s["id"] + ".json")).read_text(encoding="utf-8"))
        for s in policy["primaryCases"]
    ]
    vertical = json.loads(
        (campaign / "convergencia-vertical.json").read_text(encoding="utf-8")
    )
    fig, axes = plt.subplots(1, 2, figsize=(13, 5.5), layout="constrained")
    labels = [r["case"]["id"].replace("S_", "").replace("_", " ") for r in cases]
    errors = [r["decision"]["guarded_relative_error"] for r in cases]
    for i, (r, error) in enumerate(zip(cases, errors)):
        if error is not None:
            axes[0].barh(
                i,
                error,
                color="#267a59" if r["decision"]["status"] == "PASS" else "#bc4343",
            )
        else:
            axes[0].text(2e-13, i, "zero geomètric exacte", va="center", fontsize=8)
    axes[0].set_yticks(range(len(labels)), labels, fontsize=8)
    axes[0].set_xscale("log")
    axes[0].set_xlim(1e-13, 2e-4)
    axes[0].axvline(
        1e-4, color="#bc4343", linestyle="--", label="Llindar congelat 10⁻⁴"
    )
    axes[0].set_xlabel("(|I−R|+u_ref)/R")
    axes[0].set_title("Gate del mateix transport directe")
    axes[0].legend(fontsize=8)
    axes[0].grid(axis="x", alpha=0.2)
    for name, label in (
        ("pas7.10_original_B4_standard", "Original 7.10 (~20 km)"),
        ("S_near5km", "Font a 5 km"),
        ("S_far200km", "Font a 200 km"),
    ):
        rows = sorted(
            (r for r in vertical if r["fixture"] == name and r["mode"] == "B4"),
            key=lambda r: r["topM"],
        )
        high = rows[-1]["runtime"]["value"]
        axes[1].plot(
            [r["topM"] / 1000 for r in rows],
            [r["runtime"]["value"] / high for r in rows],
            "o-",
            label=label,
        )
        last = rows[-1]
        value = last["tailMagnitudeUpper"]
        unit = 10 ** (math.floor(math.log10(value)) - 3)
        displayed_upper = math.ceil(value / unit) * unit
        axes[1].annotate(
            f"cua ≤{displayed_upper:.4g} mag",
            (75, last["runtime"]["value"] / high),
            xytext=(-4, -18 - 12 * len(axes[1].lines)),
            textcoords="offset points",
            ha="right",
            fontsize=8,
        )
    axes[1].set_xlabel("Sostre atmosfèric (km)")
    axes[1].set_ylabel("Radiància B4 / radiància fins a 75 km")
    axes[1].set_title("Convergència vertical; cua exterior positiva")
    axes[1].legend(loc="lower right", fontsize=8)
    axes[1].grid(alpha=0.2)
    fig.suptitle(
        "7.12 — Precisió numèrica i domini atmosfèric explícit\nDispersió simple prescrita; cap homologació observacional",
        fontsize=12,
    )
    fig.savefig(root / "gate-i-convergencia-vertical.png", dpi=160)
    plt.close(fig)
    rows = json.loads(
        (root / "rendiment-b0-b4-actual.json").read_text(encoding="utf-8")
    )
    fig, axes = plt.subplots(1, 2, figsize=(12, 5), layout="constrained")
    stages = (
        "geometry",
        "occlusion",
        "atmospheric_sampling",
        "transmissions",
        "quadrature",
        "spectral_integration",
    )
    colors = ("#5999c5", "#bd654c", "#64a778", "#a187b6", "#d7b056", "#4c9995")
    names = (
        "geometria",
        "oclusió",
        "mostreig",
        "transmissions",
        "quadratura",
        "espectre",
    )
    for axis, selected, title in (
        (
            axes[0],
            [r for r in rows if not r.get("fixture") and r["iteration"] == 1],
            "900 LOS, medi homogeni; repetició",
        ),
        (
            axes[1],
            [
                r
                for r in rows
                if r.get("fixture") == "area_mountain" and r["iteration"] == 1
            ],
            "1 LOS, font extensa i muntanya; repetició",
        ),
    ):
        bottom = np.zeros(len(selected))
        for stage, color, label in zip(stages, colors, names):
            values = np.array(
                [r["profiling"]["exclusiveMs"][stage] / 1000 for r in selected]
            )
            axis.bar(
                [r["mode"] for r in selected],
                values,
                bottom=bottom,
                color=color,
                label=label,
            )
            bottom += values
        axis.set_ylabel("Temps exclusiu (s)")
        axis.set_title(title, fontsize=11)
        axis.grid(axis="y", alpha=0.2)
    axes[0].legend(fontsize=8)
    fig.suptitle(
        "Cost actual B0–B4: sense acceleracions ni extrapolació d'àrees a 900 LOS",
        fontsize=12,
    )
    fig.savefig(root / "cost-transport-i-oclusio.png", dpi=160)
    plt.close(fig)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    run(parser.parse_args().root)
