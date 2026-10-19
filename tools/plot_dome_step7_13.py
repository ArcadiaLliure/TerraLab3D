"""Gràfics científics del candidat; escala C compartida, cap calibratge absolut."""

import argparse
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import LogNorm

from terralab3d.domain.light_pollution.dome_profile import DomeField, DomeProfile


def decode(data):
    return DomeField(
        tuple(
            DomeProfile(
                p["azimuthDeg"],
                tuple(p["elevationSamplesDeg"]),
                tuple(p["radianceSamples"]),
                p["epsilonRadiance"],
                tuple(p["blockedIntervals"]),
            )
            for p in data["profiles"]
        ),
        data["radianceUnit"],
        data["provenance"],
        data["revision"],
        data["topM"],
        data["directOnly"],
    )


def plot(root: Path):
    cases = json.loads(
        (root / "resultats-angulars-cambra.json").read_text(encoding="utf8")
    )["cases"][:3]
    az = np.linspace(0, 360, 361)
    el = np.r_[0.5, np.arange(1.0, 91.0)]
    grids = [
        np.array(
            [[decode_profile.evaluate(float(a), float(e)) for a in az] for e in el],
            dtype=float,
        )
        for decode_profile in (decode(c["profile"]) for c in cases)
    ]
    cmin = min(float(g[g > 0].min()) for g in grids[1:])
    cmax = max(float(g.max()) for g in grids[1:])
    fig, axes = plt.subplots(1, 3, figsize=(15, 5.5), sharey=True, layout="constrained")
    titles = ["S · LED-B3 · 1 W definit", "C · realista NOAA-20", "C · kelvins 3000 K"]
    for i, (ax, grid, case) in enumerate(zip(axes, grids, cases)):
        norm = (
            LogNorm(float(grid[grid > 0].min()), float(grid.max()))
            if i == 0
            else LogNorm(cmin, cmax)
        )
        cmap = plt.get_cmap("inferno").copy()
        cmap.set_bad("#b7bdc3")
        mesh = ax.pcolormesh(
            az,
            el,
            np.ma.masked_less_equal(grid, 0),
            norm=norm,
            cmap=cmap,
            shading="auto",
            rasterized=True,
        )
        ax.set(
            xlabel="Azimut (°; nord → est)",
            title=titles[i],
            xlim=(0, 360),
            ylim=(0.5, 90),
        )
        ax.set_xticks([0, 90, 180, 270, 360])
        ax.set_yticks([0.5, 10, 30, 60, 90])
        cb = fig.colorbar(mesh, ax=ax, fraction=0.05, pad=0.025)
        cb.set_label(
            "W m⁻² sr⁻¹ · resposta CIE-V"
            if i == 0
            else "u. relatives m⁻² sr⁻¹ · resposta CIE-V"
        )
        ax.text(
            0.03,
            0.97,
            f"FAIL angular: {case['maximumAngularMagnitudeError']:.3f} mag",
            color="white",
            transform=ax.transAxes,
            va="top",
            bbox=dict(facecolor="black", alpha=0.6),
        )
    axes[0].set_ylabel("Elevació (°)")
    fig.suptitle(
        "DomeProfile candidat · PCHIP vertical / azimut lineal periòdic · 8 × 9 mostres\n"
        "Cambra homogènia finita de 75 km; no atmosfera COESA ni cel urbà validat",
        fontsize=13,
    )
    fig.supxlabel(
        "Procedència: SourceModel S / assets C de7.5.1 traslladats a font puntual a5km. C comparteix escala; cap normalització del màxim ni calibratge absolut.\n"
        "Reconstrucció diagnòstica no homologada. Gris = zero/no reconstruïble. Escala logarítmica; no SQM/TESS ni constant683.",
        fontsize=9,
    )
    fig.savefig(root / "mapa-calor-azimut-elevacio.png", dpi=150)
    plt.close(fig)

    fig, axes = plt.subplots(2, 3, figsize=(14, 7), sharex="row", layout="constrained")
    for i, case in enumerate(cases):
        for azimuth, color in [(90, "#a93900"), (270, "#006d91")]:
            points = sorted(
                [
                    r
                    for r in case["errors"]
                    if r["azimuthDeg"] == azimuth
                    and r["angularMagnitudeError"] is not None
                ],
                key=lambda r: r["elevationDeg"],
            )
            axes[0, i].plot(
                [r["elevationDeg"] for r in points],
                [r["direct"] for r in points],
                color=color,
                label=f"Directe {azimuth}°",
            )
            axes[0, i].plot(
                [r["elevationDeg"] for r in points],
                [r["reconstructed"] for r in points],
                "--",
                color=color,
                linewidth=1,
            )
            axes[1, i].plot(
                [r["elevationDeg"] for r in points],
                [r["angularMagnitudeError"] for r in points],
                color=color,
                label=f"Azimut {azimuth}°",
            )
        axes[0, i].set_yscale("log")
        axes[0, i].set_title(titles[i])
        axes[0, i].legend(fontsize=8)
        axes[1, i].axhline(
            0.01, color="black", linestyle=":", label="Límit angular0,01mag"
        )
        axes[1, i].set(
            xlabel="Elevació (°)",
            ylabel="Error reconstrucció (mag equivalents)",
            xlim=(0.5, 90),
        )
        axes[1, i].legend(fontsize=8)
        axes[0, i].set_ylabel(
            "W m⁻² sr⁻¹ ponderats" if i == 0 else "u. relatives m⁻² sr⁻¹ ponderades"
        )
    fig.suptitle(
        "Error de compressió vertical separat del transport · oracle a pas d’1°\n"
        "Línia contínua: kernel directe contrastat amb SG-REF; discontínua: PCHIP de9elevacions",
        fontsize=13,
    )
    fig.savefig(root / "error-pchip-vertical.png", dpi=150)
    plt.close(fig)

    terrain_path = root / "control-terrain-resultats.json"
    if terrain_path.exists():
        rows = json.loads(terrain_path.read_text(encoding="utf8"))
        fig, ax = plt.subplots(figsize=(9, 4.7), layout="constrained")
        for a in (89, 90, 91):
            points = sorted(
                [r for r in rows if r["azimuthDeg"] == a],
                key=lambda r: r["elevationDeg"],
            )
            ax.plot(
                [r["elevationDeg"] for r in points],
                [r["runtime"]["value"] for r in points],
                "o",
                label=f"Kernel {a}°",
                markersize=4,
            )
            ax.plot(
                [r["elevationDeg"] for r in points],
                [r["references"][-1]["value"] for r in points],
                "x",
                color="black",
                markersize=4,
            )
        ax.set(
            xlabel="Elevació (°)",
            ylabel="W m⁻² sr⁻¹ · resposta CIE-V",
            xlim=(20, 30),
            title="Oclusió de muntanya · cambra finita75km\nPunts directes / creus SG-REF; zeros exactes, cap suavitzat PCHIP",
        )
        ax.axvspan(
            23.7,
            23.8,
            facecolor="none",
            edgecolor="gray",
            hatch="////",
            label="Transició entre mostres; no interpolada",
        )
        ax.legend()
        fig.savefig(root / "oclusio-i-zero-directes.png", dpi=150)
        plt.close(fig)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path("docs/evidencies/pas7.13"))
    plot(parser.parse_args().root)
