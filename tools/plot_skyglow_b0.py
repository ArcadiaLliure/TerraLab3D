"""Regenera la figura B0 des del JSON mesurat; requereix matplotlib opcional."""

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
    if (
        data.get("benchmarkId") != "B0"
        or data.get("stage") != "geometry_only_not_radiance"
    ):
        raise ValueError("Cal un resultat B0 geomètric mesurat")
    aggregate = data["aggregates"]
    primary = next(
        a for a in aggregate if a["sourceCount"] == data["primarySourceCount"]
    )
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.3), layout="constrained")
    for name, marker, color in (("P50", "o", "#175e99"), ("P95", "s", "#9b3b76")):
        axes[0].plot(
            [a["sourceCount"] for a in aggregate],
            [a["latency" + name + "Ms"] for a in aggregate],
            marker=marker,
            label=name,
            color=color,
        )
    axes[0].set(
        xlabel="Fonts S sintètiques (9 LOS per font)",
        ylabel="Temps per passada (ms)",
        title=f"Escalat geomètric · {aggregate[0]['iterations']} passades per mida",
    )
    axes[0].legend(frameon=False)
    axes[0].grid(alpha=0.2)
    times = [
        a["wall_ms"]
        for a in data["iterations"]
        if a["source_count"] == data["primarySourceCount"]
    ]
    axes[1].hist(times, bins=10, color="#175e99", alpha=0.8)
    for name, color in (("P50", "#237f64"), ("P95", "#9b3b76"), ("P99", "#c06b1c")):
        value = primary["latency" + name + "Ms"]
        axes[1].axvline(value, color=color, label=f"{name}: {value:.1f} ms")
    axes[1].set(
        xlabel="Temps per passada (ms)",
        ylabel="Passades",
        title=f"Sèrie principal · {primary['sourceCount']} fonts, {primary['counters']['los_count']} LOS",
    )
    axes[1].legend(frameon=False, fontsize=9)
    axes[1].grid(alpha=0.2)
    fig.suptitle(
        "B0 · integrand unitari, geometria CPU; cap gate radiomètric", fontsize=14
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(args.output, dpi=170)
    plt.close(fig)


if __name__ == "__main__":
    main()
