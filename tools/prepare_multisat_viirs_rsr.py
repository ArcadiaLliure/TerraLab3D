"""Extreu RSR DNB NOAA per a diagnòstic offline; no descarrega grànuls.

Els fitxers resultants es guarden a la biblioteca de dades externa indicada per
--output. Cap entrada del manifest afirma equivalència amb Black Marble L3.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from zipfile import ZipFile


SOURCES = {
    "NOAA-20": {
        "product": "VJ146A2",
        "release": "J1_DAWG_at_launch_V2.1",
        "launch": "2017-11-18",
        "url": "https://ncc.nesdis.noaa.gov/NOAA-20/docs/J1_VIIRS_RSR_DAWG_At-Launch_Public_Release_V2.1_Nov2016.zip",
        "members": {
            "LGS": "J1_VIIRS_RSR_DNBLGS_BA_Fused_V2FS.txt",
            "MGS": "J1_VIIRS_RSR_DNBMGS_BA_V1F.txt",
        },
    },
    "NOAA-21": {
        "product": "VJ246A2",
        "release": "J2_DAWG_at_launch_V2",
        "launch": "2022-11-10",
        "url": "https://ncc.nesdis.noaa.gov/NOAA-21/docs/J2_VIIRS_RSR_DAWG_At-Launch_Public_Release_V2_Jul2019.zip",
        "members": {
            "LGS": "J2_VIIRS_RSR_DNBLGS_BA_Fused_V2FS.txt",
            "MGS": "J2_VIIRS_RSR_DNBMGS_BA_Fused_V2FS.txt",
        },
    },
}


def prepare(archive: Path, output: Path, platform: str) -> Path:
    source = SOURCES[platform]
    output.mkdir(parents=True, exist_ok=True)
    archive_sha256 = hashlib.sha256(archive.read_bytes()).hexdigest()
    responses = []
    with ZipFile(archive) as package:
        members = package.namelist()
        for gain_stage, basename in source["members"].items():
            matches = [name for name in members if name.rsplit("/", 1)[-1] == basename]
            if len(matches) != 1:
                raise ValueError(f"Manca un membre únic: {basename}")
            member = matches[0]
            raw = package.read(member)
            samples = []
            for line in raw.decode("ascii").splitlines():
                parts = line.split()
                if len(parts) == 3 and parts[0] in {"DNBL", "DNBM"}:
                    samples.append((float(parts[1]), float(parts[2])))
            if len(samples) < 2 or any(y < 0 for _, y in samples):
                raise ValueError(f"RSR invàlida: {basename}")
            text = "".join(f"{x:.8f} {y:.10g}\n" for x, y in samples)
            filename = f"{platform.lower()}-{gain_stage.lower()}-at-launch.dat"
            target = output / filename
            target.write_bytes(text.encode("utf-8"))
            responses.append({
                "platform": platform,
                "productId": "VIIRS_DNB_TOA",
                "collection": "at_launch_reference",
                "relatedBlackMarbleProduct": source["product"],
                "releaseId": source["release"],
                "gainStage": gain_stage,
                "application": "diagnostic_at_launch_toa",
                "validFrom": source["launch"],
                "validThrough": source["launch"],
                "fileName": filename,
                "wavelengthUnit": "nm",
                "responseUnit": "dimensionless",
                "sourceUrl": source["url"],
                "sourceArchiveSha256": archive_sha256,
                "sourceMember": member,
                "sourceMemberSha256": hashlib.sha256(raw).hexdigest(),
                "retrievedAt": "2026-10-18",
                "localSha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
                "redistributionStatus": "external_data_only",
                "evidenceClass": "diagnostic_historical",
                "evidenceReference": source["url"],
                "l3LinkStatus": "unverified",
                "spectralUncertaintyStatus": "unquantified",
            })
            if platform == "NOAA-21" and gain_stage == "MGS":
                responses.append({
                    **responses[-1],
                    "gainStage": "HGS_proxy_MGS",
                    "evidenceClass": "official_recommended_proxy",
                    "gainMappingEvidence": "Readme_J2_VIIRS_RSR_DAWG_At-Launch_Public_Release_V2_July2019.pdf in source archive",
                    "proxyLimitation": "HGS was not measured prelaunch; no numerical spectral uncertainty bound is supplied",
                })
    manifest = output / f"{platform.lower()}-diagnostic-rsr.json"
    manifest.write_text(
        json.dumps({"schemaVersion": 2, "responses": responses}, indent=2) + "\n",
        encoding="utf-8",
    )
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("platform", choices=sorted(SOURCES))
    parser.add_argument("archive", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    print(prepare(args.archive, args.output, args.platform))


if __name__ == "__main__":
    main()
