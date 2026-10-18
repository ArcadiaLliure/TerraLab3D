"""Valida 1/2/8 tiles, columnes SG-REF, dependències i regressió B0."""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import subprocess
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import scipy
from terralab3d.domain.light_pollution.gauss_kronrod import QuadratureSettings

from benchmark_skyglow_b0 import fixtures as b0_fixtures
from terralab3d.application.ports.atmospheric_optics import (
    OpticalFieldRequest,
    OpticalTileSpec,
)
from terralab3d.domain.light_pollution.geometric_transport import (
    GeometricPartition,
    SphericalFrame,
    ViewDirection,
    make_ray,
)
from terralab3d.domain.light_pollution.optical_field import TileBounds
from terralab3d.domain.light_pollution.propagation_kernel import (
    DirectionSet,
    PropagationKernel,
    PropagationOptions,
    PropagationRequest,
    number_density_integrand,
)
from terralab3d.domain.light_pollution.reference_optical_column import (
    reference_optical_column,
)
from terralab3d.domain.light_pollution.source_model import (
    AngularEmissionProfile,
    DefinedSpectrum,
    EmissionAmplitude,
    GeodeticPosition,
    PointSourceGeometry,
    SourceModel,
)
from terralab3d.infrastructure.adapters.atmosphere.standard_optics import (
    StandardAtmosphericOpticsProvider,
    standard_pressure_temperature,
)

ROOT = Path(__file__).resolve().parents[1]


def field_request(count: int, step: float = 100.0) -> OpticalFieldRequest:
    cuts = [-100.0] + [i * 9600 / count for i in range(1, count)] + [20000.0]
    tiles = tuple(
        OpticalTileSpec(
            f"tile-{i}", "standard-data-v1", TileBounds(a, b, -20000, 20000)
        )
        for i, (a, b) in enumerate(zip(cuts, cuts[1:]))
    )
    return OpticalFieldRequest(
        GeodeticPosition(0, 0, 0),
        datetime(2026, 10, 19, tzinfo=timezone.utc),
        tiles,
        vertical_step_m=step,
    )


def propagation_request(field) -> PropagationRequest:
    source = SourceModel(
        "defined-optical-test",
        "v1",
        "Fixture de columna, no emissió urbana",
        PointSourceGeometry(GeodeticPosition(0, 0.05, 0)),
        DefinedSpectrum("flat", "Definició", "CC0-1.0", (400.0, 700.0), (1.0, 1.0)),
        AngularEmissionProfile("uniform", "Definició", (0.0, 90.0), (1.0, 1.0)),
        EmissionAmplitude(
            1, "W", "defined_absolute", "Definició; no afecta la columna molecular"
        ),
    )
    return PropagationRequest(
        (source,),
        GeodeticPosition(0, 0, 100),
        DirectionSet((ViewDirection("east45", 90, 45),)),
        optical_field=field,
    )


def b0_regression() -> dict:
    protocol = json.loads(
        (ROOT / "docs/evidencies/pas7.7/protocol-b0-v1.json").read_text(
            encoding="utf-8"
        )
    )
    golden = json.loads(
        (ROOT / "docs/evidencies/pas7.7/resultats-b0-v1.json").read_text(
            encoding="utf-8"
        )
    )
    o = protocol["observer"]
    q = protocol["quadrature"]
    options = PropagationOptions(
        top_m=protocol["topM"],
        earth_radius_m=protocol["earthRadiusM"],
        quadrature=QuadratureSettings(
            q["relativeTolerance"], q["absoluteToleranceM"], q["maxIntervals"]
        ),
        partition=GeometricPartition(
            protocol["geometricCellSizeM"], tuple(protocol["layerHeightsM"])
        ),
    )
    req = PropagationRequest(
        b0_fixtures(protocol)[:100],
        GeodeticPosition(o["latitudeDeg"], o["longitudeDeg"], o["heightM"]),
        DirectionSet(
            tuple(
                ViewDirection(f"elevation-{e:g}", 0, float(e))
                for e in protocol["elevationsDeg"]
            ),
            "source_bearing",
        ),
        options,
    )
    current = PropagationKernel().evaluate(req)
    signature = hashlib.sha256(
        json.dumps(current.to_dict(), sort_keys=True, allow_nan=False).encode()
    ).hexdigest()
    expected = next(a for a in golden["aggregates"] if a["sourceCount"] == 100)[
        "resultSignature"
    ]
    if signature != expected:
        raise ValueError("Regressió de valors/comptadors/serialització B0")
    return {
        "expectedSignature": expected,
        "actualSignature": signature,
        "identical": True,
        "scope": "900_LOS_values_counters_and_serialization;not_new_timing_campaign",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    raw = (ROOT / "docs/evidencies/pas7.8/protocol-optical-field-v1.json").read_bytes()
    protocol = json.loads(raw)
    provider = StandardAtmosphericOpticsProvider()
    kernel = PropagationKernel()
    cases = []
    for count in protocol["fixtures"]:
        field = provider.resolve(field_request(count))
        for contrast in [False, True] if count == 2 else [False]:
            if contrast:
                tile = field.tiles[1]
                profile = replace(
                    tile.profile,
                    pressure_pa=tuple(p * 0.8 for p in tile.profile.pressure_pa),
                    revision="prescribed-lateral-contrast-v1",
                    provenance=tuple(
                        replace(
                            p,
                            model_revision="prescribed-lateral-contrast-v1",
                            interpretation=p.interpretation
                            + "; contrast lateral definit de pressió ×0,8, no model estàndard pur",
                        )
                        for p in tile.profile.provenance
                    ),
                )
                field = replace(
                    field,
                    tiles=(
                        field.tiles[0],
                        replace(tile, version="defined-contrast-v1", profile=profile),
                    ),
                )
            request = propagation_request(field)
            result = kernel.evaluate(
                request,
                number_density_integrand,
                integrand_id="number-density-column-v1",
                integral_unit="m^-2",
            )
            reference = reference_optical_column(
                field,
                make_ray(
                    SphericalFrame(request.observer),
                    request.directions.directions[0],
                    request.options.top_m,
                ),
            )
            relative = abs(result.rays[0].integral / reference.number_column_m2 - 1)
            if relative > protocol["columnDiagnosticRelativeTolerance"]:
                raise ValueError(
                    "Desajust de columna per damunt del control prospectiu"
                )
            repeated = kernel.evaluate(
                request,
                number_density_integrand,
                integrand_id="number-density-column-v1",
                integral_unit="m^-2",
            )
            if repeated != result:
                raise ValueError("Camp òptic no reproduïble")
            cases.append(
                {
                    "tiles": count,
                    "prescribedContrast": contrast,
                    "field": field.to_dict(),
                    "source": request.sources[0].to_dict(),
                    "result": result.to_dict(),
                    "reference": reference.to_dict(),
                    "relativeDifference": relative,
                }
            )
            print(
                f"{count} tiles, contrast={contrast}: diferència columna {relative:.3e}",
                flush=True,
            )
    convergence = []
    heights = np.linspace(0.37, 9999.63, 2003)
    for step in protocol["profileConvergenceStepsM"]:
        profile = provider.resolve(field_request(1, step)).tiles[0].profile
        errors = [
            abs(
                profile.values(float(h))[0] / standard_pressure_temperature(float(h))[0]
                - 1
            )
            for h in heights
        ]
        convergence.append(
            {
                "verticalStepM": step,
                "maxRelativePressureInterpolationError": max(errors),
                "sampleCount": len(heights),
            }
        )
    if not all(
        b["maxRelativePressureInterpolationError"]
        < a["maxRelativePressureInterpolationError"]
        for a, b in zip(convergence, convergence[1:])
    ):
        raise ValueError("La interpolació de pressió no convergeix amb el refinament")
    field = provider.resolve(field_request(2))
    extra = replace(
        field.tiles[0],
        tile_id="unvisited",
        bounds=TileBounds(30000, 40000, -20000, 20000),
    )
    first = replace(field, tiles=(*field.tiles, extra))
    second = replace(field, tiles=(*field.tiles, replace(extra, version="changed-v2")))
    a = kernel.evaluate(propagation_request(first), number_density_integrand)
    b = kernel.evaluate(propagation_request(second), number_density_integrand)
    if (
        a.optical_dependency_signature != b.optical_dependency_signature
        or a.input_signature == b.input_signature
    ):
        raise ValueError("Dependències no locals al trajecte real")
    report = {
        "schemaVersion": 1,
        "validationTimestampUtc": datetime.now(timezone.utc).isoformat(),
        "gitCommit": subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip(),
        "environment": {
            "python": platform.python_version(),
            "numpy": np.__version__,
            "scipy": scipy.__version__,
        },
        "protocolId": protocol["protocolId"],
        "protocolSha256": hashlib.sha256(raw).hexdigest(),
        "cases": cases,
        "profileConvergence": convergence,
        "dependencyCheck": {
            "unusedTileChangePreservesUsedDependencies": True,
            "inputSignatureChanges": True,
            "usedDependencySignature": a.optical_dependency_signature,
        },
        "analyticProfileSamples": [
            {
                "geometricHeightM": h,
                "pressurePa": standard_pressure_temperature(h)[0],
                "temperatureK": standard_pressure_temperature(h)[1],
            }
            for h in (0, 1000, 5000, 10000, 15000, 25000, 40000, 50000)
        ],
        "b0Regression": b0_regression(),
        "stage": "atmospheric_field_and_column_diagnostics;not_sky_radiance",
        "radiometricGate": "not_evaluated_step_7.12",
        "empiricalValidation": "not_evaluated;H_pending",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.output.with_name(args.output.name + ".tmp")
    temporary.write_text(
        json.dumps(report, indent=2, ensure_ascii=False, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    temporary.replace(args.output)
    print(f"Evidència de camp òptic escrita: {args.output}", flush=True)


if __name__ == "__main__":
    main()
