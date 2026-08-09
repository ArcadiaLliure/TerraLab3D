"""Download independent JPL Horizons vectors used by Step 8.6 tests.

The resulting compact JSON is evidence, not a runtime authority.  Runtime
positions continue to come exclusively from the installed NAIF SPKs.
"""

from __future__ import annotations

import csv
import json
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path


FIXTURES = (
    ("Moon", 301, 399),
    ("Phobos", 401, 499),
    ("Deimos", 402, 499),
    ("Io", 501, 599),
    ("Europa", 502, 599),
    ("Ganymede", 503, 599),
    ("Callisto", 504, 599),
    ("Himalia", 506, 599),
    ("Enceladus", 602, 699),
    ("Titan", 606, 699),
    ("Iapetus", 608, 699),
    ("Phoebe", 609, 699),
    ("Ymir", 619, 699),
    ("Titania", 703, 799),
    ("Oberon", 704, 799),
    ("Miranda", 705, 799),
    ("Triton", 801, 899),
    ("Nereid", 802, 899),
    ("Charon", 901, 999),
    ("Nix", 902, 999),
    ("Hydra", 903, 999),
)

API = "https://ssd.jpl.nasa.gov/api/horizons.api"


def main() -> int:
    records = []
    for name, body, parent in FIXTURES:
        params = {
            "format": "json",
            "COMMAND": f"'{body}'",
            "OBJ_DATA": "'NO'",
            "MAKE_EPHEM": "'YES'",
            "EPHEM_TYPE": "'VECTORS'",
            "CENTER": f"'@{parent}'",
            "START_TIME": "'2026-07-09'",
            "STOP_TIME": "'2026-07-10'",
            "STEP_SIZE": "'1 d'",
            "REF_PLANE": "'FRAME'",
            "REF_SYSTEM": "'ICRF'",
            "VEC_CORR": "'NONE'",
            "OUT_UNITS": "'KM-S'",
            "VEC_TABLE": "'2'",
            "CSV_FORMAT": "'YES'",
        }
        url = API + "?" + urllib.parse.urlencode(params)
        with urllib.request.urlopen(url, timeout=60) as response:
            payload = json.load(response)
        result = str(payload["result"])
        block = result.split("$$SOE", 1)[1].split("$$EOE", 1)[0].strip()
        row = next(csv.reader([block.splitlines()[0]], skipinitialspace=True))
        records.append({
            "name": name,
            "naifId": body,
            "parentNaifId": parent,
            "julianDateTdb": float(row[0]),
            "positionJ2000Km": [float(value) for value in row[2:5]],
            "velocityJ2000KmS": [float(value) for value in row[5:8]],
            "requestUrl": url,
        })
        print(f"MGP: [HorizonsFixtures] [download] [body={name} naif={body}]")

    output = Path(__file__).resolve().parents[1] / "backend" / "tests" / "fixtures" / "horizons_satellites_2026_07_09.json"
    output.write_text(json.dumps({
        "source": API,
        "apiSignature": {"source": "NASA/JPL Horizons API", "version": "1.2"},
        "acquiredAtUtc": datetime.now(timezone.utc).isoformat(),
        "referenceFrame": "J2000/ICRF",
        "referencePlane": "FRAME",
        "corrections": "NONE",
        "units": "KM-S",
        "fixtures": records,
    }, indent=2) + "\n", encoding="utf-8")
    print(f"MGP: [HorizonsFixtures] [complete] [file={output} fixtures={len(records)}]")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
