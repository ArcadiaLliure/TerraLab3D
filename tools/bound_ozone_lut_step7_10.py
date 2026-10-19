"""Cota de l'error LUT O3 per a T variable i dues cames de la fixture 50 km.

La diferència de dues taules bilineals λ/T assoleix el màxim als nusos
conjunts. Amb columnes no negatives, |Δτ|<=N_O3,max max|Δσ| i el mateix
límit multiplicatiu s'aplica a qualsevol integral amb pesos positius.
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import numpy as np

from diagnose_spectral_transport_step7_10 import ceiling_fixture
from terralab3d.infrastructure.adapters.atmosphere.gas_catalog import load_ozone_lut


def calculate() -> dict:
    raw, lut = load_ozone_lut(fine=True), load_ozone_lut()
    differences = np.abs(lut.matrix(np.array(raw.wavelengths_nm)) - np.array(raw.cross_sections_m2))
    cross_section_error = float(differences.max()) + 64 * np.finfo(float).eps * float(np.max(raw.cross_sections_m2))
    req = ceiling_fixture("B4_standard")
    assert req.optical_field and req.spectral and req.spectral.gas
    field = req.optical_field
    assert len(field.tiles) == 1
    profile = field.tiles[0].profile
    gas = req.spectral.gas.profiles[0]
    # Domini conservador que conté els punts S a 100 m i les àrees C de
    # Barcelona a 0 m. La part radial inicial descendent d'una àrea tangent
    # amb emissió ascendent respecte del seu centre dura com a màxim l'offset.
    maximum_anchor_height_m, maximum_area_offset_m = 100., 500.
    impact_cap = math.hypot(field.radius_m + maximum_anchor_height_m, maximum_area_offset_m)
    gas_terms, air_terms, max_gas_density = [], [], 0.
    for i, (a, b) in enumerate(zip(profile.heights_m, profile.heights_m[1:])):
        impact = min(impact_cap, field.radius_m + a)
        shell_length = math.sqrt((field.radius_m + b - impact) * (field.radius_m + b + impact)) - math.sqrt((field.radius_m + a - impact) * (field.radius_m + a + impact))
        number_density = max(profile.pressure_pa[i:i + 2]) / (1.380649e-23 * min(profile.temperature_k[i:i + 2]))
        mixing = max(gas.fraction(a), gas.fraction(b))
        gas_density = number_density * mixing
        max_gas_density = max(max_gas_density, gas_density)
        gas_terms.append(shell_length * gas_density)
        air_terms.append(shell_length * number_density)
    column = (2 * math.fsum(gas_terms) + maximum_area_offset_m * max_gas_density) * (1 + 128 * np.finfo(float).eps)
    air = (2 * math.fsum(air_terms) + maximum_area_offset_m * max(profile.pressure_pa) / (1.380649e-23 * min(profile.temperature_k))) * (1 + 128 * np.finfo(float).eps)
    return {"scope": "O3 LUT error only; prescribed COESA0–50km and supplied ozone profile; no physical cross-section uncertainty included", "maximumCrossSectionDifferenceM2": cross_section_error, "maximumTwoLegOzoneColumnM2": column, "maximumTwoLegAirColumnM2": air, "maximumLutMagnitudeErrorBound": 2.5 / math.log(10) * column * cross_section_error, "maximumInclusiveMagnitudeBudget": .01, "temperaturesK": [203, 293], "wavelengthNm": [380, 780], "geometryDomain": {"maximumSourceAnchorHeightM": maximum_anchor_height_m, "maximumAreaNodeOffsetM": maximum_area_offset_m, "observerHeightM": 100, "sourceEmission": "upward about centre normal", "observerLOS": "positive elevation", "above50km": "unbounded_not_assumed_zero"}, "proof": ["max abs difference of the two piecewise bilinear cross-section tables lies at joint lambda/T knots", "pressure<=max endpoints; temperature>=min endpoints; mixing<=max endpoints within every declared layer", "an upward radial leg has shell length <=sqrt(r_high^2-b^2)-sqrt(r_low^2-b^2), maximum at b=min(impact_cap,r_low)", "an area source may have an initial radial descending prefix of length at most its tangent-plane node offset; add a global density bound for that prefix", "two legs bounded by twice the shell sum plus the source prefix", "positive column-temperature basis implies abs(delta_tau)<=column_bound*max_delta_sigma", "positive source/scattering/response weights preserve exp(+-max_delta_tau) integral-ratio bounds"]}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    result = calculate()
    parser.parse_args().output.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(result["maximumLutMagnitudeErrorBound"])
