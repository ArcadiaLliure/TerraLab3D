"""Figures científiques de resultats mesurats; cap punt ni temps sintetitzat."""

from __future__ import annotations

import argparse
import csv
import gzip
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


def run(root: Path):
    timing = json.loads(
        (root / "resultats-b0-b1-b2-b4.json").read_text(encoding="utf-8")
    )
    modes = ["B0", "B1", "B2", "B4"]
    stages = [
        "geometry",
        "atmospheric_sampling",
        "transmissions",
        "quadrature",
        "spectral_integration",
    ]
    labels = [
        "Geometria",
        "Mostreig atmosfèric",
        "Transmissions i fases",
        "Quadratura",
        "Integració espectral",
    ]
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.7), layout="constrained")
    base = np.zeros(4)
    for stage, label in zip(stages, labels):
        values = np.array(
            [
                np.mean(
                    [
                        r["profiling"]["exclusiveMs"][stage]
                        for r in timing["runs"]
                        if r["mode"] == mode
                    ]
                )
                / 1000
                for mode in modes
            ]
        )
        axes[0].bar(modes, values, bottom=base, label=label)
        base += values
    wall = np.array(
        [
            np.mean([r["wallMs"] for r in timing["runs"] if r["mode"] == mode]) / 1000
            for mode in modes
        ]
    )
    axes[0].bar(
        modes, wall - base, bottom=base, label="Resta i instrumentació", color="0.7"
    )
    axes[0].set(
        ylabel="Segons per 900 LOS (mitjana)", title="Cost exclusiu de cada etapa"
    )
    axes[0].legend(fontsize=8)
    for i, mode in enumerate(modes):
        runs = [r["wallMs"] / 1000 for r in timing["runs"] if r["mode"] == mode]
        axes[1].scatter(np.full(len(runs), i), runs, alpha=0.65, s=18)
        axes[1].plot(
            [i - 0.15, i + 0.15], [np.median(runs)] * 2, color="black", linewidth=2
        )
    axes[1].set(
        xticks=range(4),
        xticklabels=modes,
        ylabel="Segons per 900 LOS",
        title="Passades mesurades i mediana",
    )
    fig.suptitle("B0/B1/B2/B4 directes · mateixa posició de 100 fonts · AD OFF")
    fig.savefig(root / "cost-etapes-i-latencia.png", dpi=170)
    plt.close(fig)

    rows = {}
    with gzip.open(
        root / "casos-pressupost-espectral.csv.gz", "rt", encoding="utf-8"
    ) as stream:
        for r in csv.DictReader(stream):
            family = r["operator"].split("-T")[0]
            values = rows.setdefault(family, [[], [], []])
            for key, target in zip(
                ("error_mag", "lut_error_mag", "simpson_error_mag"), values
            ):
                target.append(float(r[key]))
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.5), layout="constrained")
    x = np.arange(len(rows))
    for i, label in enumerate(
        ("Total vs original", "LUT vs original", "Simpson vs LUT")
    ):
        values = [max(v[i]) for v in rows.values()]
        axes[0].bar(
            x + (i - 1) * 0.24, np.maximum(values, 1e-16), width=0.24, label=label
        )
    axes[0].axhline(0.01, color="crimson", linestyle="--", label="Pressupost 0,01 mag")
    axes[0].set(
        yscale="log",
        xticks=x,
        xticklabels=list(rows),
        ylabel="Error màxim (mag equivalents)",
        title="Pressupost congelat, màxim de cada família",
    )
    axes[0].tick_params(axis="x", labelsize=8)
    axes[0].legend(fontsize=8)
    gas = rows["combined"]
    for i, label in enumerate(("Total", "LUT", "Simpson")):
        axes[1].hist(
            np.log10(np.maximum(gas[i], 1e-16)), bins=45, histtype="step", label=label
        )
    axes[1].set(
        xlabel="log10(error en mag); zeros a −16",
        ylabel="Casos",
        title="Distribució: gasos + Rayleigh + aerosol",
    )
    axes[1].legend(fontsize=8)
    fig.savefig(root / "pressupost-espectral.png", dpi=170)
    plt.close(fig)

    diag = json.loads(
        (root / "diagnostics-transport-i-sostre.json").read_text(encoding="utf-8")
    )
    fig, axes = plt.subplots(1, 3, figsize=(14, 4.5), layout="constrained")
    for ax, mode, title in zip(
        axes,
        ("B1_homogeneous_extension", "B1_standard", "B4_standard"),
        (
            "B1 homogeni estès (prescrit)",
            "B1 COESA + aerosol H=1,2 km",
            "B4 COESA + aerosol + O3 prescrit",
        ),
    ):
        for elevation in (0.5, 5.0, 30.0, 90.0):
            cases = [
                r
                for r in diag["ceilingCases"]
                if r["mode"] == mode and r["elevationDeg"] == elevation
            ]
            ax.plot(
                [r["topM"] / 1000 for r in cases],
                [100 * r["fractionOf50km"] for r in cases],
                marker="o",
                label=f"{elevation:g}°",
            )
        ax.set(
            title=title, xlabel="Sostre (km)", ylabel="Radiància respecte de 50 km (%)"
        )
        ax.grid(alpha=0.25)
        ax.legend(fontsize=8)
    fig.suptitle(
        "Sensibilitat al sostre · la contribució superior a 50 km continua desconeguda"
    )
    fig.savefig(root / "sensibilitat-sostre-atmosferic.png", dpi=170)
    plt.close(fig)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", required=True, type=Path)
    run(parser.parse_args().root)
