"""Diagnòstics reproduïbles de 7.11; cap gate radiomètric de 7.12."""

from __future__ import annotations

import argparse
from dataclasses import asdict, replace
import hashlib
import json
import math
from pathlib import Path
import time

import numpy as np

from diagnose_spectral_transport_step7_10 import conditional_source
from terrain_fixtures_step7_11 import grid_surface, request
from terralab3d.application.terrain_visibility_builder import build_terrain_surface
from terralab3d.domain.light_pollution.geometric_transport import (
    SphericalFrame,
    make_ray,
)
from terralab3d.domain.light_pollution.propagation_kernel import PropagationKernel
from terralab3d.domain.light_pollution.reference_single_scattering import (
    solve_reference_b1,
)
from terralab3d.domain.light_pollution.reference_spectral_transport import (
    solve_reference_spectral,
)
from terralab3d.domain.light_pollution.reference_terrain import ReferenceTerrain
from terralab3d.domain.light_pollution.single_scattering import (
    SingleScatteringTransport,
)
from terralab3d.domain.light_pollution.source_model import (
    GeodeticPosition,
    PointSourceGeometry,
)
from terralab3d.domain.light_pollution.terrain_visibility import (
    TerrainVisibility,
    visible_area_nodes,
)
from terralab3d.domain.light_pollution.transport_profiling import TransportProfiler
from terralab3d.infrastructure.adapters.dem.adapter import RasterioElevationAdapter

ROOT = Path(__file__).resolve().parents[1]


def write(path, value):
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False),
        encoding="utf8",
    )


def topology(output):
    req = request()
    surface = req.terrain
    assert surface
    write(output / "fixture-muntanya.json", asdict(surface))
    ray = make_ray(SphericalFrame(req.observer), req.directions.directions[0], 10000.0)
    frame = SphericalFrame(req.observer)
    source = frame.position_ecef(req.sources[0].geometry.position)
    vis, ref = TerrainVisibility(surface, lambda: None), ReferenceTerrain(surface)
    plan = vis.plan(source, ray)
    flips = [
        s for i, s in enumerate(plan.cuts[1:-1]) if plan.mask[i] != plan.mask[i + 1]
    ]
    samples = []
    for distance in np.random.default_rng(711).uniform(0, ray.length_m, 200):
        p = ray.point(float(distance))
        samples.append(
            {
                "sM": float(distance),
                "runtime": vis.visible(source, p),
                "plan": plan.at(float(distance)),
                "reference": bool(ref.visible(np.array(source), np.array(p))),
            }
        )
    assert all(s["runtime"] == s["plan"] == s["reference"] for s in samples)
    flip_samples = [
        {
            "sM": f + delta,
            "runtime": vis.visible(source, ray.point(f + delta)),
            "reference": bool(
                ref.visible(np.array(source), np.array(ray.point(f + delta)))
            ),
        }
        for f in flips
        for delta in (-0.01, -0.0001, 0.0001, 0.01)
    ]
    curvature = []
    for spacing in (10000, 5000, 2000):
        easts = tuple(float(x) for x in range(-10000, 210001, spacing))
        terrain = grid_surface(
            easts, (-10000.0, 0.0, 10000.0), [[0.0] * len(easts)] * 3
        )
        engine, oracle = (
            TerrainVisibility(terrain, lambda: None),
            ReferenceTerrain(terrain),
        )
        a = frame.position_ecef(GeodeticPosition(0, 0, 100))
        b = frame.position_ecef(
            GeodeticPosition(0, math.degrees(200000 / frame.radius_m), 100)
        )
        high = frame.position_ecef(
            GeodeticPosition(0, math.degrees(200000 / frame.radius_m), 10000)
        )
        hits = engine.intersections(a, b)
        rhits = oracle.hits(np.array(a), np.array(b))
        curvature.append(
            {
                "spacingM": spacing,
                "triangles": len(terrain.faces),
                "lowVisible": engine.visible(a, b),
                "highVisible": engine.visible(a, high),
                "firstHitM": hits[0],
                "referenceFirstHitM": rhits[0],
                "analyticSphereFirstHitM": math.dist(a, b) / 2
                - math.sqrt(
                    frame.radius_m**2
                    - (math.hypot(*tuple((x + y) / 2 for x, y in zip(a, b)))) ** 2
                ),
            }
        )
    flip = flips[0]
    exact = {
        "sM": flip,
        "runtime": vis.visible(source, ray.point(flip)),
        "reference": bool(ref.visible(np.array(source), np.array(ray.point(flip)))),
        "meaning": "tangència opaca; no interpolada",
    }
    assert not exact["runtime"] and not exact["reference"]
    area_request = request(area=True)
    emitter = SingleScatteringTransport(
        area_request.sources[0],
        area_request.optical_field,
        area_request.scattering,
        ray,
        4096,
        lambda: None,
        set(),
    )
    center = np.mean(emitter.corners, axis=0)
    axis_u = (np.array(emitter.corners[1]) - emitter.corners[0]) / 400
    axis_v = (np.array(emitter.corners[3]) - emitter.corners[0]) / 400
    sweep = []
    for s in np.linspace(2100, 2500, 41):
        point = ray.point(float(s))
        nodes = visible_area_nodes(vis, point, emitter.corners, 160000.0, 4)
        _, weights = ref.area_nodes(
            np.array(point), center, axis_u, axis_v, 400, 400, 4
        )
        sweep.append(
            {
                "sM": float(s),
                "visibleFraction": sum(w for _, w in nodes),
                "referenceVisibleFraction": float(weights.sum()),
            }
        )
    write(
        output / "topologia-i-flips.json",
        {
            "samples": samples,
            "flipsM": flips,
            "flipSamples": flip_samples,
            "curvature": curvature,
            "criterion": "booleans; primera interseccio 1e-6 m; radiancia nomes diagnostic",
            "exactBoundary": exact,
            "areaSweep": sweep,
            "maxAreaFractionDifference": max(
                abs(s["visibleFraction"] - s["referenceVisibleFraction"]) for s in sweep
            ),
        },
    )


def transport(output, *, area_only=False):
    rows = []
    cases = (
        [
            ("B1_point_zenith", request()),
            ("B1_point_low", request(elevation=5)),
            ("B2_point_zenith", request("B2")),
            ("B4_point_zenith", request("B4")),
        ]
        if not area_only
        else []
    )
    for mode in () if area_only else ("realistic", "kelvin"):
        path = (
            ROOT
            / "docs/evidencies/pas7.5.1"
            / (
                "barcelona-realista.json"
                if mode == "realistic"
                else "barcelona-kelvin-3000.json"
            )
        )
        original = conditional_source(path)
        base = request("B4", area=True)
        # Conserva SPD/amplitud/semàntica C de l'evidència, trasllada només
        # geometria a la muntanya sintètica. No és una mesura urbana nova.
        source = replace(original, geometry=base.sources[0].geometry)
        cases.append(
            (f"B4_C_{mode}_relocated_synthetic", replace(base, sources=(source,)))
        )
        write(
            output / f"input-c-{mode}.json",
            {
                "originalSha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                "transformation": "geometry replaced by synthetic400x400m at5km,height10m; SPD/amplitude/sourceMode unchanged",
                "source": source.to_dict(),
            },
        )
    if area_only:
        cases = [("B1_area", request(area=True))]
    for label, req in cases:
        assert req.optical_field
        runtime_rows, reference_rows = [], []
        orders = (2, 4, 8) if "area" in label else (2,)
        for order in orders:
            case = req
            if req.scattering:
                case = replace(
                    req, scattering=replace(req.scattering, area_order=order)
                )
            elif req.spectral:
                case = replace(
                    req,
                    spectral=replace(
                        req.spectral,
                        reference_configuration=replace(
                            req.spectral.monochromatic(), area_order=order
                        ),
                    ),
                )
            profiler = TransportProfiler()
            start = time.perf_counter()
            value = PropagationKernel().evaluate(case, profiler=profiler)
            runtime_rows.append(
                {
                    "areaOrder": order,
                    "value": value.rays[0].integral,
                    "seconds": time.perf_counter() - start,
                    "estimatedOuterError": value.rays[0].estimated_error,
                    "counters": asdict(value.counters),
                    "terrain": value.terrain_metadata,
                    "profile": profiler.to_dict(),
                    "signature": value.input_signature,
                }
            )
            print(label, "runtime", order, runtime_rows[-1]["seconds"], flush=True)
        for order in (
            orders if len(orders) > 1 else (2, 4) if "_C_" in label else (4, 8)
        ):
            start = time.perf_counter()
            if req.scattering:
                ref = solve_reference_b1(
                    req.sources[0],
                    req.observer,
                    90,
                    req.directions.directions[0].elevation_deg,
                    req.optical_field,
                    req.scattering.band,
                    10000.0,
                    terrain=req.terrain,
                    area_order=order,
                    path_order=16,
                    relative_tolerance=2e-8,
                )
            else:
                ref = solve_reference_spectral(
                    req.sources[0],
                    req.observer,
                    req.optical_field,
                    req.spectral,
                    90,
                    90,
                    10000.0,
                    terrain=req.terrain,
                    area_order=order,
                    spectral_order=4 if order < 8 else 8,
                    relative_tolerance=2e-8,
                )
            reference_rows.append(
                {**asdict(ref), "seconds": time.perf_counter() - start}
            )
            print(label, "reference", order, reference_rows[-1]["seconds"], flush=True)
        rows.append(
            {
                "case": label,
                "unit": value.integral_unit,
                "runtime": runtime_rows,
                "reference": reference_rows,
                "absoluteResidual": runtime_rows[-1]["value"]
                - reference_rows[-1]["value"],
                "relativeResidual": runtime_rows[-1]["value"]
                / reference_rows[-1]["value"]
                - 1
                if reference_rows[-1]["value"]
                else None,
                "referenceRefinementRelative": reference_rows[-1]["value"]
                / reference_rows[-2]["value"]
                - 1
                if len(reference_rows) > 1 and reference_rows[-2]["value"]
                else None,
                "gate": "diagnostic_only;not7.12",
            }
        )
        write(
            output
            / ("diagnostic-area.json" if area_only else "diagnostic-transport.json"),
            rows,
        )


def real_dem(output):
    dem = RasterioElevationAdapter()
    try:
        center = GeodeticPosition(41.3875, 2.1666667, 0)
        lat = tuple(center.latitude_deg + d for d in (-0.01, 0, 0.01))
        lon = tuple(center.longitude_deg + d for d in (-0.01, 0, 0.01))
        metadata = dem.metadata()
        # Hipòtesi explícita del model esfèric, no conversió a l'el·lipsoide.
        start = time.perf_counter()
        surface = build_terrain_surface(
            dem,
            lat,
            lon,
            SphericalFrame(center),
            upper_envelope_m=3000.0,
            height_interpretation="Altura numèrica DEM assignada a altura radial esfèrica; datum vertical/geoid no verificat; només diagnòstic",
            height_to_radial=lambda h: h,
        )
        elapsed = time.perf_counter() - start
        write(output / "dem-real-snapshot.json", asdict(surface))
        highest = max(math.hypot(*v) - surface.radius_m for v in surface.vertices)
        req = request()
        obs = replace(center, altitude_m=highest + 100)
        source = replace(
            req.sources[0],
            geometry=PointSourceGeometry(
                replace(
                    center,
                    longitude_deg=center.longitude_deg + 0.005,
                    altitude_m=highest + 10,
                )
            ),
        )
        req = replace(
            req,
            observer=obs,
            sources=(source,),
            optical_field=replace(req.optical_field, origin=obs),
            terrain=surface,
        )
        result = PropagationKernel().evaluate(req)
        write(
            output / "dem-real-resultat.json",
            {
                "metadata": {
                    "sourceId": metadata.source_id,
                    "fingerprint": metadata.fingerprint,
                    "resolutionM": metadata.resolution_m,
                    "sourceCount": len(metadata.source_ids),
                    "nativeCrs": metadata.native_crs,
                },
                "gridLatitudes": lat,
                "gridLongitudes": lon,
                "builderSeconds": elapsed,
                "surfaceSignature": surface.signature,
                "sampledHeightsM": [
                    math.hypot(*v) - surface.radius_m for v in surface.vertices
                ],
                "result": result.to_dict(),
                "limitation": "Diagnòstic de nou nusos; datum vertical no certificat; no es redistribueix el raster DEM",
            },
        )
    finally:
        dem.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--part", choices=("topology", "transport", "area", "dem"), required=True
    )
    args = parser.parse_args()
    args.output.mkdir(exist_ok=True, parents=True)
    {
        "topology": topology,
        "transport": transport,
        "area": lambda out: transport(out, area_only=True),
        "dem": real_dem,
    }[args.part](args.output)
