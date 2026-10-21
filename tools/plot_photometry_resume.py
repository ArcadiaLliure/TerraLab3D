"""Figures reproduïbles de la represa7.14, només amb dades arxivades."""

import csv
import json

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from photometry_coordinates_step7_14_v2 import OUT


def read(name):
    return json.loads((OUT / name).read_text("utf8"))


def main():
    plt.rcParams.update({"font.size": 10, "axes.grid": True, "grid.alpha": 0.2})
    data = read("coordenades-i-postprojeccions-v2.json")
    positives = [
        r for r in data["postProjections"] if r["coordinateChangeMag"] is not None
    ]
    names = [
        "S · 0",
        "S · 160",
        "S · 220",
        "C realista · 0",
        "C realista · 160",
        "C realista · 220",
        "C 3.000 K · 0",
        "C 3.000 K · 160",
        "C 3.000 K · 220",
        "S · muntanya visible",
        "S · àrea400m",
        "S · COESA52,19°",
    ]
    fig, ax = plt.subplots(figsize=(11, 5.8), layout="constrained")
    colors = ["C1" if r["name"].startswith("C_") else "C0" for r in positives]
    ax.barh(names, [r["coordinateChangeMag"] for r in positives], color=colors)
    ax.axvline(0, color="0.3", lw=0.8)
    ax.invert_yaxis()
    ax.set_xlabel("Δmag de ponderació CIE: V en aire450ppm / taula aplicada en buit")
    ax.set_title(
        "7.14 · Canvi explícit de convenció espectral\nNo és error de quadratura · la SPD retinguda original no canvia · C continua relatiu"
    )
    fig.savefig(OUT / "canvi-coordenades-cie-v2.png", dpi=170)
    plt.close(fig)

    fig, axes = plt.subplots(1, 2, figsize=(12, 4.5), layout="constrained")
    filter_support = []
    for file in sorted((OUT / "fonts-primaries/report/filters").glob("*.ecsv")):
        lines = [
            line
            for line in file.read_text("utf8").splitlines()
            if not line.startswith("#")
        ]
        rows = list(csv.DictReader(lines))
        x = [float(r["Wavelength"]) for r in rows]
        filter_support.append((min(x), max(x)))
        y = [float(r["Transmittance"]) for r in rows]
        label = file.stem.split("_", 2)[-1]
        axes[0].plot(x, y, label=label)
    axes[0].set(
        xlim=(300, 1100),
        xlabel="Longitud d’ona indicada pel laboratori (nm)",
        ylabel="Transmissió tabulada del filtre",
        title="LICA2026 · filtres de diferents lots",
    )
    axes[0].axvspan(300, max(a for a, _ in filter_support), color="0.8", alpha=0.5)
    axes[0].axvspan(min(b for _, b in filter_support), 1100, color="0.8", alpha=0.5)
    axes[0].legend(fontsize=8)
    for file in sorted((OUT / "fonts-primaries/report/tessw").glob("*.csv")):
        rows = list(csv.DictReader(file.open(encoding="utf8")))
        axes[1].plot(
            [float(r["Wavelength"]) for r in rows],
            [float(r["Mean freq"]) for r in rows],
            label=file.stem,
        )
    axes[1].set(
        xlabel="Longitud d’ona indicada pel laboratori (nm)",
        ylabel="Freqüència mitjana crua (Hz)",
        title="Mesures de fotòmetres; encara no són R(λ)",
    )
    axes[1].legend(fontsize=8)
    fig.suptitle(
        "7.14 · Dades primàries addicionals · GUAIX/LICA, commit0f55129d\nGris: fora del suport mesurat dels filtres · cap extrapolació nul·la ni calibratge nou"
    )
    fig.savefig(OUT / "dades-primaries-lots-v2.png", dpi=170)
    plt.close(fig)

    spectral = read("pressupost-espectral-v2.json")
    fig, axes = plt.subplots(1, 3, figsize=(12, 4.2), layout="constrained")
    metrics = [
        spectral["maximumErrorMag"],
        max(r["relativeError"] for r in data["fluxControls"]),
        max(r["relativeError"] for r in data["postProjections"]),
    ]
    for ax, value, limit, title, unit in zip(
        axes,
        metrics,
        [0.01, 1e-10, 1e-10],
        [
            "21.184 contrasts espectrals",
            "55 controls de flux",
            "13 projeccions / oracle",
        ],
        ["Error màxim (mag)", "Error relatiu màxim", "Error relatiu màxim"],
        strict=True,
    ):
        ax.bar(["Mesurat"], [value])
        ax.axhline(limit, color="C3", ls="--", label="Llindar preregistrat")
        ax.set(yscale="log", ylabel=unit, title=title)
        ax.legend(fontsize=8)
    fig.suptitle(
        "7.14 · Controls numèrics de la represa\nFinestres/hipòtesis de coordenada explícites; no homologació instrumental completa"
    )
    fig.savefig(OUT / "errors-i-criteris-v2.png", dpi=170)
    plt.close(fig)
    print("3 figures regenerades; transport físic addicional:0")


if __name__ == "__main__":
    main()
