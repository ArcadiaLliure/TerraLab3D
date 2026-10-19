"""Llibre d'errors i compatibilitat; no modifica el criteri del gate."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import time
from dataclasses import asdict, replace
from pathlib import Path

import numpy as np

from benchmark_skyglow_spectral import fixture
from benchmark_skyglow_b0 import memory_snapshot
from diagnose_spectral_transport_step7_10 import conditional_source
from transport_gate_fixtures_step7_12 import ROOT, primary, vertical
from validate_transport_gate_step7_12 import measured, reference, write
from terralab3d.domain.light_pollution.propagation_kernel import PropagationKernel
from terralab3d.domain.light_pollution.transport_profiling import TransportProfiler
from terralab3d.infrastructure.adapters.atmosphere.gas_catalog import load_ozone_lut


def lut_bound(req):
    """Mateixa prova conservadora7.10, recalculada per al camp ampliat."""
    raw, lut = load_ozone_lut(fine=True), load_ozone_lut()
    difference = np.abs(
        lut.matrix(np.asarray(raw.wavelengths_nm)) - np.asarray(raw.cross_sections_m2)
    )
    dsigma = float(difference.max()) + 64 * np.finfo(float).eps * float(
        np.max(raw.cross_sections_m2)
    )
    field = req.optical_field
    profile = field.tiles[0].profile
    gas = req.spectral.gas.profiles[0]
    impact_cap = math.hypot(field.radius_m + 100, 500)
    terms = []
    maximum = 0.0
    for i, (a, b) in enumerate(zip(profile.heights_m, profile.heights_m[1:])):
        impact = min(impact_cap, field.radius_m + a)
        length = math.sqrt(
            (field.radius_m + b - impact) * (field.radius_m + b + impact)
        ) - math.sqrt((field.radius_m + a - impact) * (field.radius_m + a + impact))
        n = max(profile.pressure_pa[i : i + 2]) / (
            1.380649e-23 * min(profile.temperature_k[i : i + 2])
        )
        nq = n * max(gas.fraction(a), gas.fraction(b))
        maximum = max(maximum, nq)
        terms.append(length * nq)
    column = (2 * math.fsum(terms) + 500 * maximum) * (1 + 128 * np.finfo(float).eps)
    return dict(
        upperColumnM2=column,
        maxDeltaSigmaM2=dsigma,
        magnitudeBound=2.5 / math.log(10) * column * dsigma,
        budgetMag=0.01,
        domain="COESA0–75km, q O3 prescrit, observador100m, fonts0..100m, offsets<=500m, cames ascendents + prefix tangent; cua/física separades",
    )


def errors(output):
    path = output / "llibre-errors-numerics.json"
    rows = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    refinement = dict(spectralGL=8, pathGL=16, areaGL=8, losEpsrel=1e-11)
    if "lutBound75km" not in rows:
        rows["lutBound75km"] = lut_bound(vertical("S_near5km", "B4"))
        write(path, rows)
    rows.setdefault("verticalInterpolation", [])
    for step in (5000, 2500, 1000, 500):
        if any(r["stepM"] == step for r in rows["verticalInterpolation"]):
            continue
        req = primary(
            dict(
                mode="B4",
                standard=True,
                stepM=step,
                area=False,
                distanceM=5000,
                elevationDeg=90,
                terrain="none",
            )
        )
        assert req.optical_field
        start = time.perf_counter()
        ref = reference(req, refinement)
        rows["verticalInterpolation"].append(
            dict(
                stepM=step,
                reference=asdict(ref),
                seconds=time.perf_counter() - start,
                fieldSignature=req.optical_field.signature,
            )
        )
        write(path, rows)
        print("profile", step, ref.value, flush=True)
    if "spectrum75km" not in rows:
        req = vertical("S_near5km", "B4")
        assert req.spectral and req.spectral.gas
        base = reference(req, refinement)
        fine = reference(
            replace(
                req,
                spectral=replace(
                    req.spectral,
                    gas=replace(req.spectral.gas, luts=(load_ozone_lut(fine=True),)),
                ),
            ),
            dict(spectralGL=4, pathGL=16, areaGL=8, losEpsrel=1e-11),
        )
        rows["spectrum75km"] = dict(
            coarseLut=asdict(base),
            rawData=asdict(fine),
            lutMagnitudeDifference=abs(2.5 * math.log10(base.value / fine.value)),
            rawLutStepNm=0.01,
        )
        write(path, rows)
        print(
            "raw-spectrum", rows["spectrum75km"]["lutMagnitudeDifference"], flush=True
        )


def compatibility(output):
    path = output / "compatibilitat-c-realista-k.json"
    rows = json.loads(path.read_text(encoding="utf-8")) if path.exists() else []
    for name in ("barcelona-realista.json", "barcelona-kelvin-3000.json"):
        if any(r["asset"] == name for r in rows):
            continue
        asset = ROOT / "docs/evidencies/pas7.5.1" / name
        req = primary(
            dict(
                mode="B4",
                standard=False,
                area=True,
                distanceM=5000,
                elevationDeg=90,
                terrain="mountain",
            )
        )
        source = replace(conditional_source(asset), geometry=req.sources[0].geometry)
        req = replace(req, sources=(source,))
        run = measured(req)
        ref = reference(req, dict(spectralGL=4, pathGL=8, areaGL=4, losEpsrel=1e-10))
        rows.append(
            dict(
                asset=name,
                sha256=hashlib.sha256(asset.read_bytes()).hexdigest(),
                sourceMode=source.source_mode,
                source=source.to_dict(),
                runtime=run,
                reference=asdict(ref),
                relativeResidual=run["value"] / ref.value - 1,
                observationallyValidated=False,
                note="Geometria traslladada a la fixture sintètica de muntanya; C relatiu amb escala conservada, no ciutat observada",
            )
        )
        write(path, rows)
        print("C", name, rows[-1]["relativeResidual"], flush=True)


def benchmark(output):
    path = output / "rendiment-b0-b4-actual.json"
    rows = json.loads(path.read_text(encoding="utf-8")) if path.exists() else []
    for mode in ("B0", "B1", "B2", "B4"):
        for iteration in (0, 1):
            if any(r["mode"] == mode and r["iteration"] == iteration for r in rows):
                continue
            req = fixture(100, mode)
            profile = TransportProfiler()
            start, cpu = time.perf_counter(), time.process_time()
            result = PropagationKernel().evaluate(req, profiler=profile)
            rows.append(
                dict(
                    mode=mode,
                    iteration=iteration,
                    temperatureLabel="primera passada"
                    if iteration == 0
                    else "repetició en procés",
                    wallSeconds=time.perf_counter() - start,
                    cpuSeconds=time.process_time() - cpu,
                    memory=memory_snapshot(),
                    inputSignature=result.input_signature,
                    counters=asdict(result.counters),
                    profiling=profile.to_dict(),
                )
            )
            write(path, rows)
            print("benchmark", mode, iteration, rows[-1]["wallSeconds"], flush=True)
    for mode in ("B1", "B4"):
        for iteration in (0, 1):
            if any(
                r.get("fixture") == "area_mountain"
                and r["mode"] == mode
                and r["iteration"] == iteration
                for r in rows
            ):
                continue
            req = primary(
                dict(
                    mode=mode,
                    standard=False,
                    area=True,
                    distanceM=5000,
                    elevationDeg=90,
                    terrain="mountain",
                )
            )
            row = measured(req)
            row.update(
                fixture="area_mountain",
                mode=mode,
                iteration=iteration,
                memory=memory_snapshot(),
            )
            rows.append(row)
            write(path, rows)
            print("benchmark-area", mode, iteration, row["wallSeconds"], flush=True)


def diagnostics(output):
    """Sortida completa: estimadors GK/τ, dependències i treball d'àrea.

    Sostre10km aquí només redueix el cost del diagnòstic dels estimadors;
    no acredita el truncament atmosfèric. El gate físic conserva75km.
    """
    path = output / "diagnostics-complets-quadratura.json"
    rows = json.loads(path.read_text(encoding="utf-8")) if path.exists() else []
    for standard in (True, False):
        for mode in ("B1", "B4"):
            if any(r["standard"] == standard and r["mode"] == mode for r in rows):
                continue
            req = primary(
                dict(
                    mode=mode,
                    standard=standard,
                    stepM=1000,
                    area=not standard,
                    distanceM=5000,
                    elevationDeg=90,
                    terrain="none" if standard else "mountain",
                )
            )
            req = replace(req, options=replace(req.options, top_m=10000.0))
            profiler = TransportProfiler()
            result = PropagationKernel().evaluate(req, profiler=profiler)
            rows.append(
                dict(
                    standard=standard,
                    mode=mode,
                    result=result.to_dict(),
                    profiling=profiler.to_dict(),
                    scope="Estimadors i dependències; el sostre10km no queda validat físicament",
                )
            )
            write(path, rows)
            print("diagnostics", standard, mode, flush=True)


def oracle_controls(output):
    path = output / "controls-independents-quadratura.json"
    rows = json.loads(path.read_text(encoding="utf-8")) if path.exists() else []
    spec = json.loads(
        (
            ROOT / "docs/evidencies/pas7.12/criteri-transport-preregistrat-v1.json"
        ).read_text(encoding="utf-8")
    )["primaryCases"][2]
    req = primary(spec)
    fine = json.loads(
        (output / "campanya-v1" / (spec["id"] + ".json")).read_text(encoding="utf-8")
    )["references"][-1]["result"]["value"]
    controls = (
        ("area", dict(spectralGL=8, pathGL=16, areaGL=2, losEpsrel=1e-11)),
        ("path", dict(spectralGL=8, pathGL=4, areaGL=8, losEpsrel=1e-11)),
        ("spectral", dict(spectralGL=2, pathGL=16, areaGL=8, losEpsrel=1e-11)),
    )
    for name, refinement in controls:
        if any(r["control"] == name for r in rows):
            continue
        ref = reference(req, refinement)
        rows.append(
            dict(
                case=spec["id"],
                control=name,
                settings=refinement,
                reference=asdict(ref),
                fineReference=fine,
                relativeChange=ref.value / fine - 1,
                meaning="Diagnòstic d'un ordre cada vegada, mateix camp/DEM; no altera el criteri ni substitueix la incertesa conjunta preregistrada",
            )
        )
        write(path, rows)
        print("oracle-control", name, rows[-1]["relativeChange"], flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--part",
        choices=(
            "errors",
            "compatibility",
            "benchmark",
            "diagnostics",
            "oracle-controls",
        ),
        required=True,
    )
    args = parser.parse_args()
    args.output.mkdir(exist_ok=True, parents=True)
    {
        "errors": errors,
        "compatibility": compatibility,
        "benchmark": benchmark,
        "diagnostics": diagnostics,
        "oracle-controls": oracle_controls,
    }[args.part](args.output)
