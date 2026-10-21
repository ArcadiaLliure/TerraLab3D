"""Regenera figures científiques des de dades arxivades, sense noves LOS."""

import json

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from photometry_fixtures_step7_14 import OUT, profiles


def read(name):
    return json.loads((OUT / name).read_text(encoding="utf8"))


def save(fig, name):
    fig.savefig(OUT / name, dpi=170)
    plt.close(fig)


def main():
    plt.rcParams.update({"font.size": 10, "axes.grid": True, "grid.alpha": 0.2})
    responses = profiles()
    labels = [
        "CIE V(λ), taula2019",
        "SQM CM500, SVO/Cinzano2005",
        "TESS-W stars1277, LICA2024",
    ]
    fig, axes = plt.subplots(3, 1, figsize=(10, 8), layout="constrained")
    for ax, response, label in zip(axes, responses, labels, strict=True):
        x, y = response.curve.wavelengths_nm, response.curve.values
        ax.plot(x, y, label=label)
        ax.axvspan(
            380, 780, color="C2", alpha=0.09, label="Font transportada: 380–780 nm"
        )
        if response.kind != "CIE":
            ax.axvspan(280, x[0], facecolor="none", edgecolor="0.6", hatch="///")
            ax.axvspan(x[-1], 1100, facecolor="none", edgecolor="0.6", hatch="///")
        ax.set(xlim=(280, 1100), ylim=(0, 1.08), ylabel="Resposta relativa")
        ax.legend(loc="upper right", fontsize=9)
    axes[-1].set_xlabel(
        "Longitud d’ona tabulada (nm); convenció aire/buit pendent de qualificació"
    )
    fig.suptitle(
        "7.14 · Respostes d’energia documentades\nRatllat: suport desconegut, mai zero físic · SQM/TESS no homologats"
    )
    save(fig, "respostes-i-suport.png")

    rows = read("transport-i-projeccions.json")
    gate = read("gate-projeccions-v1.json")
    results = [r for row in rows for r in row["results"] if r["signal"]["value"] > 0]
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.5), layout="constrained")
    errors = [r["equivalentMagnitudeError"] for r in results]
    axes[0].semilogy(range(1, len(errors) + 1), errors, "o", ms=4)
    axes[0].axhline(0.01, color="C3", ls="--", label="Pressupost espectral: 0,01 mag")
    axes[0].set(
        xlabel="Contrast de banda/LOS (36 positius; 3 zeros exactes)",
        ylabel="|Δmag| candidat / SG-REF",
        ylim=(1e-16, 0.03),
    )
    axes[0].legend(fontsize=8)
    spectral = gate["metrics"]["spectral"]
    axes[1].bar(
        ["Oracle fi", "LUT O₃", "Simpson"],
        [
            spectral["maximumErrorMag"],
            spectral["maximumLutErrorMag"],
            spectral["maximumSimpsonErrorMag"],
        ],
    )
    axes[1].set(yscale="log", ylabel="Error màxim (mag)", ylim=(1e-13, 0.03))
    axes[1].axhline(0.01, color="C3", ls="--")
    axes[1].set_title("10.624/10.624 contrasts espectrals PASS")
    fig.suptitle(
        "7.14 · Errors numèrics en finestres conegudes\nNo inclouen incertesa de resposta, calibratge, FOV o física atmosfèrica"
    )
    save(fig, "errors-projeccions.png")

    indices = [0, 160, 220]
    lookup = {r["name"]: r for r in rows}
    fig, axes = plt.subplots(1, 3, figsize=(13, 4.8), layout="constrained")
    s_values = [
        lookup[f"S_B4_chamber_point_5km-{i}"]["results"][0]["signal"]["value"] * 683
        for i in indices
    ]
    axes[0].bar(range(3), s_values)
    axes[0].set(
        xticks=range(3),
        xticklabels=[str(i) for i in indices],
        xlabel="Índex del holdout7.13",
        ylabel="Luminància modelada S (cd/m²)",
        title="CIE · font S definida (SI)",
    )
    for j, label in enumerate(["CIE V", "SQM, finestra", "TESS-W, finestra"]):
        ratios = [
            lookup[f"C_kelvins3000_chamber_point_5km-{i}"]["results"][j]["signal"][
                "value"
            ]
            / lookup[f"C_realista_chamber_point_5km-{i}"]["results"][j]["signal"][
                "value"
            ]
            for i in indices
        ]
        axes[1].plot(range(3), ratios, "o-", label=label)
    axes[1].axhline(1, color="0.4", ls=":")
    axes[1].set(
        xticks=range(3),
        xticklabels=[str(i) for i in indices],
        xlabel="Índex del holdout7.13",
        ylabel="Senyal C 3.000 K / realista",
        title="C · mateixa escala condicionada",
    )
    axes[1].legend(fontsize=8)
    coesa = lookup["S-COESA75km-52.19"]
    axes[2].bar(
        ["Kernel amb\nespectre", "Projeccions\nreutilitzades"],
        [coesa["kernelWallSeconds"], coesa["postProjectionWallSeconds"]],
    )
    axes[2].set(
        yscale="log", ylabel="Temps de paret (s)", title="COESA · una LOS registrada"
    )
    axes[2].text(
        0.5,
        0.94,
        "0 LOS noves en projectar",
        transform=axes[2].transAxes,
        ha="center",
        va="top",
        fontsize=9,
    )
    fig.suptitle(
        "7.14 · Escales S/C i cost observat\nCambra homogènia finita; COESA75 km + cota positiva condicionada · sense lectures natives ni Bortle"
    )
    save(fig, "escenaris-i-costos.png")
    print("3 figures regenerades; transport físic nou: 0")


if __name__ == "__main__":
    main()
