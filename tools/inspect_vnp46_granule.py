"""Inspecciona una mostra local VNP46A2.002 amb el contracte del Pas 7.2."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path

from terralab3d.domain.light_pollution.vnp46 import Vnp46Policy
from terralab3d.infrastructure.adapters.light_pollution.vnp46 import (
    Vnp46CancelledError,
    Vnp46GranuleAdapter,
    Vnp46QuarantineError,
    Vnp46UnavailableError,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Valida i llegeix un píxel VNP46A2.002 local")
    parser.add_argument("granule", type=Path, help="Fitxer HDF5 descarregat de LAADS")
    parser.add_argument("--sha256", required=True, help="SHA-256 registrat abans de llegir el grànul")
    parser.add_argument("--date", required=True, type=date.fromisoformat, help="Dia d'adquisició ISO 8601")
    parser.add_argument("--row", required=True, type=int)
    parser.add_argument("--column", required=True, type=int)
    parser.add_argument("--source-url", help="URL d'origen exacte del grànul")
    parser.add_argument(
        "--profile",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "docs/skyglow/skyglow-v1-profile.json",
    )
    args = parser.parse_args()
    try:
        policy = Vnp46Policy.from_profile(json.loads(args.profile.read_text(encoding="utf-8")))
        with Vnp46GranuleAdapter(
            args.granule,
            policy=policy,
            expected_sha256=args.sha256,
            source_url=args.source_url,
        ) as reader:
            observation = reader.read_pixel(args.date, args.row, args.column)
        print(json.dumps(observation.to_dict(), ensure_ascii=False, allow_nan=False, indent=2))
        return 0
    except (OSError, ValueError, KeyError, Vnp46UnavailableError, Vnp46QuarantineError, Vnp46CancelledError) as exc:
        print(f"Observació VNP46 no disponible: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
