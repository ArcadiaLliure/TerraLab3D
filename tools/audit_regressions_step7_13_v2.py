"""Reprodueix les comparacions exactes amb els baselines científics anteriors."""

import json
from collections import Counter

from validate_adaptive_dome_step7_13_v2 import OUT, ROOT, digest
from validate_transport_gate_step7_12 import write


def diagnostics(data):
    return Counter(
        json.dumps(
            {**d, "file": d["file"].replace("\\", "/").lower()},
            sort_keys=True,
        )
        for d in data["generalDiagnostics"]
    )


def audit():
    def read(path):
        return json.loads(path.read_text(encoding="utf8"))

    baseline = read(ROOT / "docs/evidencies/pas7.13/pyright-global.json")
    current = read(OUT / "pyright-global.json")
    columns = read(OUT / "columnes-b0.json")
    old_columns = read(ROOT / "docs/evidencies/pas7.8/resultats-optical-field-v1.json")
    original = read(
        ROOT / "docs/evidencies/pas7.12/campanya-v1/vinculacio-candidat-v1.json"
    )
    code_differences = [
        name
        for name, sha in original["codeHashes"].items()
        if digest(ROOT / name) != sha
    ]
    preservation = read(OUT / "preservacio-inicial.json")
    evidence_differences = [
        name
        for name, sha in preservation["files"].items()
        if digest(ROOT / name) != sha
    ]
    exact_columns = [
        a["result"] == b["result"]
        for a, b in zip(columns["cases"], old_columns["cases"], strict=True)
    ]
    expected_b0 = "21d3453df822b95d56aa508fee6bd9c76e712b27c63f3f03a3222e86e075b53e"
    b0 = columns["b0Regression"]
    checks = dict(
        samePyrightDiagnosticMultiset=diagnostics(current) == diagnostics(baseline),
        sameFourColumns=len(exact_columns) == 4 and all(exact_columns),
        sameB0=b0["actualSignature"] == expected_b0 and b0["identical"],
        previousScientificCodeUnchanged=not code_differences,
        previousEvidenceUnchanged=not evidence_differences,
    )
    result = dict(
        status="PASS" if all(checks.values()) else "FAIL",
        checks=checks,
        pyrightSummary=current["summary"],
        exactColumns=exact_columns,
        b0Regression=b0,
        previousScientificCodeCount=len(original["codeHashes"]),
        previousScientificCodeDifferences=code_differences,
        historicalEvidenceCount=len(preservation["files"]),
        historicalEvidenceDifferences=evidence_differences,
        timing="Benchmarks B0–B4 històrics preservats; sense nova campanya ni inferència de speedup.",
    )
    write(OUT / "regressions-i-preservacio-v2.json", result)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return all(checks.values())


if __name__ == "__main__":
    raise SystemExit(0 if audit() else 1)
