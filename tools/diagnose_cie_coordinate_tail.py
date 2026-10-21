"""Cota exterior CIE corregida, dominada per resposta plana1; cap nova LOS."""

import json
import math
import time
from dataclasses import asdict, replace

from photometry_coordinates_step7_14_v2 import (
    OUT,
    ROOT,
    cie_standard_air,
    digest,
    write,
)
from validate_photometry_step7_14 import cases
from terralab3d.domain.light_pollution.atmospheric_tail import conditional_tail_bound
from terralab3d.domain.light_pollution.spectral_oracle import (
    DIMENSIONLESS_UNIT,
    SpectralCurve,
)


def main():
    start = time.perf_counter()
    policy_path = (
        ROOT / "docs/evidencies/pas7.12/criteri-transport-preregistrat-v1.json"
    )
    policy = json.loads(policy_path.read_text("utf8"))
    vertical = next(
        v
        for v in policy.values()
        if isinstance(v, dict) and "tailMaximumMagnitude" in v
    )
    name, request, _ = next(r for r in cases() if "COESA" in r[0])
    assert request.spectral is not None and request.optical_field is not None
    top = request.options.top_m
    assert top == vertical["tailTopM"] == 75000
    response = cie_standard_air()
    assert min(response.curve.values) >= 0 and max(response.curve.values) <= 1
    flat = SpectralCurve(
        "positive-envelope-1-for-coordinate-cie-v2",
        (request.spectral.wavelength_start_nm, request.spectral.wavelength_end_nm),
        (1.0, 1.0),
        DIMENSIONLESS_UNIT,
        "unavailable",
    )
    config = replace(request.spectral, responses=(flat,))
    tail = conditional_tail_bound(
        request.sources[0],
        request.observer,
        request.directions.directions[0],
        top,
        request.optical_field.tiles[0].profile.pressure_pa[-1],
        config,
    )
    rows = json.loads(
        (OUT / "coordenades-i-postprojeccions-v2.json").read_text("utf8")
    )["postProjections"]
    signal = next(r for r in rows if r["name"] == name)["coordinateProjection"][
        "signal"
    ]["value"]
    # Protecció pels pressupostos espectral i de transport heretats; cap retoc del llindar.
    lower = signal / (10 ** (0.01 / 2.5) * (1 + 1e-4))
    mag = 2.5 * math.log1p(tail.upper_radiance / lower) / math.log(10)
    result = dict(
        case=name,
        topM=top,
        responseEnvelope="0<=V_air(lambda_vac/n)<=1; resposta plana1 domina també la V corregida",
        tail=asdict(tail),
        coordinateCieSignal=signal,
        protectedSignalLower=lower,
        conditionalTailMagnitudeUpper=mag,
        maximumInclusiveMagnitude=vertical["tailMaximumMagnitude"],
        passCriterion=tail.upper_radiance > 0
        and mag <= vertical["tailMaximumMagnitude"],
        inheritedPolicySha256=digest(policy_path),
        newPhysicalLos=0,
        measuredCalculationWallSeconds=time.perf_counter() - start,
        scope="Mateixes hipòtesis seques hidrostàtiques de7.12; cota positiva fins a infinit, no atmosfera observacional general.",
    )
    path = OUT / "cota-exterior-cie-v2.json"
    assert not path.exists(), "Conservar la cota i versionar una repetició"
    write(path, result)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
