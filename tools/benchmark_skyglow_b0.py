"""Campanya B0 geomètrica: protocol congelat, warm-up i JSON/CSV per passada."""

from __future__ import annotations

import argparse
import csv
import ctypes
import hashlib
import io
import json
import math
import os
import platform
import subprocess
import sys
import sysconfig
import time
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from terralab3d.domain.light_pollution.gauss_kronrod import QuadratureSettings
from terralab3d.domain.light_pollution.geometric_transport import (
    GeometricPartition,
    ViewDirection,
)
from terralab3d.domain.light_pollution.propagation_kernel import (
    DirectionSet,
    MODEL_VERSION,
    PropagationKernel,
    PropagationOptions,
    PropagationRequest,
)
from terralab3d.domain.light_pollution.source_model import (
    AngularEmissionProfile,
    DefinedSpectrum,
    EmissionAmplitude,
    GeodeticPosition,
    RectangularAreaGeometry,
    SourceModel,
)

ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = ROOT / "docs/evidencies/pas7.7/protocol-b0-v1.json"


def memory_snapshot() -> tuple[int | None, int | None, int | None]:
    """RSS actual, peak RSS de procés i RAM física; cap valor simulat."""
    if sys.platform == "win32":
        from ctypes import wintypes

        class Counters(ctypes.Structure):
            _fields_ = [("cb", wintypes.DWORD), ("PageFaultCount", wintypes.DWORD)] + [
                (name, ctypes.c_size_t)
                for name in (
                    "PeakWorkingSetSize",
                    "WorkingSetSize",
                    "QuotaPeakPagedPoolUsage",
                    "QuotaPagedPoolUsage",
                    "QuotaPeakNonPagedPoolUsage",
                    "QuotaNonPagedPoolUsage",
                    "PagefileUsage",
                    "PeakPagefileUsage",
                )
            ]

        class Status(ctypes.Structure):
            _fields_ = [
                ("dwLength", wintypes.DWORD),
                ("dwMemoryLoad", wintypes.DWORD),
            ] + [
                (name, ctypes.c_ulonglong)
                for name in (
                    "ullTotalPhys",
                    "ullAvailPhys",
                    "ullTotalPageFile",
                    "ullAvailPageFile",
                    "ullTotalVirtual",
                    "ullAvailVirtual",
                    "ullAvailExtendedVirtual",
                )
            ]

        counters = Counters()
        counters.cb = ctypes.sizeof(counters)
        status = Status()
        status.dwLength = ctypes.sizeof(status)
        psapi = ctypes.WinDLL("psapi", use_last_error=True)
        psapi.GetProcessMemoryInfo.argtypes = (
            ctypes.c_void_p,
            ctypes.POINTER(Counters),
            wintypes.DWORD,
        )
        psapi.GetProcessMemoryInfo.restype = wintypes.BOOL
        kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel.GlobalMemoryStatusEx.argtypes = (ctypes.POINTER(Status),)
        kernel.GlobalMemoryStatusEx.restype = wintypes.BOOL
        ok = psapi.GetProcessMemoryInfo(
            ctypes.c_void_p(-1), ctypes.byref(counters), counters.cb
        )
        ram_ok = kernel.GlobalMemoryStatusEx(ctypes.byref(status))
        return (
            int(counters.WorkingSetSize) if ok else None,
            int(counters.PeakWorkingSetSize) if ok else None,
            int(status.ullTotalPhys) if ram_ok else None,
        )
    if sys.platform.startswith("linux"):
        import resource

        pages = int(Path("/proc/self/statm").read_text().split()[1])
        return (
            pages * os.sysconf("SC_PAGE_SIZE"),
            int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss) * 1024,
            int(os.sysconf("SC_PHYS_PAGES") * os.sysconf("SC_PAGE_SIZE")),
        )
    return None, None, None


def cpu_model() -> str:
    if sys.platform == "win32":
        import winreg

        try:
            with winreg.OpenKey(
                winreg.HKEY_LOCAL_MACHINE,
                r"HARDWARE\DESCRIPTION\System\CentralProcessor\0",
            ) as key:
                return str(winreg.QueryValueEx(key, "ProcessorNameString")[0]).strip()
        except OSError:
            pass
    return platform.processor() or "not_exposed"


def fixtures(protocol: dict) -> tuple[SourceModel, ...]:
    rng = np.random.Generator(np.random.PCG64(int(protocol["seed"], 16)))
    max_count = max(protocol["sourceCounts"])
    low, high = protocol["sourceDistancesM"]
    distances = rng.uniform(float(low), float(high), max_count)
    bearings = rng.uniform(0, 2 * math.pi, max_count)
    observer = protocol["observer"]
    phi, lam = (
        math.radians(observer["latitudeDeg"]),
        math.radians(observer["longitudeDeg"]),
    )
    sources = []
    spectrum = DefinedSpectrum(
        "b0-flat-defined",
        "Fixture geomètrica, no mesura urbana",
        "CC0-1.0",
        (400.0, 700.0),
        (1.0, 1.0),
    )
    angular = AngularEmissionProfile(
        "b0-uniform",
        "Perfil definit, no avaluat radiomètricament a B0",
        (0.0, 90.0),
        (1.0, 1.0),
    )
    for i, (distance, bearing) in enumerate(zip(distances, bearings)):
        angle = float(distance) / protocol["earthRadiusM"]
        latitude = math.asin(
            math.sin(phi) * math.cos(angle)
            + math.cos(phi) * math.sin(angle) * math.cos(bearing)
        )
        longitude = lam + math.atan2(
            math.sin(bearing) * math.sin(angle) * math.cos(phi),
            math.cos(angle) - math.sin(phi) * math.sin(latitude),
        )
        pos = GeodeticPosition(
            math.degrees(latitude), (math.degrees(longitude) + 180) % 360 - 180, 0
        )
        sources.append(
            SourceModel(
                f"b0-region-{i:03d}",
                protocol["fixtureVersion"],
                "Rectangle S definit; només geometria B0",
                RectangularAreaGeometry(pos, 500, 500),
                spectrum,
                angular,
                EmissionAmplitude(
                    1,
                    "W",
                    "defined_absolute",
                    "Potència definida; no consumida per integrand unitari",
                ),
            )
        )
    return tuple(sources)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    raw = PROTOCOL.read_bytes()
    protocol = json.loads(raw)
    all_sources = fixtures(protocol)
    q = protocol["quadrature"]
    options = PropagationOptions(
        protocol["topM"],
        protocol["earthRadiusM"],
        GeometricPartition(
            protocol["geometricCellSizeM"], tuple(protocol["layerHeightsM"])
        ),
        QuadratureSettings(
            q["relativeTolerance"], q["absoluteToleranceM"], q["maxIntervals"]
        ),
    )
    obs = protocol["observer"]
    observer = GeodeticPosition(obs["latitudeDeg"], obs["longitudeDeg"], obs["heightM"])
    views = DirectionSet(
        tuple(
            ViewDirection(f"elevation-{e:g}", 0, float(e))
            for e in protocol["elevationsDeg"]
        ),
        "source_bearing",
    )
    requests = {
        n: PropagationRequest(all_sources[:n], observer, views, options)
        for n in protocol["sourceCounts"]
    }
    rng = np.random.Generator(np.random.PCG64(int(protocol["seed"], 16)))
    kernel = PropagationKernel()
    campaign_start = time.perf_counter()
    started = datetime.now(timezone.utc).isoformat()
    for warmup in range(protocol["warmupPasses"]):
        for n in rng.permutation(protocol["sourceCounts"]):
            kernel.evaluate(requests[int(n)])
        print(f"Warm-up {warmup + 1}/{protocol['warmupPasses']}", flush=True)
    rows = []
    fingerprints = {}
    representative = {}
    deviation = None
    for iteration in range(protocol["measuredPasses"]):
        for order, n0 in enumerate(rng.permutation(protocol["sourceCounts"])):
            n = int(n0)
            wall = time.perf_counter_ns()
            cpu = time.process_time_ns()
            result = kernel.evaluate(requests[n])
            cpu_ms = (time.process_time_ns() - cpu) / 1e6
            wall_ms = (time.perf_counter_ns() - wall) / 1e6
            signature = hashlib.sha256(
                json.dumps(result.to_dict(), sort_keys=True, allow_nan=False).encode()
            ).hexdigest()
            if n in fingerprints and fingerprints[n] != signature:
                raise ValueError(
                    "B0 no reprodueix resultats/comptadors amb la mateixa entrada"
                )
            fingerprints[n] = signature
            representative.setdefault(n, result)
            c = result.counters
            assert c.los_count == n * len(views.directions)
            assert (
                c.quadrature_node_count
                == 15 * c.segment_count + 30 * c.gk_subdivision_count
            )
            assert c.leaf_interval_count == c.segment_count + c.gk_subdivision_count
            for ray in result.rays:
                if abs(ray.integral - ray.path_length_m) > 64 * np.finfo(
                    float
                ).eps * max(1, ray.path_length_m):
                    raise ValueError("Fallada de contrast amb la longitud analítica")
            rss, peak, _ = memory_snapshot()
            rows.append(
                {
                    "benchmark_id": "B0",
                    "run_id": started,
                    "scenario": "FLAT_CLEAR_NEAR_GEOMETRY_ONLY",
                    "variant": "GK7_15_UNIT",
                    "source_count": n,
                    "iteration": iteration,
                    "configuration_order": order,
                    "wall_ms": wall_ms,
                    "cpu_ms": cpu_ms,
                    "los": c.los_count,
                    "segments": c.segment_count,
                    "nodes": c.quadrature_node_count,
                    "phase_evals": 0,
                    "gk_subdivisions": c.gk_subdivision_count,
                    "leaf_intervals": c.leaf_interval_count,
                    "rss_bytes": rss,
                    "peak_rss_bytes": peak,
                    "cache_hit": 0,
                    "relative_error": None,
                    "p95_delta_mag": None,
                    "length_max_abs_error_m": max(
                        abs(ray.integral - ray.path_length_m) for ray in result.rays
                    ),
                    "input_signature": result.input_signature,
                    "result_signature": signature,
                }
            )
        print(f"B0 passada {iteration + 1}/{protocol['measuredPasses']}", flush=True)
        if (
            time.perf_counter() - campaign_start > 600
            and iteration + 1 >= protocol["minimumPassesIfCampaignExceeds600s"]
        ):
            deviation = (
                "campaign_exceeded_600s;at_least_10_measured_passes_per_configuration"
            )
            break
    _, peak, ram = memory_snapshot()
    aggregates = []
    for n in protocol["sourceCounts"]:
        selected = [row for row in rows if row["source_count"] == n]
        times = np.array([row["wall_ms"] for row in selected])
        result = representative[n]
        aggregates.append(
            {
                "sourceCount": n,
                "iterations": len(selected),
                "latencyP50Ms": float(np.percentile(times, 50)),
                "latencyP95Ms": float(np.percentile(times, 95)),
                "latencyP99Ms": float(np.percentile(times, 99)),
                "losPerSecond": result.counters.los_count
                / (float(np.median(times)) / 1000),
                "counters": asdict(result.counters),
                "maxLengthAbsoluteErrorM": max(
                    row["length_max_abs_error_m"] for row in selected
                ),
                "inputSignature": result.input_signature,
                "resultSignature": fingerprints[n],
            }
        )
    git = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    source_paths = [
        ROOT / "backend/src/terralab3d/domain/light_pollution" / name
        for name in (
            "geometric_transport.py",
            "gauss_kronrod.py",
            "propagation_kernel.py",
        )
    ] + [Path(__file__).resolve()]
    artifact = {
        "schemaVersion": 1,
        "benchmarkId": "B0",
        "runId": started,
        "protocolId": protocol["protocolId"],
        "protocolSha256": hashlib.sha256(raw).hexdigest(),
        "gitCommit": git,
        "workingTreeCodeSha256": {
            str(p.relative_to(ROOT)).replace("\\", "/"): hashlib.sha256(
                p.read_bytes()
            ).hexdigest()
            for p in source_paths
        },
        "modelVersion": MODEL_VERSION,
        "datasetFixtureVersion": protocol["fixtureVersion"],
        "seed": protocol["seed"],
        "timestampUtc": started,
        "completedUtc": datetime.now(timezone.utc).isoformat(),
        "os": platform.platform(),
        "cpuModel": cpu_model(),
        "cpuCores": os.cpu_count(),
        "ramBytes": ram,
        "pythonVersion": platform.python_version(),
        "numpyVersion": np.__version__,
        "compiler": platform.python_compiler(),
        "compilerFlags": sysconfig.get_config_var("CFLAGS"),
        "compilerFlagsStatus": "reported_if_exposed_by_python_build",
        "gpuModel": None,
        "gpuStatus": "not_used_by_B0",
        "temperature": None,
        "thermalThrottling": None,
        "thermalTelemetryStatus": "not_exposed_by_this_runner",
        "warmupPasses": protocol["warmupPasses"],
        "requestedPasses": protocol["measuredPasses"],
        "protocolDeviation": deviation,
        "campaignWallSeconds": time.perf_counter() - campaign_start,
        "peakRssBytes": peak,
        "memoryMeaning": "Windows_GetProcessMemoryInfo_working_set_and_process_lifetime_peak;not_per_iteration_allocation_peak"
        if sys.platform == "win32"
        else "process_RSS_and_lifetime_peak",
        "observer": asdict(observer),
        "options": asdict(options),
        "directions": asdict(views),
        "sources": [s.to_dict() for s in all_sources],
        "primarySourceCount": protocol["primarySourceCount"],
        "aggregates": aggregates,
        "iterations": rows,
        "primaryExampleRays": [
            asdict(ray)
            for ray in representative[protocol["primarySourceCount"]].rays[:9]
        ],
        "stage": "geometry_only_not_radiance",
        "radiometricError": None,
        "runtimeRadiometricGate": "not_evaluated_step_7.12",
        "productSLOGate": "not_evaluated_step_7.22",
        "scope": "source_anchors_orient_views_only;no_area_emission_approximation;no_OpticalField_DEM_cache_LUT_AD_or_renderer",
    }
    args.output_dir.mkdir(parents=True, exist_ok=True)
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
    writer.writeheader()
    writer.writerows(rows)
    for name, content in (
        (
            "resultats-b0-v1.json",
            json.dumps(artifact, indent=2, ensure_ascii=False, allow_nan=False) + "\n",
        ),
        ("passades-b0-v1.csv", stream.getvalue()),
    ):
        temporary = args.output_dir / (name + ".tmp")
        temporary.write_text(content, encoding="utf-8")
        temporary.replace(args.output_dir / name)
    print(
        f"B0 complet: {len(rows)} passades mesurades; sortida {args.output_dir}",
        flush=True,
    )


if __name__ == "__main__":
    main()
