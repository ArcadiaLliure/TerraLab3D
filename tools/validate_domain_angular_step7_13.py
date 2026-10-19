"""Controls angulars acotats de COESA i oclusió, prospectius i sense malla extensa."""

import argparse
import json
import math
from dataclasses import asdict, replace
from datetime import datetime, timezone
from typing import Any

from angular_fixtures_step7_13 import fixture
from transport_gate_fixtures_step7_12 import ROOT
from validate_transport_gate_step7_12 import measured, reference, write
from terralab3d.domain.light_pollution.atmospheric_tail import conditional_tail_bound
from terralab3d.domain.light_pollution.geometric_transport import ViewDirection
from terralab3d.domain.light_pollution.propagation_kernel import DirectionSet
from terralab3d.domain.light_pollution.radiometric_gate import assess_transport

OUT = ROOT / "docs/evidencies/pas7.13"


def run(part):
    policy = json.loads(
        (OUT / "criteri-angular-preregistrat-v1.json").read_text(encoding="utf8")
    )
    points = (
        [(90, 0.5)]
        if part == "standard"
        else [
            (az, el)
            for az in (89, 90, 91)
            for el in (
                0.5,
                2,
                5,
                10,
                20,
                22,
                23,
                23.5,
                23.7,
                23.8,
                24,
                24.5,
                25,
                30,
                45,
                60,
                90,
            )
        ]
    )
    name = (
        "S_B4_standard_point_5km"
        if part == "standard"
        else "S_B4_chamber_mountain_point_5km"
    )
    base = fixture(name)
    path = OUT / f"control-{part}-preregistrat.json"
    if not path.exists():
        write(
            path,
            dict(
                registeredAtUtc=datetime.now(timezone.utc).isoformat(),
                points=points,
                fullInput=asdict(base),
                metrics=policy["metric"],
                purpose="COESA75km horitzó: criteri7.12 amb cua positiva"
                if part == "standard"
                else "Muntanya dins cobertura DEM existent; zeros i transició de visibilitat, sense extrapolar cobertura",
            ),
        )
    output = OUT / f"control-{part}-resultats.json"
    rows = json.loads(output.read_text(encoding="utf8")) if output.exists() else []
    for az, el in points:
        if any(r["azimuthDeg"] == az and r["elevationDeg"] == el for r in rows):
            continue
        req = replace(
            base, directions=DirectionSet((ViewDirection("angular-control", az, el),))
        )
        run_result = measured(req)
        refs = [asdict(reference(req, level)) for level in policy["referenceLevels"]]
        decision = assess_transport(
            run_result["value"],
            tuple(r["value"] for r in refs),
            tuple(r["los_error_estimate"] for r in refs),
            relative_limit=policy["metric"]["transportRelativeMaximum"],
            reference_resolution=policy["metric"]["referenceRelativeMaximum"],
        )
        row: dict[str, Any] = dict(
            azimuthDeg=az,
            elevationDeg=el,
            runtime=run_result,
            references=refs,
            transportDecision=asdict(decision),
        )
        if part == "standard":
            assert req.optical_field is not None and req.spectral is not None
            bound = conditional_tail_bound(
                req.sources[0],
                req.observer,
                req.directions.directions[0],
                75000.0,
                req.optical_field.tiles[0].profile.pressure_pa[-1],
                req.spectral,
            )
            lower = decision.reference - decision.reference_uncertainty
            row["conditionalTail"] = asdict(bound)
            row["tailMagnitudeUpper"] = (
                2.5 * math.log10(1 + bound.upper_radiance / lower)
                if lower > 0
                else None
            )
        rows.append(row)
        write(output, rows)
        print(part, az, el, decision.status, flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--part", choices=("standard", "terrain"), required=True)
    run(parser.parse_args().part)
