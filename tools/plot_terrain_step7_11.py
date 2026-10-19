"""Figures científiques de les evidències reals del Pas 7.11."""

import argparse
import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

from terrain_fixtures_step7_11 import request
from terralab3d.domain.light_pollution.geometric_transport import (
    SphericalFrame,
    make_ray,
)
from terralab3d.domain.light_pollution.source_model import GeodeticPosition


def run(root):
    top = json.loads((root / "topologia-i-flips.json").read_text(encoding="utf8"))
    perf = json.loads((root / "rendiment-b0-b1-b2-b4.json").read_text(encoding="utf8"))
    req = request()
    frame = SphericalFrame(GeodeticPosition(0, 0, 0))
    zero = frame.position_ecef(frame.observer)

    def local(p):
        v = frame.ecef_to_enu(tuple(a - b for a, b in zip(p, zero)))
        return v[0] / 1000, v[2]

    vertices = [v for v in req.terrain.vertices if abs(v[2]) < 1e-8]
    xy = sorted(local(v) for v in vertices)
    ray = make_ray(SphericalFrame(req.observer), req.directions.directions[0], 10000)
    source = local(frame.position_ecef(req.sources[0].geometry.position))
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.6), constrained_layout=True)
    ax = axes[0]
    ax.fill_between(*np.array(xy).T, -100, color="#a89976")
    ax.plot(*np.array(xy).T, color="#564a33", label="DEM triangular")
    ax.scatter(*source, color="#d7a01a", label="Font S", zorder=4)
    ax.scatter(0, 100, color="#165b9c", label="Observador", zorder=4)
    for s, color, style, label in (
        (2100, "#b65142", "--", "Trajecte ocult"),
        (2500, "#27845a", "-", "Trajecte visible"),
    ):
        target = local(ray.point(s))
        ax.plot(
            [source[0], target[0]],
            [source[1], target[1]],
            color=color,
            linestyle=style,
            label=label,
        )
    ax.plot([0, 0], [100, 2750], color="#165b9c", linewidth=1)
    ax.set(
        xlim=(-0.5, 6),
        ylim=(-60, 2800),
        xlabel="Est ENU (km)",
        ylabel="Amunt ENU (m)",
        title="Secció de la geometria ECEF compartida",
    )
    ax.legend(fontsize=8, loc="upper right")
    ax = axes[1]
    flip = top["flipsM"][0]
    ax.step(
        [2100, flip, 2500],
        [0, 1, 1],
        where="post",
        color="#165b9c",
        label="Visibilitat puntual",
    )
    ax.scatter([flip], [0], color="#165b9c", zorder=4, s=22)
    sweep = top["areaSweep"]
    ax.plot(
        [s["sM"] for s in sweep],
        [s["visibleFraction"] for s in sweep],
        color="#27845a",
        label="Àrea visible / àrea total",
    )
    ax.scatter(
        [s["sM"] for s in sweep[::4]],
        [s["referenceVisibleFraction"] for s in sweep[::4]],
        color="#6f4d96",
        marker="x",
        s=25,
        label="SG-REF independent",
    )
    ax.axvline(flip, color=".7", linewidth=0.8, linestyle=":")
    ax.set(
        xlabel="Distància s sobre la LOS zenital (m)",
        ylabel="Visibilitat / fracció d’àrea",
        ylim=(-0.04, 1.04),
        title="Salt binari i font parcial de 400×400 m",
    )
    ax.legend(fontsize=8, loc="upper left")
    fig.suptitle("Pas 7.11 · fixture sintètica; cap transparència del terreny")
    fig.savefig(root / "topologia-i-visibilitat.png", dpi=160)
    plt.close(fig)

    fig, axes = plt.subplots(1, 2, figsize=(12, 4.7), constrained_layout=True)
    x = np.arange(4)
    for i, (terrain, label, color) in enumerate(
        (
            ("none", "Sense DEM", "#8495a6"),
            ("flat", "DEM pla", "#4b82ab"),
            ("mountain", "Muntanya", "#b98b4c"),
        )
    ):
        values = [
            perf["summary"][f"{m}/{terrain}"]["p50Seconds"]
            for m in ("B0", "B1", "B2", "B4")
        ]
        axes[0].bar(x + (i - 1) * 0.24, values, width=0.23, color=color, label=label)
    axes[0].set(
        xticks=x,
        xticklabels=("B0", "B1", "B2", "B4"),
        ylabel="P50 (s / 90 LOS)",
        title="Font puntual · 5 mesures per configuració",
    )
    axes[0].legend(fontsize=8)
    for i, (terrain, label, color) in enumerate(
        (("none", "Sense DEM", "#8495a6"), ("mountain", "Muntanya", "#b98b4c"))
    ):
        values = [
            perf["areaSummary"][f"{m}/{terrain}"]["p50Seconds"] for m in ("B1", "B4")
        ]
        axes[1].bar(
            np.arange(2) + (i - 0.5) * 0.28,
            values,
            width=0.27,
            color=color,
            label=label,
        )
    axes[1].set(
        xticks=np.arange(2),
        xticklabels=("B1", "B4"),
        ylabel="P50 (s / 1 LOS), escala logarítmica",
        yscale="log",
        title="Àrea 400×400 m · ordre 2 · 3 mesures",
    )
    axes[1].legend(fontsize=8)
    fig.suptitle("Campanya final aïllada · no extrapolable als 900 LOS històrics")
    fig.savefig(root / "cost-oclusio.png", dpi=160)
    plt.close(fig)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    run(parser.parse_args().root)
