"""Golden independent SciPy PCHIP, compartit literalment entre Python i TypeScript."""

import math

import numpy as np
from scipy.interpolate import PchipInterpolator

from transport_gate_fixtures_step7_12 import ROOT
from validate_transport_gate_step7_12 import write


def generate():
    x = [0.5, 2, 5, 10, 20, 30, 45, 60, 90]
    rows = []
    for scale in (1e-12, 1.0, 1e10):
        for values in ([9, 7, 4, 2, 1, 2, 3, 2, 1], [1, 2, 3, 4, 5, 6, 7, 8, 9]):
            b = [v * scale for v in values]
            epsilon = min(b) * 1e-15
            oracle = PchipInterpolator(
                x, np.log(np.array(b) + epsilon), extrapolate=False
            )
            queries = [
                dict(
                    elevationDeg=float(q), expected=float(math.exp(oracle(q)) - epsilon)
                )
                for q in np.linspace(0.5, 90, 101)
            ]
            rows.append(
                dict(
                    profile=dict(
                        azimuthDeg=0.0,
                        elevationSamplesDeg=x,
                        radianceSamples=b,
                        epsilonRadiance=epsilon,
                        blockedIntervals=[],
                    ),
                    queries=queries,
                )
            )
    write(
        ROOT / "docs/evidencies/pas7.13/golden-pchip-python-typescript.json",
        dict(
            oracle="SciPy PchipInterpolator, no implementació candidata",
            toleranceRelative=2e-12,
            cases=rows,
        ),
    )


if __name__ == "__main__":
    generate()
