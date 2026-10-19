"""Figures científiques de B1 a partir del JSON mesurat."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    data = json.loads(args.input.read_text(encoding="utf-8"))
    args.output_dir.mkdir(parents=True, exist_ok=True)
    cases = data["diagnostics"]["cases"]
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.4), layout="constrained")
    phase = data["diagnostics"]["phaseRefinement"]
    axes[0].loglog(
        [r["samples"] for r in phase],
        [r["maxRelativeDifferenceAgainstDefinedAnalyticPhase"] for r in phase],
        "o-",
        color="#276888",
    )
    axes[0].set(
        xlabel="Nombre de nusos de fase",
        ylabel="Error relatiu màxim",
        title="Taula vs fase analítica definida",
    )
    labels = [
        "Rayleigh",
        "HG",
        "Taula",
        "Gradient",
        "Perfil vertical",
        "Rectangle",
        "Escala C",
    ]
    axes[1].barh(labels, [abs(c["relativeDifference"]) for c in cases], color="#387544")
    axes[1].set(
        xscale="log",
        xlabel="|runtime / SG-REF − 1|",
        title="Residuals diagnòstics, sense gate",
    )
    axes[1].invert_yaxis()
    for ax in axes:
        ax.grid(alpha=0.2)
    fig.suptitle("B1 · 550 nm · dispersió simple en medis prescrits", fontsize=13)
    fig.savefig(
        args.output_dir / "fase-i-residuals-b1.png", dpi=160, bbox_inches="tight"
    )
    plt.close(fig)
    if data["aggregates"]:
        fig, axes = plt.subplots(1, 2, figsize=(11, 4.4), layout="constrained")
        a = data["aggregates"]
        counts = [r["sourceCount"] for r in a]
        axes[0].plot(counts, [r["latencyP50Ms"] for r in a], "o-", label="p50")
        axes[0].plot(counts, [r["latencyP95Ms"] for r in a], "o-", label="p95")
        axes[0].set(
            xlabel="Fonts puntuals S (9 LOS/font)",
            ylabel="Temps per passada (ms)",
            title="Ruta directa, sense cache",
        )
        axes[0].legend()
        times = [r["wall_ms"] for r in data["iterations"] if r["source_count"] == 100]
        axes[1].hist(times, bins=min(10, len(times)), color="#276888", alpha=0.8)
        for percentile in (50, 95, 99):
            value = np.percentile(times, percentile)
            axes[1].axvline(
                value, label=f"p{percentile}: {value:.0f} ms", linestyle="--"
            )
        axes[1].set(
            xlabel="Temps de 900 LOS (ms)",
            ylabel="Passades",
            title="Sèrie principal · 100 fonts",
        )
        axes[1].legend(fontsize=8)
        for ax in axes:
            ax.grid(alpha=0.2)
        fig.suptitle(
            "B1a · HG explícit de fallback · temps observats, sense SLO", fontsize=13
        )
        fig.savefig(
            args.output_dir / "escalat-i-latencia-b1.png", dpi=160, bbox_inches="tight"
        )
        plt.close(fig)


if __name__ == "__main__":
    main()
