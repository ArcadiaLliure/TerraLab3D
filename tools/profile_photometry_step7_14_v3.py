"""Diagnòstic de cost del candidat intacte7.14v2, sense transport ni optimització."""

from __future__ import annotations

import argparse
import cProfile
import hashlib
import io
import json
import os
from pathlib import Path
import platform
import pstats
import sys
import time
from typing import cast

from photometry_coordinates_step7_14_v2 import cie_standard_air
from project_skyglow_photometry import spectral_payload
from terralab3d.application.coordinate_photometry import project_coordinate_band

ROOT = Path(__file__).resolve().parents[1]


def run(output: Path) -> None:
    output.mkdir(parents=True, exist_ok=True)
    target = output / "cost-projeccio-v3.json"
    if target.exists():
        raise FileExistsError("Cal un directori nou; no sobreescriure evidències")
    base = ROOT / "docs/evidencies/pas7.14"
    prereg = base / "represa-v3/criteri-diagnostic-preregistrat-v3.json"
    prereg_hash = hashlib.sha256(prereg.read_bytes()).hexdigest()
    assert prereg_hash == (prereg.with_suffix(".sha256")).read_text("ascii").strip()
    policy = json.loads(prereg.read_text("utf8"))
    binding = json.loads(
        (base / "represa-v2/vinculacio-candidat-v3.json").read_text("utf8")
    )
    # El manifest final fixa tant el candidat numèric com la resta del runtime.
    manifest = json.loads(
        (base / "represa-v2/manifest-final-represa-v2.json").read_text("utf8")
    )
    assert all(
        hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == sha
        for name, sha in manifest["sourceHashes"].items()
    )
    start = time.perf_counter()
    raw = json.loads((base / "transport-i-projeccions.json").read_text("utf8"))
    decode_start = time.perf_counter()
    cases = [
        (row, spectral_payload(row["captured"]).spectral_samples[0]) for row in raw
    ]
    decode_seconds = time.perf_counter() - decode_start
    response_start = time.perf_counter()
    response = cie_standard_air()
    response_seconds = time.perf_counter() - response_start
    references = json.loads(
        (base / "represa-v2/coordenades-i-postprojeccions-v2.json").read_text("utf8")
    )
    (output / "reference-schema.txt").write_text(
        repr(list(references)) + "\n", encoding="utf8"
    )
    rows = []
    for row, samples in cases:
        tick = time.perf_counter()
        result = project_coordinate_band(
            samples,
            response,
            input_radiance_basis="vacuum_nm",
            domain_nm=(samples.knots_nm[0], samples.knots_nm[-1]),
        )
        previous = next(
            r for r in references["postProjections"] if r["name"] == row["name"]
        )
        oracle = previous["oracle"]
        relative = (
            abs(result.signal.value / oracle - 1)
            if oracle
            else 0.0
            if result.signal.value == 0
            else None
        )
        rows.append(
            dict(
                caseId=row["name"],
                panels=len(samples.knots_nm) - 1,
                responseKnots=len(response.curve.values),
                wallSeconds=time.perf_counter() - tick,
                signal=result.signal.value,
                losError=result.signal.los_error_estimate,
                refinementError=result.refinement_error,
                independentOracle=oracle,
                relativeError=relative,
                exactlyMatchesFrozenResult=result.signal.value
                == previous["coordinateProjection"]["signal"]["value"],
                passCriterion=relative is not None
                and relative
                <= policy["inheritedCriteria"]["projectionRelativeMaximum"],
            )
        )
        assert (
            time.perf_counter() - start < policy["campaign"]["maximumScientificSeconds"]
        )
    chosen = next(
        samples
        for row, samples in cases
        if row["name"] == policy["campaign"]["profilingCase"]
    )

    def project():
        return project_coordinate_band(
            chosen,
            response,
            input_radiance_basis="vacuum_nm",
            domain_nm=(chosen.knots_nm[0], chosen.knots_nm[-1]),
        )

    repeated = []
    for _ in range(policy["campaign"]["timedRepeats"]):
        tick = time.perf_counter()
        project()
        repeated.append(time.perf_counter() - tick)
    profiler = cProfile.Profile()
    tick = time.perf_counter()
    profiler.runcall(project)
    profile_seconds = time.perf_counter() - tick
    profiler.dump_stats(str(output / "projeccio-cie-v3.prof"))
    stream = io.StringIO()
    stats = pstats.Stats(profiler, stream=stream).sort_stats("cumulative")
    stats.print_stats(35)
    (output / "cprofile-cumulative-v3.txt").write_text(
        stream.getvalue(), encoding="utf8"
    )
    functions = []
    profile_rows = cast(
        dict[tuple[str, int, str], tuple[int, int, float, float, object]],
        vars(stats)["stats"],
    )
    for (filename, line, name), (
        primitive,
        calls,
        own,
        cumulative,
        _,
    ) in profile_rows.items():
        if name in {
            "leggauss",
            "at_vacuum",
            "air_from_vacuum",
            "vacuum_knots",
            "density",
            "_integrate_response_prepared",
        }:
            functions.append(
                dict(
                    function=name,
                    line=line,
                    primitiveCalls=primitive,
                    calls=calls,
                    exclusiveSeconds=own,
                    cumulativeSeconds=cumulative,
                )
            )
    elapsed = time.perf_counter() - start
    result = dict(
        schemaVersion=1,
        ownerStep="7.14",
        policySha256=prereg_hash,
        candidateBindingSha256=hashlib.sha256(
            json.dumps(binding, sort_keys=True).encode()
        ).hexdigest(),
        python=sys.version,
        platform=platform.platform(),
        threadEnvironment={
            k: os.environ.get(k)
            for k in ["OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"]
        },
        retainedDecodeSeconds=decode_seconds,
        responsePreparationSeconds=response_seconds,
        cases=rows,
        repeatedUnprofiledSeconds=repeated,
        profiledSeconds=profile_seconds,
        profiledFunctions=functions,
        calculationWallSeconds=elapsed,
        physicalTransportEvaluations=0,
        runtimeChanged=False,
        interpretation="Temps profilats instrumentats; no sumar temps inclusius. Repeticions de paret sense profiler separades. Cap SLO ni acceleració acreditada.",
    )
    assert elapsed < policy["campaign"]["maximumScientificSeconds"]
    target.write_text(
        json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False) + "\n",
        encoding="utf8",
    )
    print(
        json.dumps(
            dict(cases=len(rows), wallSeconds=elapsed, profileSeconds=profile_seconds),
            indent=2,
        )
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    run(parser.parse_args().output)
