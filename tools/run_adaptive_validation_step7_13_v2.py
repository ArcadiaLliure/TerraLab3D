"""Conductor serial amb estimació prospectiva i mesura completa de cada fase."""

import json
import subprocess
import sys
import time
from datetime import datetime, timezone

from validate_adaptive_dome_step7_13_v2 import OUT, ROOT, policy
from validate_transport_gate_step7_12 import write


def run():
    p = policy()
    builds = [
        json.loads(
            (OUT / (name.lower().replace("_", "-") + "-camp.json")).read_text(
                encoding="utf8"
            )
        )
        for name in p["fixtures"]
    ]
    spent = sum(d["wallSeconds"] for d in builds)
    for part, estimate in [
        ("holdout", p["cost"]["estimateValidationSeconds"]),
        ("controls", 820.0),
    ]:
        timings = OUT / f"temps-{part}.json"
        if timings.exists():
            result = json.loads(timings.read_text(encoding="utf8"))
            assert result["exitCode"] == 0
            spent += result["wallSeconds"]
            continue
        write(
            OUT / f"estimacio-{part}.json",
            dict(
                registeredAtUtc=datetime.now(timezone.utc).isoformat(),
                estimatedWallSeconds=estimate,
                spentScientificSeconds=spent,
                maximumCampaignSeconds=p["cost"][
                    "maximumScientificCampaignWallSeconds"
                ],
                note="Projecció orientativa abans de la fase. Controls:3COESA1km75km més12DEM i3àrees; cap rebaixa de precisió.",
            ),
        )
        if spent + estimate > p["cost"]["maximumScientificCampaignWallSeconds"]:
            raise RuntimeError("La projecció excedeix el pressupost preregistrat")
        start = time.perf_counter()
        with (OUT / f"log-{part}.txt").open("w", encoding="utf8", newline="\n") as log:
            process = subprocess.run(
                [
                    sys.executable,
                    "-X",
                    "utf8",
                    str(ROOT / "tools/validate_adaptive_dome_step7_13_v2.py"),
                    "--part",
                    part,
                ],
                stdout=log,
                stderr=subprocess.STDOUT,
            )
        duration = time.perf_counter() - start
        write(
            timings,
            dict(
                part=part,
                wallSeconds=duration,
                exitCode=process.returncode,
                estimatedSeconds=estimate,
                serialExecution=True,
                includesProcessSetup=True,
            ),
        )
        print(part, process.returncode, duration, flush=True)
        if process.returncode:
            raise SystemExit(process.returncode)
        spent += duration
        if spent > p["cost"]["maximumScientificCampaignWallSeconds"]:
            raise RuntimeError(
                "Pressupost real de campanya exhaurit; gate no certificable"
            )


if __name__ == "__main__":
    run()
