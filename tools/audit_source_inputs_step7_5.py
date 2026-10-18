"""Audita els manifests RSR locals sense inferir cap emissió de Black Marble."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import date
from pathlib import Path

from terralab3d.infrastructure.app_paths import resolve_data_root


TARGET_PRODUCTS = {
    "Suomi-NPP": "VNP46A2",
    "NOAA-20": "VJ146A2",
    "NOAA-21": "VJ246A2",
}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--date", type=date.fromisoformat, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root = resolve_data_root() / "data" / "earth" / "light-pollution" / "viirs-rsr"
    manifests = (
        root / "noaa-ncc" / "manifest.json",
        root / "research" / "noaa-multisat" / "prepared" / "noaa-20-diagnostic-rsr.json",
        root / "research" / "noaa-multisat" / "prepared" / "noaa-21-diagnostic-rsr.json",
    )
    records = []
    for path in manifests:
        raw = path.read_bytes()
        manifest = json.loads(raw)
        for response in manifest["responses"]:
            same_day = date.fromisoformat(response["validFrom"]) <= args.date <= date.fromisoformat(response["validThrough"])
            operational_l3 = response["application"] == "operational_l3"
            applicable_target = (
                response["productId"] == TARGET_PRODUCTS.get(response["platform"])
                and response["collection"] == "002"
            )
            source_model_metadata_candidate = (
                same_day and operational_l3 and applicable_target
                and response.get("evidenceClass") in {"official_direct", "official_reconstructed"}
                and response.get("l3LinkStatus") == "verified"
                and bool(response.get("gainMappingEvidence"))
                and bool(response.get("evidenceReference"))
                and bool(response.get("l3LinkEvidence"))
            )
            records.append({
                "manifest": str(path.relative_to(resolve_data_root())),
                "manifestSha256": hashlib.sha256(raw).hexdigest(),
                "platform": response["platform"],
                "productId": response["productId"],
                "collection": response["collection"],
                "releaseId": response["releaseId"],
                "gainStage": response["gainStage"],
                "application": response["application"],
                "evidenceClass": response.get("evidenceClass", "diagnostic_historical"),
                "l3LinkStatus": response.get("l3LinkStatus", "unverified"),
                "spectralUncertaintyStatus": response.get("spectralUncertaintyStatus", "unquantified"),
                "validFrom": response["validFrom"],
                "validThrough": response["validThrough"],
                "coversRequestedDate": same_day,
                "operationalL3ForRequestedDate": same_day and operational_l3,
                "sourceModelMetadataCandidateForRequestedDate": source_model_metadata_candidate,
            })
    result = {
        "requestedDate": args.date.isoformat(),
        "manifestCount": len(manifests),
        "responseCount": len(records),
        "operationalL3Matches": sum(row["operationalL3ForRequestedDate"] for row in records),
        "sourceModelMetadataCandidateMatches": sum(row["sourceModelMetadataCandidateForRequestedDate"] for row in records),
        "records": records,
        "scope": "Inventari de manifests instal·lats; l'absència d'una entrada no prova que no existeixi una RSR fora de la biblioteca local.",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
