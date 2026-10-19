"""B1 monocromàtic: invariants, referència revalidada i campanya JSON/CSV."""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import math
import os
import platform
import subprocess
import sysconfig
import time
from dataclasses import asdict, replace
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import scipy

from benchmark_skyglow_b0 import cpu_model, fixtures as b0_fixtures, memory_snapshot
from validate_optical_field_step7_8 import b0_regression
from terralab3d.application.ports.atmospheric_optics import (
    OpticalFieldRequest,
    OpticalTileSpec,
)
from terralab3d.domain.light_pollution.geometric_transport import (
    ViewDirection,
)
from terralab3d.domain.light_pollution.optical_field import TileBounds
from terralab3d.domain.light_pollution.propagation_kernel import (
    DirectionSet,
    PropagationKernel,
    PropagationRequest,
)
from terralab3d.domain.light_pollution.reference_single_scattering import (
    solve_reference_b1,
)
from terralab3d.domain.light_pollution.scattering import (
    AerosolReference,
    PhaseFunction,
    ScatteringBand,
    ScatteringConfiguration,
    dry_air_rayleigh,
)
from terralab3d.domain.light_pollution.source_model import (
    PointSourceGeometry,
    RectangularAreaGeometry,
    GeodeticPosition,
)
from terralab3d.infrastructure.adapters.atmosphere.standard_optics import (
    StandardAtmosphericOpticsProvider,
)

ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = ROOT / "docs/evidencies/pas7.9/protocol-b1-v1.json"


def analytic_two_lobe_phase(mu: float) -> float:
    """Oracle analític definit, sense interpolació de la taula candidata."""
    return 0.85 * (1 - 0.75**2) / (
        4 * math.pi * (1 + 0.75**2 - 1.5 * mu) ** 1.5
    ) + 0.15 * (1 - 0.3**2) / (4 * math.pi * (1 + 0.3**2 + 0.6 * mu) ** 1.5)


def phase_table(count: int) -> PhaseFunction:
    mu = -np.cos(np.linspace(0, np.pi, count))

    def hg(g):
        return (1 - g * g) / (4 * np.pi * (1 + g * g - 2 * g * mu) ** 1.5)

    values = 0.85 * hg(0.75) + 0.15 * hg(-0.3)
    return PhaseFunction(
        "tabulated",
        "Fixture analítica dos lòbuls HG 85/15; no Mie ni mesura",
        cosines=tuple(float(x) for x in mu),
        relative_values=tuple(float(x) for x in values),
    )


def base_request(
    protocol: dict, *, count=1, standard=False, tiles=1, phase=None
) -> PropagationRequest:
    previous = json.loads(
        (ROOT / "docs/evidencies/pas7.7/protocol-b0-v1.json").read_text(
            encoding="utf-8"
        )
    )
    # Fonts puntuals definides, amb les mateixes posicions deterministes de B0.
    sources = tuple(
        replace(
            s,
            source_model_id=f"b1-point-{i:03}",
            definition_reference="Font S puntual definida B1; cap àrea col·lapsada",
            geometry=PointSourceGeometry(
                s.geometry.center
                if isinstance(s.geometry, RectangularAreaGeometry)
                else s.geometry.position
            ),
        )
        for i, s in enumerate(b0_fixtures(previous)[:count])
    )
    o = previous["observer"]
    observer = GeodeticPosition(o["latitudeDeg"], o["longitudeDeg"], o["heightM"])
    cuts = [-2000000.0] + [10000.0 * i for i in range(1, tiles)] + [2000000.0]
    field = StandardAtmosphericOpticsProvider().resolve(
        OpticalFieldRequest(
            observer,
            datetime(2026, 10, 19, tzinfo=timezone.utc),
            tuple(
                OpticalTileSpec(
                    f"b1-tile-{i}", "b1-data-v1", TileBounds(a, b, -2000000, 2000000)
                )
                for i, (a, b) in enumerate(zip(cuts, cuts[1:]))
            ),
            vertical_step_m=1000,
        )
    )
    if not standard:
        field = replace(
            field,
            tiles=tuple(
                replace(
                    t,
                    profile=replace(
                        t.profile,
                        heights_m=(0.0, 10000.0),
                        pressure_pa=(101325.0, 101325.0),
                        temperature_k=(288.15, 288.15),
                        revision="b1-prescribed-homogeneous-v1",
                        provenance=tuple(
                            replace(
                                p,
                                model_revision="b1-prescribed-homogeneous-v1",
                                interpretation="P/T constants prescrites per B1; no perfil COESA",
                            )
                            for p in t.profile.provenance
                        ),
                    ),
                )
                for t in field.tiles
            ),
        )
    sigma, rphase = dry_air_rayleigh(protocol["wavelengthNm"])
    aerosol_phase = phase or PhaseFunction(
        "hg_fallback",
        "Henyey–Greenstein 1941; fallback prescrit, no aerosol mesurat",
        asymmetry=0.65,
    )
    band = ScatteringBand(
        protocol["wavelengthNm"],
        sigma,
        rphase,
        tuple(
            AerosolReference(
                t.tile_id,
                "b1-aerosol-v1",
                1e-5,
                0.9,
                aerosol_phase,
                "Aerosol prescrit B1; coeficients no observats",
            )
            for t in field.tiles
        ),
        "B1 prescrit, sense absorció gasosa ni núvols",
    )
    views = DirectionSet(
        tuple(
            ViewDirection(f"elevation-{e:g}", 0, float(e))
            for e in protocol["elevationsDeg"]
        ),
        "source_bearing",
    )
    return PropagationRequest(
        sources,
        observer,
        views,
        optical_field=field,
        scattering=ScatteringConfiguration(band),
    )


def diagnostics(protocol: dict) -> dict:
    req = base_request(protocol)
    assert req.scattering is not None and req.optical_field is not None
    req = replace(req, directions=DirectionSet((ViewDirection("zenith", 0, 90),)))
    assert req.scattering is not None and req.optical_field is not None
    cases = []
    for name in (
        "Rayleigh_only",
        "HG_fallback",
        "tabulated_two_lobe_reference",
        "prescribed_lateral_gradient",
        "standard_vertical_profile",
        "direct_rectangle",
        "relative_C_scale",
    ):
        candidate = req
        if name == "Rayleigh_only":
            band = replace(
                req.scattering.band,
                aerosols=tuple(
                    replace(a, extinction_per_m=0) for a in req.scattering.band.aerosols
                ),
            )
            candidate = replace(req, scattering=replace(req.scattering, band=band))
        if name == "tabulated_two_lobe_reference":
            band = replace(
                req.scattering.band,
                aerosols=tuple(
                    replace(a, phase=phase_table(8193))
                    for a in req.scattering.band.aerosols
                ),
            )
            candidate = replace(req, scattering=replace(req.scattering, band=band))
        if name == "prescribed_lateral_gradient":
            candidate = base_request(protocol, tiles=2)
            assert candidate.scattering is not None
            band = replace(
                candidate.scattering.band,
                aerosols=(
                    candidate.scattering.band.aerosols[0],
                    replace(
                        candidate.scattering.band.aerosols[1],
                        extinction_per_m=3e-5,
                        version="gradient-v1",
                    ),
                ),
            )
            candidate = replace(
                candidate,
                directions=req.directions,
                scattering=replace(candidate.scattering, band=band),
            )
        if name == "standard_vertical_profile":
            candidate = replace(
                base_request(protocol, standard=True), directions=req.directions
            )
        if name == "direct_rectangle":
            assert isinstance(req.sources[0].geometry, PointSourceGeometry)
            pos = req.sources[0].geometry.position
            source = replace(
                req.sources[0], geometry=RectangularAreaGeometry(pos, 500, 500, 20)
            )
            candidate = replace(
                req, sources=(source,), scattering=replace(req.scattering, area_order=4)
            )
        if name == "relative_C_scale":
            amplitude = replace(
                req.sources[0].amplitude,
                unit="relative",
                absolute_calibration_status="parametric",
                parameter_name="b1-relative-scale",
            )
            candidate = replace(
                req,
                sources=(
                    replace(
                        req.sources[0],
                        source_mode="CONDITIONAL_L3",
                        amplitude=amplitude,
                    ),
                ),
            )
        assert candidate.scattering is not None and candidate.optical_field is not None
        result = PropagationKernel().evaluate(candidate)
        refinements = []
        for tolerance, order in zip(protocol["referenceRefinements"], (8, 12, 16)):
            ref = solve_reference_b1(
                candidate.sources[0],
                candidate.observer,
                0,
                90,
                candidate.optical_field,
                candidate.scattering.band,
                candidate.options.top_m,
                relative_tolerance=tolerance,
                path_order=order,
                area_order=order,
                aerosol_phase_evaluator=analytic_two_lobe_phase
                if name == "tabulated_two_lobe_reference"
                else None,
            )
            refinements.append({"relativeTolerance": tolerance, **asdict(ref)})
        cases.append(
            {
                "name": name,
                "result": result.to_dict(),
                "referenceRefinements": refinements,
                "relativeDifference": result.rays[0].integral / refinements[-1]["value"]
                - 1,
                "acceptance": "diagnostic_only;not_PASS_FAIL",
                "phaseReference": "independent_analytic_two_lobe_fixture;residual_includes_table_approximation"
                if name == "tabulated_two_lobe_reference"
                else "same_declared_phase;independent_evaluation",
                "source": candidate.sources[0].to_dict(),
                "field": candidate.optical_field.to_dict(),
            }
        )
        print(
            f"Diagnòstic {name}: residual {cases[-1]['relativeDifference']:.3e}",
            flush=True,
        )
    phase_errors = []
    mu = np.linspace(-1, 1, 2003)
    truth = 0.85 * (1 - 0.75**2) / (
        4 * np.pi * (1 + 0.75**2 - 1.5 * mu) ** 1.5
    ) + 0.15 * (1 - 0.3**2) / (4 * np.pi * (1 + 0.3**2 + 0.6 * mu) ** 1.5)
    for count in protocol["phaseSamples"]:
        phase = phase_table(count)
        phase_errors.append(
            {
                "samples": count,
                "maxRelativeDifferenceAgainstDefinedAnalyticPhase": float(
                    max(
                        abs(np.array([phase.density(float(x)) for x in mu]) / truth - 1)
                    )
                ),
            }
        )
    return {
        "cases": cases,
        "phaseRefinement": phase_errors,
        "b0Regression": b0_regression(),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--diagnostics-only", action="store_true")
    args = parser.parse_args()
    raw = PROTOCOL.read_bytes()
    protocol = json.loads(raw)
    started = datetime.now(timezone.utc).isoformat()
    start = time.perf_counter()
    diagnostic = diagnostics(protocol)
    requests = {n: base_request(protocol, count=n) for n in protocol["sourceCounts"]}
    kernel = PropagationKernel()
    rng = np.random.Generator(np.random.PCG64(int(protocol["seed"], 16)))
    rows = []
    fingerprints = {}
    representative = {}
    deviation = None
    if not args.diagnostics_only:
        for warmup in range(protocol["warmupPasses"]):
            for n in rng.permutation(protocol["sourceCounts"]):
                kernel.evaluate(requests[int(n)])
            print(f"Warm-up {warmup + 1}/{protocol['warmupPasses']}", flush=True)
        for iteration in range(protocol["measuredPasses"]):
            for index, n0 in enumerate(rng.permutation(protocol["sourceCounts"])):
                n = int(n0)
                wall = time.perf_counter()
                cpu = time.process_time()
                result = kernel.evaluate(requests[n])
                cpu_ms = (time.process_time() - cpu) * 1000
                wall_ms = (time.perf_counter() - wall) * 1000
                signature = hashlib.sha256(
                    json.dumps(
                        result.to_dict(), sort_keys=True, allow_nan=False
                    ).encode()
                ).hexdigest()
                if n in fingerprints and fingerprints[n] != signature:
                    raise ValueError("B1 no reprodueix valors/comptadors/signatures")
                fingerprints[n] = signature
                representative.setdefault(n, result)
                rss, peak, _ = memory_snapshot()
                c = result.counters
                assert (
                    c.los_count == n * 9
                    and c.quadrature_node_count
                    == 15 * c.segment_count + 30 * c.gk_subdivision_count
                )
                rows.append(
                    {
                        "benchmark_id": "B1a",
                        "run_id": started,
                        "scenario": "PRESCRIBED_HOMOGENEOUS_SPHERICAL_GEOMETRY",
                        "variant": "HG_FALLBACK_ONE_WAVELENGTH_AD_OFF",
                        "source_count": n,
                        "iteration": iteration,
                        "configuration_order": index,
                        "wall_ms": wall_ms,
                        "cpu_ms": cpu_ms,
                        "los": c.los_count,
                        "segments": c.segment_count,
                        "nodes": c.quadrature_node_count,
                        "phase_evals": sum(
                            d.phase_evaluations for d in result.transport_diagnostics
                        ),
                        "transmission_segments": sum(
                            d.transmission_segments
                            for d in result.transport_diagnostics
                        ),
                        "transmission_nodes": sum(
                            d.transmission_nodes for d in result.transport_diagnostics
                        ),
                        "gk_subdivisions": c.gk_subdivision_count,
                        "rss_bytes": rss,
                        "peak_rss_bytes": peak,
                        "relative_error": None,
                    }
                )
            print(
                f"Passada {iteration + 1}/{protocol['measuredPasses']}: {time.perf_counter() - start:.1f} s acumulats",
                flush=True,
            )
            if (
                time.perf_counter() - start > 600
                and iteration + 1 >= protocol["minimumPassesIfCampaignExceeds600s"]
            ):
                deviation = "campaign_exceeded_600s;at_least_10_measured_passes_per_configuration"
                break
    aggregates = []
    for n in protocol["sourceCounts"] if rows else ():
        selected = [r for r in rows if r["source_count"] == n]
        times = [r["wall_ms"] for r in selected]
        result = representative[n]
        aggregates.append(
            {
                "sourceCount": n,
                "iterations": len(selected),
                "latencyP50Ms": float(np.percentile(times, 50)),
                "latencyP95Ms": float(np.percentile(times, 95)),
                "latencyP99Ms": float(np.percentile(times, 99)),
                "resultSignature": fingerprints[n],
                "inputSignature": result.input_signature,
                "counters": asdict(result.counters),
                "transportCounters": {
                    k: sum(getattr(d, k) for d in result.transport_diagnostics)
                    for k in (
                        "phase_evaluations",
                        "transmission_nodes",
                        "transmission_segments",
                    )
                },
                "spectralRadianceMin": min(r.integral for r in result.rays),
                "spectralRadianceMax": max(r.integral for r in result.rays),
            }
        )
    _, peak, ram = memory_snapshot()
    codepaths = list(
        (ROOT / "backend/src/terralab3d/domain/light_pollution").glob("*.py")
    ) + [Path(__file__).resolve()]
    primary = requests[100]
    assert primary.scattering is not None and primary.optical_field is not None
    artifact = {
        "schemaVersion": 1,
        "benchmarkId": "B1a",
        "runId": started,
        "timestampUtc": started,
        "completedUtc": datetime.now(timezone.utc).isoformat(),
        "gitCommit": subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip(),
        "workingTreeCodeSha256": {
            str(p.relative_to(ROOT)).replace("\\", "/"): hashlib.sha256(
                p.read_bytes()
            ).hexdigest()
            for p in codepaths
        },
        "protocolId": protocol["protocolId"],
        "protocolSha256": hashlib.sha256(raw).hexdigest(),
        "modelVersion": "single-scattering-monochromatic-v1",
        "datasetFixtureVersion": protocol["benchmarkFixture"],
        "seed": protocol["seed"],
        "os": platform.platform(),
        "cpuModel": cpu_model(),
        "cpuCores": os.cpu_count(),
        "ramBytes": ram,
        "pythonVersion": platform.python_version(),
        "numpyVersion": np.__version__,
        "scipyVersion": scipy.__version__,
        "compilerFlags": sysconfig.get_config_var("CFLAGS"),
        "gpuModel": None,
        "gpuStatus": "not_used",
        "temperature": None,
        "thermalThrottling": None,
        "thermalTelemetryStatus": "not_exposed",
        "peakRssBytes": peak,
        "memoryMeaning": "process_working_set_and_lifetime_peak;not_per_iteration_allocation_peak",
        "warmupPasses": 0 if args.diagnostics_only else protocol["warmupPasses"],
        "requestedMeasuredPasses": protocol["measuredPasses"],
        "protocolDeviation": deviation,
        "campaignWallSeconds": time.perf_counter() - start,
        "aggregates": aggregates,
        "iterations": rows,
        "diagnostics": diagnostic,
        "primarySources": [s.to_dict() for s in requests[100].sources],
        "field": primary.optical_field.to_dict(),
        "scattering": asdict(primary.scattering),
        "directions": asdict(requests[100].directions),
        "observer": asdict(requests[100].observer),
        "primaryExampleRays": [asdict(r) for r in representative[100].rays[:9]]
        if rows
        else [],
        "runtimeRadiometricGate": "not_evaluated_step_7.12",
        "productSLOGate": "not_evaluated_step_7.22",
        "empiricalValidation": "not_evaluated;H_pending",
        "AD": "not_implemented_step_7.20",
        "gasAbsorption": "not_computed_step_7.10",
        "terrainVisibility": "not_computed_step_7.11",
    }
    args.output_dir.mkdir(parents=True, exist_ok=True)
    contents = {
        "resultats-b1-v1.json": json.dumps(
            artifact, ensure_ascii=False, indent=2, allow_nan=False
        )
        + "\n"
    }
    if rows:
        stream = io.StringIO(newline="")
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
        contents["passades-b1-v1.csv"] = stream.getvalue()
    for name, content in contents.items():
        tmp = args.output_dir / (name + ".tmp")
        tmp.write_text(content, encoding="utf-8")
        tmp.replace(args.output_dir / name)
    print(f"Evidències B1 escrites a {args.output_dir}", flush=True)


if __name__ == "__main__":
    main()
