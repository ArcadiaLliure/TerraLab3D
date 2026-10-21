"""Arxiva fonts primàries i deriva models de referència explícitament incomplets."""

import csv
import hashlib
import io
import json
import statistics
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs/evidencies/pas7.14"
LPCOMMIT = "0f55129d6a27ccfe489558f1f46d441e278626f6"
LICACOMMIT = "a70ee75f24ef3c9766673a8dbb449147f90a1352"
SOURCES = {
    "sqm-cm500-svo.xml": "https://svo2.cab.inta-csic.es/theory/fps/fps.php?ID=Cameras/SQM.CM500",
    "stars1277-frequencies.csv": f"https://raw.githubusercontent.com/guaix-ucm/licaplot/{LPCOMMIT}/data/tessw/stars1277-frequencies.csv",
    "stars1277-photodiode.csv": f"https://raw.githubusercontent.com/guaix-ucm/licaplot/{LPCOMMIT}/data/tessw/stars1277-photodiode.csv",
    "pin10d-responsivity.ecsv": f"https://raw.githubusercontent.com/guaix-ucm/lica/{LICACOMMIT}/src/lica/lab/photodiode/PIN-10D-Responsivity-Cross-Calibrated@1nm.ecsv",
    "licaplot-gpl3-license.txt": f"https://raw.githubusercontent.com/guaix-ucm/licaplot/{LPCOMMIT}/LICENSE",
    "lica-license.txt": f"https://raw.githubusercontent.com/guaix-ucm/lica/{LICACOMMIT}/LICENSE",
}


def prepare():
    folder = OUT / "fonts"
    folder.mkdir(exist_ok=True)
    manifest = []
    for name, url in SOURCES.items():
        path = folder / name
        if not path.exists():
            with urllib.request.urlopen(url, timeout=25) as r:
                path.write_bytes(r.read())
        manifest.append(
            dict(
                file=name, url=url, sha256=hashlib.sha256(path.read_bytes()).hexdigest()
            )
        )
    table = ET.parse(folder / "sqm-cm500-svo.xml")
    params = {
        p.attrib["name"]: p.attrib.get("value") for p in table.findall(".//PARAM")
    }
    assert params["DetectorType"] == "0", "La resposta ha de ser d’energia, no QE sola"
    rows = [[float(c.text) for c in tr.findall("TD")] for tr in table.findall(".//TR")]
    sqm = dict(
        responseId="SQM-CM500-Cinzano2005-SVO-reference-v1",
        kind="SQM",
        wavelengthsNm=[r[0] / 10 for r in rows],
        energyResponse=[r[1] for r in rows],
        provenance="Cinzano2005 Fig8, SVO Cameras/SQM.CM500, digitització publicada; detectorType0 energy counter",
        fovModelId="SQM-L-nominal-Gaussian20deg-2019-v1",
        nominalFwhmDeg=20,
        fovProvenance="Bará/Tapia/Zamorano2019 §2.1: aproximadament gaussià FWHM20°; no FOV mesurat de la unitat2005",
        zeroPointId="AB-3631Jy-arcsec2-tabulated-reference-band-v1",
        limitations=[
            "Resposta SVO truncada amb valor final no nul; cua espectral desconeguda",
            "Resposta2005 i FOV nominalSQM-L2019 no són un perfil mesurat de la mateixa unitat",
            "Cap calibratge natiu emparellat amb aquest perfil",
        ],
        redistribution="Valors de mesures publicades i atribució SVO/Cinzano; no es redistribueix el PDF ni codi de tercers",
    )
    frequencies: dict[float, list[float]] = {}
    with (folder / "stars1277-frequencies.csv").open(encoding="utf8") as f:
        for row in csv.DictReader(f, delimiter=";"):
            frequencies.setdefault(float(row["wavelength (nm)"]), []).append(
                float(row["frequency (Hz)"])
            )
    currents = {}
    with (folder / "stars1277-photodiode.csv").open(encoding="utf8") as f:
        for row in csv.DictReader(f, delimiter=";"):
            currents[float(row["wavelength (nm)"])] = abs(float(row["current (A)"]))
    lines = "\n".join(
        line
        for line in (folder / "pin10d-responsivity.ecsv").read_text("utf8").splitlines()
        if not line.startswith("#")
    )
    diode = list(csv.DictReader(io.StringIO(lines)))
    waves = [float(r["Wavelength"]) for r in diode]
    responsivity = [float(r["Responsivity"]) for r in diode]
    x = sorted(frequencies)
    assert set(x) <= currents.keys() and waves[0] <= min(x) < max(x) <= waves[-1]
    energy = [
        statistics.median(frequencies[w])
        * float(np.interp(w, waves, responsivity))
        / currents[w]
        for w in x
    ]
    maximum = max(energy)
    assert maximum > 0 and min(energy) >= 0
    tess = dict(
        responseId="TESSW-stars1277-LICA2024-reference-v1",
        kind="TESS_W",
        wavelengthsNm=x,
        energyResponse=[v / maximum for v in energy],
        provenance=f"LICA stars1277 2024-10-30; licaplot{LPCOMMIT}; PIN10D de lica{LICACOMMIT}. Mediana(f)·R_PIN/|i_PIN|, normalitzada al màxim. No s’afegeix λ: és resposta d’energia.",
        fovModelId="TESSW-nominal-Gaussian17deg-2019-v1",
        nominalFwhmDeg=17,
        fovProvenance="Bará/Tapia/Zamorano2019 §2.1: aproximadament gaussià FWHM17°, no mesura angular de stars1277",
        zeroPointId="AB-3631Jy-arcsec2-tabulated-reference-band-v1",
        limitations=[
            "Freqüència fosca no documentada amb aquestes mesures: model de referència amb fosc no resolt",
            "No hi ha resposta angular mesurada emparellada amb stars1277",
            "Suport mesurat finit i cap cota acreditada de resposta fora de taula",
            "Calibratge natiu i incertesa conjunta no acreditats per aquest model",
        ],
        medianStatistic="Mediana determinista de totes les freqüències per λ; cap resta arbitrària del fosc",
        redistribution="Dades de licaplot sota GPL3 i calibratge PIN de lica sota MIT; llicències adjuntes. No es reutilitza codi de tercers.",
    )
    for name, value in [
        ("models-resposta-referencia.json", [sqm, tess]),
        ("fonts-manifest.json", manifest),
    ]:
        path = OUT / name
        text = json.dumps(value, ensure_ascii=False, indent=2) + "\n"
        if path.exists():
            assert path.read_text("utf8") == text, (
                "Models canviats: cal una versió nova"
            )
        else:
            path.write_text(text, encoding="utf8", newline="\n")
    print(
        [
            (
                r["responseId"],
                len(r["wavelengthsNm"]),
                r["wavelengthsNm"][0],
                r["wavelengthsNm"][-1],
            )
            for r in (sqm, tess)
        ]
    )


if __name__ == "__main__":
    prepare()
