"""Figura de cost reproduïble del postprocessament7.14, sense transport."""

import argparse
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "docs/evidencies/pas7.14/represa-v3"


def plot(output: Path) -> None:
    if output.exists():
        raise FileExistsError(
            "Cal una sortida nova per preservar les figures anteriors"
        )
    data = json.loads((EVIDENCE / "cost-projeccio-v3.json").read_text("utf8"))
    rows = data["cases"]
    figure, (left, right) = plt.subplots(1, 2, figsize=(13, 7), layout="constrained")
    left.barh(
        [r["caseId"] for r in rows],
        [r["wallSeconds"] for r in rows],
        color=["#d08624" if r["caseId"].startswith("C") else "#287bb5" for r in rows],
    )
    left.invert_yaxis()
    left.set_xlabel("Temps de paret sense profiler (s / projecció)")
    left.set_title("13 espectres retinguts; S i C sense reescalar")
    left.grid(axis="x", alpha=0.2)
    left.set_axisbelow(True)
    names = ["leggauss", "at_vacuum", "density", "vacuum_knots"]
    labels = [
        "Regles Gauss–Legendre",
        "Resposta i coordenada",
        "Densitat retinguda",
        "Nusos aire → buit",
    ]
    functions = {r["function"]: r for r in data["profiledFunctions"]}
    times = [functions[n]["cumulativeSeconds"] for n in names]
    right.barh(labels, times, color="#58916a")
    right.invert_yaxis()
    right.set_xlabel("Temps inclusiu sota cProfile (s)")
    right.set_title(
        f"Una projecció de 968 panells\n{data['profiledSeconds']:.3f} s instrumentats",
        fontsize=11,
    )
    for index, name in enumerate(names):
        right.text(
            times[index] + 0.008,
            index,
            f"{functions[name]['calls']:,} "
            + ("crida" if functions[name]["calls"] == 1 else "crides"),
            va="center",
            fontsize=9,
        )
    right.set_xlim(0, max(times) * 1.3)
    right.grid(axis="x", alpha=0.2)
    right.set_axisbelow(True)
    figure.suptitle(
        "TerraLab3D · Pas 7.14 · Diagnòstic de cost del candidat v2 intacte",
        fontsize=14,
    )
    figure.supxlabel(
        "Procedència: transport-i-projeccions v1, resposta CIE2019 en aire450ppm, projecció en buit.\n"
        "Temps instrumentat i de paret diferenciats; zero LOS noves. Cap SLO, optimització o homologació SQM/TESS.",
        fontsize=9,
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(output, dpi=160)
    plt.close(figure)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    plot(parser.parse_args().output)
