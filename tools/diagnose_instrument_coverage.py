"""Acota regions no mesurades del filtre dins la taula del chip; no inventa cues."""

import csv
import json
import math
import time

import numpy as np
from scipy.integrate import quad

from photometry_coordinates_step7_14_v2 import OUT, digest, write


def integrate(curves, lo, hi, order=8):
    breaks = sorted({lo, hi} | {float(w) for x, _ in curves for w in x if lo < w < hi})
    nodes, weights = np.polynomial.legendre.leggauss(order)
    result = []
    for a, b in zip(breaks, breaks[1:]):
        w = (a + b) / 2 + (b - a) / 2 * nodes
        y = w**-2
        for x, v in curves:
            y = y * np.interp(w, x, v)
        result.append(float((b - a) / 2 * np.dot(weights, y)))
    return math.fsum(result)


def oracle(curves, lo, hi):
    breaks = sorted({lo, hi} | {float(w) for x, _ in curves for w in x if lo < w < hi})

    def function(w):
        return math.prod(float(np.interp(w, x, v)) for x, v in curves) / (w * w)

    return math.fsum(
        quad(function, a, b, epsabs=1e-20, epsrel=1e-12)[0]
        for a, b in zip(breaks, breaks[1:])
    )


def main():
    start = time.perf_counter()
    path = OUT / "criteri-diagnostic-cobertura-preregistrat-v2.json"
    assert digest(path) == path.with_suffix(".sha256").read_text("ascii").strip()
    policy = json.loads(path.read_text("utf8"))
    rows = list(
        csv.reader(
            (
                OUT / "fonts-primaries/data/tessw/TSL237_normalized_responsivity.csv"
            ).open(encoding="utf8")
        )
    )[1:]
    chip = tuple(np.array([float(r[i]) for r in rows]) for i in range(2))
    lo, hi = float(chip[0][0]), float(chip[0][-1])
    result = []
    for file in sorted((OUT / "fonts-primaries/report/filters").glob("*.ecsv")):
        data = list(
            csv.DictReader(
                [
                    line
                    for line in file.read_text("utf8").splitlines()
                    if not line.startswith("#")
                ]
            )
        )
        f = tuple(
            np.array([float(r[k]) for r in data])
            for k in ("Wavelength", "Transmittance")
        )
        a, b = float(f[0][0]), float(f[0][-1])
        known = integrate((chip, f), a, b)
        uv = integrate((chip,), lo, a)
        ir = integrate((chip,), b, hi)
        independent = [
            oracle((chip, f), a, b),
            oracle((chip,), lo, a),
            oracle((chip,), b, hi),
        ]
        relative = max(
            abs(x / y - 1) for x, y in zip((known, uv, ir), independent, strict=True)
        )
        magnitude = 2.5 * math.log1p((uv + ir) / known) / math.log(10)
        result.append(
            dict(
                file=file.relative_to(OUT).as_posix(),
                filterRangeNm=[a, b],
                filterSamples=len(data),
                chipRangeNm=[lo, hi],
                knownABWeightIgnoringCommonConstant=known,
                missingUvWeightUpperWithinChip=uv,
                missingIrWeightUpperWithinChip=ir,
                conditionalReferenceMagnitudeUpperWithinChip=magnitude,
                oracleRelativeError=relative,
                oraclePass=relative <= policy["oracleRelativeMaximum"],
                partialBoundWithinBudget=magnitude
                <= policy["coverageMagnitudeMaximum"],
                fullPhysicalBoundMag=None,
                outsideChipResponse="UNKNOWN",
                interpretation="Model de components condicionat; no cota total de l’instrument ni error real mesurat.",
            )
        )
    write(
        OUT / "diagnostic-cobertura-components-v2.json",
        dict(
            policySha256=digest(path),
            rows=result,
            measuredWallSeconds=time.perf_counter() - start,
            newPhysicalLos=0,
            physicalStatus="BLOCKED_NOMINAL_RESPONSE_OR_COVERAGE",
            scope=policy["model"],
        ),
    )
    print(
        json.dumps(
            dict(
                rows=len(result),
                allOraclesPass=all(r["oraclePass"] for r in result),
                rangeConditionalUpperMag=[
                    min(
                        r["conditionalReferenceMagnitudeUpperWithinChip"]
                        for r in result
                    ),
                    max(
                        r["conditionalReferenceMagnitudeUpperWithinChip"]
                        for r in result
                    ),
                ],
                wallSeconds=time.perf_counter() - start,
            ),
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
