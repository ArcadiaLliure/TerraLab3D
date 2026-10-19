"""Figures v2 a partir de dades congelades; C relativa i escales compartides."""

import json

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import LogNorm, TwoSlopeNorm

from validate_adaptive_dome_step7_13_v2 import OUT, decode, policy
from terralab3d.domain.light_pollution.dome_profile import DomeProfile


def plot():
    cases = []
    for name in policy()["fixtures"]:
        stem = name.lower().replace("_", "-")
        field = json.loads((OUT / (stem + "-camp.json")).read_text(encoding="utf8"))
        holdout = json.loads(
            (OUT / (stem + "-holdout.json")).read_text(encoding="utf8")
        )
        cases.append((field, holdout))
    az = np.unique(
        np.r_[
            np.arange(0.0, 360.01, 0.5),
            [p["azimuthDeg"] for field, _ in cases for p in field["field"]["profiles"]],
        ]
    )
    el = np.unique(
        np.r_[
            0.5,
            np.arange(0.75, 5.01, 0.25),
            np.arange(6.0, 91.0),
            [
                e
                for field, _ in cases
                for p in field["field"]["profiles"]
                for e in p["elevationSamplesDeg"]
            ],
        ]
    )
    grids = [
        np.array(
            [[decode_field.evaluate(float(a), float(e)) for a in az] for e in el],
            dtype=float,
        )
        for decode_field in (decode(field["field"]) for field, _ in cases)
    ]
    cmin = min(float(v.min()) for v in grids[1:])
    cmax = max(float(v.max()) for v in grids[1:])
    titles = ["S · LED-B3 · 1W definit", "C · realista NOAA-20", "C · kelvins3000K"]
    fig, axes = plt.subplots(1, 3, figsize=(15, 5.4), sharey=True, layout="constrained")
    for i, (ax, (case, validation), grid) in enumerate(zip(axes, cases, grids)):
        norm = (
            LogNorm(float(grid.min()), float(grid.max()))
            if i == 0
            else LogNorm(cmin, cmax)
        )
        mesh = ax.pcolormesh(
            az, el, grid, norm=norm, cmap="inferno", shading="auto", rasterized=True
        )
        worst = max(v["guardedReconstructionErrorMag"] or 0 for v in validation["rows"])
        label = "PASS" if all(v["angularPass"] for v in validation["rows"]) else "FAIL"
        ax.set(
            title=titles[i],
            xlabel="Azimut (°; nord → est)",
            xlim=(0, 360),
            ylim=(0.5, 90),
        )
        ax.set_xticks([0, 90, 180, 270, 360])
        ax.set_yticks([0.5, 10, 30, 60, 90])
        ax.text(
            0.03,
            0.97,
            f"{label} holdout: {worst:.5f}mag\n{case['azimuthProfiles']}perfils / {case['verticalKnots']}nusos\n{case['sampleCount']}LOS de construcció",
            transform=ax.transAxes,
            va="top",
            color="white",
            fontsize=9,
            bbox=dict(facecolor="black", alpha=0.6),
        )
        cb = fig.colorbar(mesh, ax=ax, fraction=0.05, pad=0.025)
        cb.set_label(
            "W m⁻² sr⁻¹ · resposta CIE-V"
            if i == 0
            else "u. relatives m⁻² sr⁻¹ · resposta CIE-V"
        )
    axes[0].set_ylabel("Elevació (°)")
    fig.suptitle(
        "DomeProfile adaptatiu v2 · PCHIP log periòdic en azimut i perfils verticals irregulars\n"
        "Cambra homogènia finita75km; observador100m, font puntual prescrita a5km",
        fontsize=13,
    )
    fig.supxlabel(
        "Procedència S/C: fixtures7.13, SPD i amplituds C de7.5.1 conservades. C comparteix límits i escala relativa, sense normalització del màxim.\n"
        "No és cel urbà observat ni mapa COESA. No calibratge absolut C, SQM/TESS o constant683.",
        fontsize=9,
    )
    fig.savefig(OUT / "mapa-calor-adaptatiu-v2.png", dpi=150)
    plt.close(fig)

    fig, axes = plt.subplots(1, 3, figsize=(14, 4.6), sharey=True, layout="constrained")
    for ax, (field, holdout), title in zip(axes, cases, titles):
        p = field["field"]["profiles"]
        ax.scatter(
            [r["azimuthDeg"] for r in holdout["rows"]],
            [r["elevationDeg"] for r in holdout["rows"]],
            s=12,
            marker="x",
            alpha=0.5,
            label="300holdout independents",
        )
        ax.scatter(
            [r["azimuthDeg"] for r in p for _ in r["elevationSamplesDeg"]],
            [e for r in p for e in r["elevationSamplesDeg"]],
            s=8,
            color="#ad4600",
            label="Nusos finals",
        )
        ax.set(
            xlabel="Azimut (°)",
            title=title,
            ylim=(0.5, 90),
            xlim=(0, 360),
            yscale="log",
        )
        ax.set_yticks(
            [0.5, 1, 2, 5, 10, 30, 90], labels=["0,5", "1", "2", "5", "10", "30", "90"]
        )
        ax.legend(fontsize=8)
    axes[0].set_ylabel("Elevació (°; escala logarítmica)")
    fig.suptitle(
        "Refinament concentrat a l’horitzó i al voltant de la font; holdout mai utilitzat per refinar"
    )
    fig.savefig(OUT / "mostres-adaptatives-i-holdout.png", dpi=150)
    plt.close(fig)

    fig, axes = plt.subplots(1, 3, figsize=(14, 4.5), sharey=True, layout="constrained")
    for ax, (_, holdout), title in zip(axes, cases, titles):
        rows = holdout["rows"]
        ax.scatter(
            [r["elevationDeg"] for r in rows],
            [r["guardedReconstructionErrorMag"] for r in rows],
            s=12,
            label="Reconstrucció vs SG-REF + incertesa",
        )
        ax.axhline(0.01, color="black", linestyle=":", label="Límit0,01mag")
        ax.set(title=title, xlabel="Elevació (°)", xlim=(0.5, 90), ylim=(0, 0.0105))
        ax.legend(fontsize=8)
    axes[0].set_ylabel("Error protegit (mag equivalents)")
    fig.suptitle(
        "Validació independent de la reconstrucció · mateixa tolerància0,01mag que v1"
    )
    fig.savefig(OUT / "errors-independents-v2.png", dpi=150)
    plt.close(fig)

    ratio = 100 * (grids[2] / grids[1] - 1)
    diagnostics = dict(
        reconstructionOnly=True,
        additionalTransportCalls=0,
        azimuthGridCount=len(az),
        elevationGridCount=len(el),
        relativeCDifferencePercent=dict(
            minimum=float(ratio.min()), maximum=float(ratio.max())
        ),
        radianceRanges=[
            dict(minimum=float(grid.min()), maximum=float(grid.max())) for grid in grids
        ],
        comparison="Mateixa escala relativa i normalització C conservada; no calibratge absolut.",
    )
    (OUT / "diagnostics-grafics-v2.json").write_text(
        json.dumps(diagnostics, ensure_ascii=False, indent=2) + "\n",
        encoding="utf8",
        newline="\n",
    )
    fig, ax = plt.subplots(figsize=(9.5, 5), layout="constrained")
    span = max(abs(float(ratio.min())), abs(float(ratio.max())))
    mesh = ax.pcolormesh(
        az,
        el,
        ratio,
        cmap="RdBu_r",
        norm=TwoSlopeNorm(0, -span, span),
        shading="auto",
        rasterized=True,
    )
    fig.colorbar(mesh, ax=ax, label="100·(I₃₀₀₀K/Irealista−1) (%)")
    ax.set(
        xlabel="Azimut (°)",
        ylabel="Elevació (°)",
        xlim=(0, 360),
        ylim=(0.5, 90),
        title="Diferència entre escenaris C a normalització conservada\nHipòtesis SPD diferents; cap calibratge absolut ni mesura urbana",
    )
    fig.savefig(OUT / "diferencia-realista-kelvins.png", dpi=150)
    plt.close(fig)
    profile_data = json.loads(
        (OUT / "perfil-coesa-congelat.json").read_text(encoding="utf8")
    )
    profile = DomeProfile(
        profile_data["azimuth_deg"],
        tuple(profile_data["elevations_deg"]),
        tuple(profile_data["radiances"]),
        profile_data["epsilon_radiance"],
    )
    rows = json.loads((OUT / "perfil-coesa-holdout.json").read_text(encoding="utf8"))[
        "rows"
    ]
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.5), layout="constrained")
    angles = np.linspace(45, 60, 301)
    axes[0].plot(
        angles,
        [profile.evaluate(float(e)) for e in angles],
        label="PCHIP de4nusos de suport",
    )
    axes[0].scatter(
        [r["elevationDeg"] for r in rows],
        [r["references"][-1]["value"] for r in rows],
        marker="x",
        color="black",
        label="SG-REF independent",
    )
    axes[0].set(
        xlabel="Elevació (°)", ylabel="W m⁻² sr⁻¹ · resposta CIE-V", xlim=(45, 60)
    )
    axes[0].legend(fontsize=8)
    axes[1].scatter(
        [r["elevationDeg"] for r in rows],
        [r["guardedReconstructionErrorMag"] for r in rows],
    )
    axes[1].axhline(0.01, color="black", linestyle=":", label="Límit0,01mag")
    axes[1].legend()
    axes[1].set(
        xlabel="Elevació (°)",
        ylabel="Error protegit (mag equivalents)",
        xlim=(45, 60),
        ylim=(
            0,
            max(0.0105, max(r["guardedReconstructionErrorMag"] for r in rows) * 1.1),
        ),
    )
    fig.suptitle(
        "Control de reconstrucció COESA0–75km · perfil P/T d’1km, azimut270,7°\nNomés domini registrat45–60°; cua>75km acotada positivament, no nul·la"
    )
    fig.savefig(OUT / "perfil-coesa-i-error.png", dpi=150)
    plt.close(fig)

    terrain = [
        r
        for r in json.loads((OUT / "controls-domini.json").read_text(encoding="utf8"))
        if r["spec"]["group"] == "terrain"
    ]
    fig, axes = plt.subplots(1, 3, figsize=(12, 4.5), sharey=True, layout="constrained")
    for ax, azimuth in zip(axes, (89.3, 90.2, 90.7)):
        group = [r for r in terrain if r["spec"]["azimuthDeg"] == azimuth]
        elevations = [r["spec"]["elevationDeg"] for r in group]
        ax.scatter(
            elevations,
            [r["runtime"]["value"] for r in group],
            s=60,
            facecolors="none",
            edgecolors="tab:blue",
            label="Kernel directe",
        )
        ax.scatter(
            elevations,
            [r["references"][-1]["value"] for r in group],
            marker="x",
            s=35,
            color="black",
            label="SG-REF independent",
        )
        ax.axhline(0, color="gray", linewidth=0.7)
        ax.set(title=f"Azimut {azimuth:g}°", xlabel="Elevació (°)", xticks=elevations)
        ax.tick_params(axis="x", rotation=35)
        ax.legend(fontsize=8)
    axes[0].set_ylabel("W m⁻² sr⁻¹ · resposta CIE-V")
    fig.suptitle(
        "Oclusió binària de muntanya prescrita · sis zeros exactes i sis LOS positives\nPunts directes independents; cap línia interpolada ni transparència"
    )
    fig.supxlabel(
        "DEM triangular ECEF compartit; cambra finita 75 km. El mostreig no determina la posició exacta del salt.",
        fontsize=9,
    )
    fig.savefig(OUT / "oclusio-directa-v2.png", dpi=150)
    plt.close(fig)


if __name__ == "__main__":
    plot()
