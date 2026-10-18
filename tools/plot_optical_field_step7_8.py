"""Representa perfils i convergència de l'evidència del camp òptic 7.8."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    data = json.loads(args.input.read_text(encoding="utf-8"))
    profile = data["cases"][0]["field"]["tiles"][0]["profile"]
    heights = [h / 1000 for h in profile["heights_m"]]
    fig, axes = plt.subplots(1, 3, figsize=(12, 4.6), layout="constrained")
    axes[0].plot([p / 1000 for p in profile["pressure_pa"]], heights, color="#276888")
    axes[0].set(
        xlabel="Pressió (kPa)",
        ylabel="Altura geomètrica (km)",
        title="Perfil de pressió",
    )
    axes[1].plot(profile["temperature_k"], heights, color="#b45b2a")
    axes[1].set(
        xlabel="Temperatura (K)",
        ylabel="Altura geomètrica (km)",
        title="Perfil de temperatura",
    )
    convergence = data["profileConvergence"]
    steps = [p["verticalStepM"] for p in convergence]
    errors = [p["maxRelativePressureInterpolationError"] for p in convergence]
    axes[2].loglog(steps, errors, "o-", color="#387544")
    axes[2].set(
        xlabel="Pas vertical (m)",
        ylabel="Error relatiu màxim de pressió",
        title="Interpolació vs model analític",
    )
    axes[2].set_xticks(steps, [str(s) for s in steps])
    axes[2].invert_xaxis()
    for axis in axes:
        axis.grid(alpha=0.22)
    fig.suptitle(
        "Camp estàndard sec · COESA 1975, NASA TR R-459 · diagnòstic 7.8", fontsize=13
    )
    fig.text(
        0.5,
        -0.025,
        "Perfils tabulats de 0–10 km; 2.003 altures de contrast. No és radiància ni atmosfera observada.",
        ha="center",
        fontsize=9,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(args.output, dpi=160, bbox_inches="tight")
    plt.close(fig)


if __name__ == "__main__":
    main()
