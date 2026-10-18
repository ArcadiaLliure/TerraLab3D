"""Biblioteca CIE petita empaquetada i verificada; cap xarxa implícita."""

from __future__ import annotations

import csv
import hashlib
import io
import json
from importlib.resources import files

from terralab3d.domain.light_pollution.source_model import DefinedSpectrum
from terralab3d.domain.light_pollution.spectral_library import SpectralLibrary


def load_spectral_library() -> SpectralLibrary:
    root = files("terralab3d.infrastructure.catalogs").joinpath("spectra")
    manifest = json.loads(root.joinpath("manifest.json").read_text(encoding="utf-8"))
    tables = {}
    spectra: dict[str, DefinedSpectrum] = {}
    technologies: dict[str, str] = {}
    for entry in manifest["assets"]:
        raw = root.joinpath(entry["file"]).read_bytes()
        if (
            hashlib.sha256(raw).hexdigest() != entry["sha256"]
            or hashlib.md5(raw).hexdigest() != entry["publishedMd5"]
        ):
            raise ValueError(f"Checksum CIE incorrecte: {entry['file']}")
        metadata_raw = root.joinpath(entry["metadataFile"]).read_bytes()
        if hashlib.sha256(metadata_raw).hexdigest() != entry["metadataSha256"]:
            raise ValueError("Checksum de metadades CIE incorrecte")
        rows = tuple(
            tuple(float(v) for v in row)
            for row in csv.reader(io.StringIO(raw.decode("utf-8-sig")))
        )
        tables[entry["file"]] = rows
        if entry["file"] not in {
            "CIE_illum_LEDs_1nm.csv",
            "CIE_illum_HPs.csv",
            "CIE_illum_FLs_1nm.csv",
            "CIE_RefSpectrum_L41.csv",
        }:
            continue
        metadata = json.loads(metadata_raw)
        for column, header in enumerate(
            metadata["datatableInfo"]["columnHeaders"][1:], 1
        ):
            name = header["title"]
            description = header.get("description", "reference LED")
            technologies[name] = description
            spectra[name] = DefinedSpectrum(
                name,
                entry["sourcePage"],
                "CC BY-SA 4.0",
                tuple(row[0] for row in rows),
                tuple(row[column] for row in rows),
                asset_sha256=entry["sha256"],
                origin_kind="published_table",
            )
    xyz = tables["CIE_xyz_1931_2deg.csv"]
    photopic = tables["CIE_sle_photopic.csv"]
    return SpectralLibrary(
        "cie-tables-2026-10-18-v1",
        spectra,
        technologies,
        tuple(row[0] for row in xyz),
        tuple(tuple(row[i] for row in xyz) for i in (1, 2, 3)),
        tuple(row[0] for row in photopic),
        tuple(row[1] for row in photopic),
    )
