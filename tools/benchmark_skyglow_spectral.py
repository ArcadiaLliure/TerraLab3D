"""Pas 7.10: B0/B1/B2/B4 amb fixture comuna i telemetria exclusiva."""

from __future__ import annotations

import argparse
import json
import random
import subprocess
import time
from dataclasses import asdict, replace
from datetime import datetime, timezone
from pathlib import Path
import platform
import sysconfig
from typing import Any, cast

import numpy as np

from benchmark_skyglow_b0 import cpu_model, memory_snapshot
from benchmark_skyglow_b1 import base_request
from terralab3d.domain.light_pollution.gas_absorption import (
    GasAbsorptionModel,
    GasMixingProfile,
)
from terralab3d.domain.light_pollution.propagation_kernel import PropagationKernel
from terralab3d.domain.light_pollution.spectral_oracle import (
    DIMENSIONLESS_UNIT,
    SpectralCurve,
)
from terralab3d.domain.light_pollution.spectral_transport import (
    SpectralAerosol,
    SpectralTransportConfiguration,
)
from terralab3d.domain.light_pollution.transport_profiling import TransportProfiler
from terralab3d.infrastructure.adapters.atmosphere.gas_catalog import load_ozone_lut
from terralab3d.infrastructure.adapters.light_pollution.spectral_library import (
    load_spectral_library,
)

ROOT = Path(__file__).resolve().parents[1]


def fixture(
    count: int = 100,
    mode: str = "B4",
    *,
    standard: bool = False,
    top_m: float = 10000.0,
):
    protocol = json.loads(
        (ROOT / "docs/evidencies/pas7.9/protocol-b1-v1.json").read_text(
            encoding="utf-8"
        )
    )
    req = base_request(protocol, count=count, standard=standard)
    assert req.optical_field is not None and req.scattering is not None
    if mode == "B0":
        return replace(req, optical_field=None, scattering=None)
    if mode == "B1":
        return req
    library = load_spectral_library()
    sources = tuple(replace(s, spectrum=library.spectra["LED-B3"]) for s in req.sources)
    field = req.optical_field
    profiles = tuple(
        GasMixingProfile(
            t.tile_id,
            "O3",
            (0.0, 10000.0, 15000.0, 20000.0, 25000.0, 30000.0, 40000.0, 50000.0)
            if standard
            else (0.0, 10000.0),
            (4e-8, 4e-8, 1e-6, 5e-6, 8e-6, 7e-6, 3e-6, 5e-7)
            if standard
            else (4e-8, 4e-8),
            "Composició prescrita per fixture; no climatologia observada",
        )
        for t in field.tiles
    )
    gas = GasAbsorptionModel(
        "ozone-prescribed-v1",
        "O3 prescrit; altres absorbidors fora del domini declarat, no aire terrestre complet",
        (load_ozone_lut(),),
        profiles,
    )
    aerosols = tuple(
        SpectralAerosol(replace(a, scale_height_m=1200.0 if standard else None), 1.3)
        for a in req.scattering.band.aerosols
    )
    response = SpectralCurve(
        "CIE-V",
        library.photopic_wavelengths,
        library.photopic_values,
        DIMENSIONLESS_UNIT,
        "zero",
    )
    config = SpectralTransportConfiguration(
        aerosols,
        (response,),
        gas if mode == "B4" else None,
        "prescribed_composition" if mode == "B4" else "disabled_explicit_B2_diagnostic",
    )
    return replace(
        req,
        sources=sources,
        scattering=None,
        spectral=config,
        options=replace(req.options, top_m=top_m),
    )


def run(output: Path, count: int, measurements: int, warmups: int) -> None:
    output.mkdir(parents=True, exist_ok=True)
    requests = {mode: fixture(count, mode) for mode in ("B0", "B1", "B2", "B4")}
    kernel = PropagationKernel()
    result = {
        "protocol": "TL3D-SKY-7.10-v2",
        "timestampUtc": datetime.now(timezone.utc).isoformat(),
        "hardware": {
            "os": platform.platform(),
            "cpu": cpu_model(),
            "python": platform.python_version(),
            "numpy": np.__version__,
            "compilerFlags": sysconfig.get_config_var("CFLAGS"),
            "memory": memory_snapshot(),
        },
        "gitCommit": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
        ).strip(),
        "sourceCount": count,
        "warmups": warmups,
        "requestedMeasurements": measurements,
        "runs": [],
        "warmupRuns": [],
        "inputSignatures": {},
        "instrumentation": "exclusive nested perf_counter_ns; stage sums exclude request setup/signatures/serialization and measured timer overhead",
        "historicalB1Ms": 20193.3169,
        "historicalB1IsPaired": False,
    }
    order = list(requests)
    rng = random.Random(0x544C3344534B5947)
    start = time.perf_counter()
    for iteration in range(warmups + measurements):
        rng.shuffle(order)
        for mode in order:
            p = TransportProfiler()
            before_wall, before_cpu = time.perf_counter(), time.process_time()
            r = kernel.evaluate(requests[mode], profiler=p)
            row = {
                "mode": mode,
                "iteration": iteration - warmups,
                "wallMs": (time.perf_counter() - before_wall) * 1000,
                "cpuMs": (time.process_time() - before_cpu) * 1000,
                "counters": asdict(r.counters),
                "profiling": p.to_dict(),
                "memory": memory_snapshot(),
            }
            result["warmupRuns" if iteration < warmups else "runs"].append(row)
            result["inputSignatures"][mode] = r.input_signature
            if r.spectral_metadata:
                sets = cast(dict[str, dict[str, Any]], r.spectral_metadata["bandSets"])
                result.setdefault("bandCounts", {})[mode] = sorted(
                    {len(s["knots_nm"]) - 1 for s in sets.values()}
                )
            (output / "resultats-b0-b1-b2-b4.json").write_text(
                json.dumps(result, indent=2, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
            print(mode, iteration - warmups, round(row["wallMs"], 2), flush=True)
        if iteration >= warmups + 9 and time.perf_counter() - start > 600:
            result["protocolException"] = (
                "Més de 600 s; mínim 10 mesures/configuració, criteri congelat abans de la campanya"
            )
            break
    result["totalSeconds"] = time.perf_counter() - start
    result["summary"] = {
        mode: {
            "p50Ms": float(
                np.percentile(
                    [r["wallMs"] for r in result["runs"] if r["mode"] == mode], 50
                )
            ),
            "p95Ms": float(
                np.percentile(
                    [r["wallMs"] for r in result["runs"] if r["mode"] == mode], 95
                )
            ),
            "p99Ms": float(
                np.percentile(
                    [r["wallMs"] for r in result["runs"] if r["mode"] == mode], 99
                )
            ),
            "measurements": sum(r["mode"] == mode for r in result["runs"]),
        }
        for mode in requests
    }
    (output / "resultats-b0-b1-b2-b4.json").write_text(
        json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--count", type=int, default=100)
    parser.add_argument("--measurements", type=int, default=30)
    parser.add_argument("--warmups", type=int, default=5)
    args = parser.parse_args()
    run(args.output, args.count, args.measurements, args.warmups)
