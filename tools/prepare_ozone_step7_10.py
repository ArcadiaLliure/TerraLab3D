"""Reprodueix els dos assets derivats d'O3 sense xarxa ni retall de negatius."""

from __future__ import annotations

import argparse
import hashlib
import io
from pathlib import Path

import numpy as np

ORIGINAL_SHA256 = "b5001c303b8cd74e92b906e443f30b7141432d9f5ff2071e248351f77db51fdb"


def prepare(original: Path, output: Path) -> None:
    raw = original.read_bytes()
    if hashlib.sha256(raw).hexdigest() != ORIGINAL_SHA256:
        raise ValueError("No és l'original Zenodo verificat")
    source = np.loadtxt(io.BytesIO(raw), skiprows=45)
    visible = source[(source[:, 0] >= 380) & (source[:, 0] <= 780)]
    # Columna 193K rebutjada, no corregida; ordre publicat 293→193K.
    data = np.column_stack((visible[:, 0], visible[:, 1:11][:, ::-1] * 1e-4))
    if np.any(data[:, 1:] < 0):
        raise ValueError("Dades no físiques al domini 203–293 K")
    compressed = io.BytesIO()
    np.savez_compressed(
        compressed,
        wavelengths_nm=data[:, 0],
        temperatures_k=np.arange(203.0, 294.0, 10.0),
        cross_sections_m2=data[:, 1:].T,
    )
    wavelengths = np.arange(380.0, 780.1, 0.5)
    lut = np.column_stack(
        [wavelengths]
        + [np.interp(wavelengths, data[:, 0], data[:, i]) for i in range(1, 11)]
    )
    csv = io.BytesIO()
    np.savetxt(csv, lut, delimiter=",", fmt="%.12e")
    output.mkdir(parents=True, exist_ok=True)
    for filename, contents in (
        ("o3-serdyuchenko-visible-raw.npz", compressed.getvalue()),
        ("o3-serdyuchenko-visible-lut.csv", csv.getvalue().replace(b"\n", b"\r\n")),
    ):
        target = output / filename
        if target.exists() and target.read_bytes() != contents:
            raise ValueError("Es preserva l'asset existent diferent: " + str(target))
        target.write_bytes(contents)
        print(filename, hashlib.sha256(contents).hexdigest())


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--original", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    prepare(args.original, args.output)
