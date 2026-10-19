"""Refina una cota analítica de columna; no canvia el camp transportat."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any

import numpy as np

from diagnose_transport_gate_step7_12 import lut_bound
from transport_gate_fixtures_step7_12 import POLICY, primary
from validate_transport_gate_step7_12 import write
from terralab3d.domain.light_pollution.geometric_transport import (
    SphericalFrame,
    make_ray,
)
from terralab3d.domain.light_pollution.source_model import PointSourceGeometry


def refined(req, dsigma, subshell_m=50.0) -> dict[str, Any]:
    field, config = req.optical_field, req.spectral
    assert field and config and config.gas and len(field.tiles) == 1
    profile = field.tiles[0].profile
    gas = config.gas.profiles[0]
    if len(set(profile.pressure_pa)) == len(set(profile.temperature_k)) == 1:
        frame = SphericalFrame(req.observer, field.radius_m)
        ray = make_ray(frame, req.directions.directions[0], req.options.top_m)
        geometry = req.sources[0].geometry
        center = (
            geometry.position
            if isinstance(geometry, PointSourceGeometry)
            else geometry.center
        )
        area_radius = (
            0.0
            if isinstance(geometry, PointSourceGeometry)
            else math.hypot(geometry.east_width_m, geometry.north_height_m) / 2
        )
        length = (
            2 * ray.length_m
            + math.dist(frame.position_ecef(center), ray.origin_ecef_m)
            + area_radius
        )
        column = (
            length
            * profile.pressure_pa[0]
            / (1.380649e-23 * profile.temperature_k[0])
            * max(gas.mole_fractions)
        )
        method = "triangle de distàncies, n/q constants; LOS completa fins al sostre, sense aprofitar ombres"
    else:
        heights = sorted(
            set(profile.heights_m)
            | set(gas.heights_m)
            | set(np.arange(profile.heights_m[0], profile.heights_m[-1], subshell_m))
        )
        impact_cap = math.hypot(field.radius_m + 100, 500)
        terms = []
        maximum = 0.0
        for a, b in zip(heights, heights[1:]):
            impact = min(impact_cap, field.radius_m + a)
            length = math.sqrt(
                (field.radius_m + b - impact) * (field.radius_m + b + impact)
            ) - math.sqrt((field.radius_m + a - impact) * (field.radius_m + a + impact))
            pressure = math.exp(
                float(np.interp(a, profile.heights_m, np.log(profile.pressure_pa)))
            )
            temperature = min(
                float(np.interp(h, profile.heights_m, profile.temperature_k))
                for h in (a, b)
            )
            nq = (
                pressure
                / (1.380649e-23 * temperature)
                * max(gas.fraction(a), gas.fraction(b))
            )
            maximum = max(maximum, nq)
            terms.append(length * nq)
        column = 2 * math.fsum(terms) + 500 * maximum
        method = "envolupant de capes 50m sobre el mateix logP/T/q interpolat; no és remostreig COESA ni quadratura del transport"
    column *= 1 + 128 * np.finfo(float).eps
    return dict(
        maximumTwoLegOzoneColumnM2=column,
        maximumLutMagnitudeError=2.5 / math.log(10) * column * dsigma,
        maximumCrossSectionDifferenceM2=dsigma,
        method=method,
        subshellM=subshell_m,
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    policy = json.loads(POLICY.read_text(encoding="utf-8"))
    rows = []
    for spec in policy["primaryCases"]:
        if spec["mode"] != "B4":
            continue
        req = primary(spec)
        dsigma = lut_bound(req)["maxDeltaSigmaM2"]
        row = refined(req, dsigma)
        row["case"] = spec["id"]
        row["transportMagnitudeAllowance"] = 2.5 * math.log10(
            1 / (1 - policy["metric"]["maximumInclusive"])
        )
        row["combinedNumericalMagnitudeBound"] = (
            row["maximumLutMagnitudeError"] + row["transportMagnitudeAllowance"]
        )
        row["spectralBudgetMag"] = 0.01
        rows.append(row)
        print(
            spec["id"],
            row["maximumLutMagnitudeError"],
            row["combinedNumericalMagnitudeBound"],
        )
    write(
        args.output,
        dict(
            rows=rows,
            proof="La pressió log-lineal decreix; T i q són lineals dins cada subcapa. maxP/minT*maxq limita n*q sense quadrar. La suma de longituds màximes de closques i el prefix tangent són conservadors. |delta tau|<=Nmax*max|delta sigma| implica la mateixa cota multiplicativa de qualsevol integral positiva. No s'han canviat llindars ni el camp.",
            separatedErrors="P/T interpolació, DEM, cua, física i dades experimentals no formen part d'aquesta cota",
        ),
    )
