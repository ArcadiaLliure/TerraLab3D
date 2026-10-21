"""Fonts explícites i identitat de la represa7.14; sense canviar fixtures anteriors."""

from pathlib import Path
import hashlib
import json

from photometry_fixtures_step7_14 import profiles
from terralab3d.domain.wavelength_coordinates import CoordinateCurve

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs/evidencies/pas7.14/represa-v2"
POLICY_SHA = "babc518000b27dae4ffd0909bb13e1282d7b86894b5ee70678cb848c35b4d780"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def policy():
    p = OUT / "criteri-represa-preregistrat-v2.json"
    assert digest(p) == POLICY_SHA
    return json.loads(p.read_text("utf8"))


def cie_standard_air():
    return CoordinateCurve(profiles()[0].curve, "standard_air_450ppm_nm", "response")


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n",
        encoding="utf8",
        newline="\n",
    )
