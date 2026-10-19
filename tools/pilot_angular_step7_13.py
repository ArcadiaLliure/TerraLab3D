"""Mesura prospectiva sense comparació runtime/oracle ni decisió angular."""

import json
import time
from dataclasses import replace

from angular_fixtures_step7_13 import fixture
from transport_gate_fixtures_step7_12 import ROOT
from validate_transport_gate_step7_12 import measured, reference, write
from terralab3d.domain.light_pollution.geometric_transport import ViewDirection
from terralab3d.domain.light_pollution.propagation_kernel import DirectionSet


if __name__ == "__main__":
    out = ROOT / "docs/evidencies/pas7.13"
    policy = json.loads(
        (out / "criteri-angular-preregistrat-v1.json").read_text(encoding="utf8")
    )
    rows = []
    for name, az, el in [
        (policy["fixtures"][0], 90, 0.5),
        (policy["fixtures"][0], 270, 45),
        (policy["fixtures"][-1], 90, 25),
    ]:
        req = replace(
            fixture(name), directions=DirectionSet((ViewDirection("pilot", az, el),))
        )
        run = measured(req)
        times = []
        for level in policy["referenceLevels"]:
            start = time.perf_counter()
            reference(req, level)
            times.append(time.perf_counter() - start)
        rows.append(
            dict(
                fixture=name,
                azimuthDeg=az,
                elevationDeg=el,
                runtimeSeconds=run["wallSeconds"],
                referenceSeconds=times,
            )
        )
        write(out / "pilot-cost.json", rows)
        print(rows[-1], flush=True)
