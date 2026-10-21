"""Compara les dues hipòtesis ja calculades; diagnòstic, no nou PASS/FAIL."""

import csv
import gzip
import math
import statistics
import time

from photometry_coordinates_step7_14_v2 import OUT, write


def main():
    start = time.perf_counter()
    groups = {}
    with gzip.open(
        OUT / "espectral-v2/casos-pressupost-espectral.csv.gz",
        "rt",
        encoding="utf8",
        newline="",
    ) as stream:
        for row in csv.DictReader(stream):
            identifier = row["response"]
            if ":vacuum_nm:response:" in identifier:
                base = identifier.split(":vacuum_nm:response:", 1)[0]
                basis = "vacuum_nm"
            elif ":standard_air_450ppm_nm:response:" in identifier:
                base = identifier.split(":standard_air_450ppm_nm:response:", 1)[0]
                basis = "standard_air_450ppm_nm"
            else:
                continue
            groups.setdefault((row["spd"], row["operator"], base), {})[basis] = float(
                row["reference_raw"]
            )
    rows = []
    for (spd, operator, response), values in groups.items():
        v, a = values["vacuum_nm"], values["standard_air_450ppm_nm"]
        if min(v, a) > 0:
            rows.append(
                dict(
                    spd=spd,
                    operator=operator,
                    response=response,
                    magnitudeDifference=-2.5 * math.log10(a / v),
                )
            )
    summary = []
    for response in sorted({r["response"] for r in rows}):
        selected = [r for r in rows if r["response"] == response]
        worst = max(selected, key=lambda r: abs(r["magnitudeDifference"]))
        summary.append(
            dict(
                response=response,
                comparisons=len(selected),
                maximumAbsoluteDifferenceMag=abs(worst["magnitudeDifference"]),
                medianAbsoluteDifferenceMag=statistics.median(
                    abs(r["magnitudeDifference"]) for r in selected
                ),
                worst=worst,
            )
        )
    result = dict(
        summary=summary,
        comparisonCount=len(rows),
        measuredCalculationWallSeconds=time.perf_counter() - start,
        newPhysicalLos=0,
        decision="DESCRIPTIVE_ONLY",
        scope="Dues hipòtesis i finestres desplaçades explícites; la diferència no és error de discretització ni identifica la coordenada real del laboratori.",
    )
    path = OUT / "diferencies-hipotesis-coordenades-v2.json"
    assert not path.exists(), "Conservar el diagnòstic i versionar una repetició"
    write(path, result)
    print(summary)


if __name__ == "__main__":
    main()
