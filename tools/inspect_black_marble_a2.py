"""Inspecció offline reproduïble d'un grànul Black Marble A2 ja disponible.

No descarrega dades ni declara homologada cap resposta espectral.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import h5py
import numpy as np


FIELDS = "HDFEOS/GRIDS/VIIRS_Grid_DNB_2d/Data Fields"
ATTRIBUTES = "HDFEOS/ADDITIONAL/FILE_ATTRIBUTES"
LAYERS = (
    "DNB_BRDF-Corrected_NTL",
    "Gap_Filled_DNB_BRDF-Corrected_NTL",
    "Mandatory_Quality_Flag",
    "QF_Cloud_Mask",
    "Snow_Flag",
    "Latest_High_Quality_Retrieval",
    "DNB_Lunar_Irradiance",
    "lat",
    "lon",
)


def _plain(value: object) -> object:
    if isinstance(value, bytes):
        return value.decode("utf-8").strip()
    if isinstance(value, np.ndarray):
        return [_plain(item) for item in value.reshape(-1)]
    if isinstance(value, np.generic):
        return value.item()
    return value


def _dataset(group: h5py.Group, name: str) -> h5py.Dataset:
    node = group.get(name)
    if not isinstance(node, h5py.Dataset):
        raise ValueError(f"Falta el dataset {name}")
    return node


def inspect(path: Path, expected_product: str, expected_sha256: str) -> dict[str, object]:
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    if digest.lower() != expected_sha256.lower():
        raise ValueError("SHA-256 del grànul incompatible")
    with h5py.File(path, "r") as h5:
        stores = [h5.attrs]
        if ATTRIBUTES in h5:
            stores.append(h5[ATTRIBUTES].attrs)

        def attribute(name: str) -> object | None:
            values = [_plain(store[name]) for store in stores if name in store]
            if any(value != values[0] for value in values[1:]):
                raise ValueError(f"Atribut global incompatible: {name}")
            return values[0] if values else None

        if attribute("ShortName") != expected_product or attribute("LocalGranuleID") != path.name:
            raise ValueError("Identitat de producte o grànul incompatible")
        fields = h5[FIELDS]
        if not isinstance(fields, h5py.Group):
            raise ValueError("Falta el grup Data Fields")
        layer_info = {
            name: {
                "shape": list(_dataset(fields, name).shape),
                "dtype": str(_dataset(fields, name).dtype),
                "attributes": {key: _plain(value) for key, value in _dataset(fields, name).attrs.items()},
            }
            for name in LAYERS if name in fields
        }
        radiance = _dataset(fields, "DNB_BRDF-Corrected_NTL")
        quality = _dataset(fields, "Mandatory_Quality_Flag")
        latitude = _dataset(fields, "lat")
        longitude = _dataset(fields, "lon")
        if radiance.shape != quality.shape:
            raise ValueError("Forma de radiància i qualitat incompatible")
        quality_array = quality[:]
        quality_values, counts = np.unique(quality_array, return_counts=True)
        samples = []
        for value in quality_values:
            qa = int(value)
            row, column = (int(x) for x in np.argwhere(quality_array == value)[0])
            samples.append({
                "qa": qa,
                "row": row,
                "column": column,
                "latitudeDeg": float(latitude[row]),
                "longitudeDeg": float(longitude[column]),
                "rawRadiance": float(radiance[row, column]),
            })
        return {
            "path": str(path),
            "sha256": digest,
            "interpretedPhysicalStage": "black_marble_l3_corrected_surface_upward_ntl",
            "interpretationSourceUrl": "https://viirsland.gsfc.nasa.gov/PDF/BlackMarbleUserGuide_Collection2.0.pdf",
            "metadata": {name: attribute(name) for name in (
                "LocalGranuleID", "ShortName", "PlatformShortName", "SatelliteInstrument",
                "identifier_product_doi", "AlgorithmVersion", "PGEVersion", "PGENumber",
                "ProductionTime", "ProcessingCenter", "RangeBeginningDate", "RangeEndingDate",
                "GranuleDayNightFlag", "InputPointer",
            )},
            "layers": layer_info,
            "qualityCounts": {str(int(value)): int(count) for value, count in zip(quality_values, counts)},
            "firstSampleByQuality": samples,
        }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", type=Path)
    parser.add_argument("--expected-product", required=True)
    parser.add_argument("--expected-sha256", required=True)
    args = parser.parse_args()
    print(json.dumps(inspect(args.path, args.expected_product, args.expected_sha256), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
