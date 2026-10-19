"""Catàleg offline verificat; cap descàrrega ni lectura de dades al domini."""

import hashlib
import io
import json
from importlib.resources import files

import numpy as np

from terralab3d.domain.light_pollution.gas_absorption import GasCrossSectionLut


def load_ozone_lut(*, fine: bool = False) -> GasCrossSectionLut:
    root = files("terralab3d.infrastructure.catalogs").joinpath("gases")
    manifest = json.loads(root.joinpath("manifest.json").read_text(encoding="utf-8"))
    name = (
        "o3-serdyuchenko-visible-raw.npz" if fine else "o3-serdyuchenko-visible-lut.csv"
    )
    raw = root.joinpath(name).read_bytes()
    sha = hashlib.sha256(raw).hexdigest()
    if sha != manifest["assets"][name]:
        raise ValueError("Checksum de la LUT gasosa incorrecte")
    if fine:
        with np.load(io.BytesIO(raw), allow_pickle=False) as data:
            waves = data["wavelengths_nm"]
            temperatures = data["temperatures_k"]
            cross_sections = data["cross_sections_m2"]
    else:
        data = np.loadtxt(io.BytesIO(raw), delimiter=",")
        waves, temperatures, cross_sections = (
            data[:, 0],
            manifest["temperaturesK"],
            data[:, 1:].T,
        )
    return GasCrossSectionLut(
        manifest["species"],
        manifest["revision"] + ("-fine" if fine else ""),
        tuple(float(x) for x in waves),
        tuple(float(x) for x in temperatures),
        tuple(tuple(float(x) for x in row) for row in cross_sections),
        "https://doi.org/" + manifest["doi"],
        manifest["license"],
        sha,
    )
