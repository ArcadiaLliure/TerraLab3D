"""Executa NOAA-20 real → SourceModel C; no implementa SG-REF ni transport."""

from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path

from terralab3d.domain.light_pollution.simulation import SkyglowConfiguration
from terralab3d.domain.light_pollution.vnp46 import Vnp46Policy
from terralab3d.infrastructure.adapters.light_pollution.black_marble_sources import (
    read_conditional_sources,
)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("granule", type=Path)
    parser.add_argument("--sha256", required=True)
    parser.add_argument("--date", type=date.fromisoformat, required=True)
    parser.add_argument("--row", type=int, required=True)
    parser.add_argument("--column", type=int, required=True)
    parser.add_argument("--rsr-manifest", type=Path, required=True)
    parser.add_argument("--gain", choices=["LGS", "MGS"], default="MGS")
    parser.add_argument("--mode", choices=["realistic", "kelvin"], required=True)
    parser.add_argument("--kelvin", type=float, default=3000)
    parser.add_argument("--normalization", default="constant_photopic_flux")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    policy = Vnp46Policy.from_profile(
        json.loads(
            (root / "docs/skyglow/skyglow-v1-profile.json").read_text(encoding="utf-8")
        )
    )
    results = read_conditional_sources(
        args.granule,
        args.sha256,
        policy,
        args.date,
        args.row,
        args.column,
        args.rsr_manifest,
        SkyglowConfiguration(
            mode=args.mode, kelvin=args.kelvin, normalization=args.normalization
        ),
        gain_stage=args.gain,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(
            [r.to_dict() for r in results],
            ensure_ascii=False,
            indent=2,
            allow_nan=False,
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"{len(results)} fonts condicionades; transport pendent; {args.output}")


if __name__ == "__main__":
    main()
