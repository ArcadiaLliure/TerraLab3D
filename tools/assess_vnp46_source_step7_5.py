"""Diagnòstic offline de la base de mesura de 7.5 per a un píxel VNP46 real."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from datetime import date
from pathlib import Path

from terralab3d.domain.light_pollution.source_model import assess_vnp46_measurement_basis
from terralab3d.domain.light_pollution.vnp46 import Vnp46Policy
from terralab3d.infrastructure.adapters.light_pollution.vnp46 import (
    Vnp46CancelledError,
    Vnp46GranuleAdapter,
    Vnp46QuarantineError,
    Vnp46UnavailableError,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Avalua QA i RSR/L3 de la base de mesura, sense inferir emissió")
    parser.add_argument("granule", type=Path)
    parser.add_argument("--sha256", required=True)
    parser.add_argument("--date", required=True, type=date.fromisoformat)
    parser.add_argument("--row", required=True, type=int)
    parser.add_argument("--column", required=True, type=int)
    parser.add_argument(
        "--profile", type=Path,
        default=Path(__file__).resolve().parents[1] / "docs/skyglow/skyglow-v1-profile.json",
    )
    args = parser.parse_args()
    try:
        policy = Vnp46Policy.from_profile(json.loads(args.profile.read_text(encoding="utf-8")))
        with Vnp46GranuleAdapter(args.granule, policy=policy, expected_sha256=args.sha256) as reader:
            observation = reader.read_pixel(args.date, args.row, args.column)
        # Cap RSR operativa 2026 està acreditada als manifests actuals. La CLI
        # no eleva automàticament una taula diagnòstica a resposta de producte.
        assessment = assess_vnp46_measurement_basis(observation, None)
        print(json.dumps({
            "observation": observation.to_dict(),
            "measurementAssessment": asdict(assessment),
            "sourceModel": None,
        }, ensure_ascii=False, allow_nan=False, indent=2))
        return 0
    except (OSError, ValueError, KeyError, Vnp46UnavailableError, Vnp46QuarantineError, Vnp46CancelledError) as exc:
        print(f"Base de mesura VNP46 no disponible: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
