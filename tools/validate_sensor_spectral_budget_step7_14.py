"""Reutilitza l’oracle fi7.10 amb les respostes de referència7.14, sense accelerar-lo."""

import json
import time
from dataclasses import replace
from pathlib import Path

from photometry_fixtures_step7_14 import OUT, profiles
from validate_photometry_step7_14 import digest
import validate_spectral_transport_step7_10 as harness


def run():
    policy_path = OUT / "criteri-espectral-sensors-preregistrat-v1.json"
    assert (
        digest(policy_path)
        == policy_path.with_suffix(".sha256").read_text("ascii").strip()
    )
    policy = json.loads(policy_path.read_text("utf8"))
    response_models = profiles()
    original_spectra = harness.cases()[0]
    original_parameters = harness.operators()
    # Models de banda coneguda: el zero és la finestra d’aquest diagnòstic,
    # mai l’afirmació que la resposta física desconeguda del sensor sigui zero.
    curves = [
        replace(
            p.curve,
            source_id=p.response_id + "-KNOWN-SUPPORT-WINDOW-ONLY",
            outside_support="zero",
        )
        for p in response_models
    ]
    selected = [
        p
        for p in original_parameters
        if p["mu"] in (-1.0, 1.0)
        and p["alpha"] in (0.0, 2.0)
        and p["ozoneColumnM2"] in (0.0, 1e24)
    ]
    assert len(selected) == policy["operators"]
    harness.cases = lambda: (original_spectra, [(c,) for c in curves])
    harness.operators = lambda: selected
    binding = dict(
        policySha256=digest(policy_path),
        codeSha256=digest(Path(__file__)),
        oracleHarnessSha256=digest(Path(harness.__file__)),
        responseModelsSha256=digest(OUT / "models-resposta-referencia.json"),
        spectrumIds=[s.spectrum_id for s in original_spectra],
        responseIds=[c.source_id for c in curves],
        operators=selected,
    )
    destination = OUT / "espectral-v1"
    destination.mkdir(exist_ok=True)
    binding_path = destination / "vinculacio-espectral-v1.json"
    assert not binding_path.exists(), "Conservar la campanya i versionar una repetició"
    binding_path.write_text(
        json.dumps(binding, ensure_ascii=False, indent=2) + "\n",
        encoding="utf8",
        newline="\n",
    )
    start = time.perf_counter()
    harness.run(destination)
    result = json.loads((destination / "pressupost-espectral.json").read_text("utf8"))
    report = dict(
        campaignId=policy["id"],
        harnessProtocolId=result["protocolId"],
        caseCount=result["caseCount"],
        passed=result["passed"],
        failed=result["failed"],
        maximumErrorMag=result["maximumErrorMag"],
        maximumLutErrorMag=result["maximumLutErrorMag"],
        maximumSimpsonErrorMag=result["maximumSimpsonErrorMag"],
        maximumOracleRelativeRefinement=result["maximumOracleRelativeRefinement"],
        wallSeconds=time.perf_counter() - start,
        fullSQMorTESSInstrumentValidated=False,
        domain=policy["domain"],
        thresholdMagnitude=0.01,
    )
    (OUT / "pressupost-espectral-sensors-v1.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf8",
        newline="\n",
    )
    assert result["failed"] == 0 and report["maximumErrorMag"] <= 0.01
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    run()
