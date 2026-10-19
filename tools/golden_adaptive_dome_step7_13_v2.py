"""Golden ragged i periòdic generat amb SciPy, independent del candidat."""

import math
import random

from scipy.interpolate import PchipInterpolator

from transport_gate_fixtures_step7_12 import ROOT
from validate_transport_gate_step7_12 import write


def generate():
    rng = random.Random(246713)
    cases = []
    for scale in (1e-12, 1.0, 1e8):
        profiles = []
        for a in range(0, 360, 45):
            x = (
                [0.5, 2, 5, 10, 20, 30, 45, 60, 90]
                if a != 90
                else [0.5, 0.75, 1, 1.5, 2, 5, 10, 20, 30, 45, 60, 90]
            )
            b = [
                scale
                * math.exp(
                    2 * math.cos(math.radians(a)) * ((90 - e) / 89.5) ** 2 - e / 40
                )
                for e in x
            ]
            profiles.append(
                dict(
                    azimuthDeg=a,
                    elevationSamplesDeg=x,
                    radianceSamples=b,
                    epsilonRadiance=min(b) * 1e-15,
                    blockedIntervals=[],
                )
            )
        queries = []
        for a, e in [
            (rng.uniform(-720, 720), rng.uniform(0.5, 90)) for _ in range(250)
        ] + [(-0.3, 0.5), (359.7, 90), (720.3, 90)]:
            values = [
                math.exp(
                    PchipInterpolator(
                        p["elevationSamplesDeg"],
                        [
                            math.log(b + p["epsilonRadiance"])
                            for b in p["radianceSamples"]
                        ],
                    )(e)
                )
                - p["epsilonRadiance"]
                for p in profiles
            ]
            eps = min(values) * 1e-15
            x = [p["azimuthDeg"] + shift for shift in (-360, 0, 360) for p in profiles]
            y = [math.log(v + eps) for _ in range(3) for v in values]
            expected = math.exp(PchipInterpolator(x, y)(a % 360)) - eps
            queries.append(dict(azimuthDeg=a, elevationDeg=e, expected=expected))
        cases.append(
            dict(
                field=dict(
                    schemaVersion=2,
                    strategy="adaptive-pchip-log-az-el-v2",
                    interpolation="PCHIP_LOG",
                    azimuthInterpolation="PERIODIC_PCHIP_LOG",
                    profiles=profiles,
                    radianceUnit="relative",
                    provenance="Oracle SciPy ragged",
                    revision=0,
                    topM=75000.0,
                    directOnly=False,
                    blockedAzimuthIntervals=[],
                ),
                queries=queries,
            )
        )
    write(
        ROOT / "docs/evidencies/pas7.13/adaptatiu-v2/golden-python-typescript-v2.json",
        dict(
            oracle="SciPy PchipInterpolator vertical i azimutal, nusos irregulars",
            relativeMaximum=2e-12,
            cases=cases,
        ),
    )


if __name__ == "__main__":
    generate()
