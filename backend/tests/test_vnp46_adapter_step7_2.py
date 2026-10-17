"""Fixtures HDF-EOS5 locals per al contracte d'observació VNP46A2.002."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from datetime import date, timedelta
from pathlib import Path

import h5py
import numpy as np
import pytest

from terralab3d.domain.light_pollution.vnp46 import Vnp46Policy
from terralab3d.infrastructure.adapters.light_pollution.vnp46 import (
    Vnp46CancelledError,
    Vnp46GranuleAdapter,
    Vnp46QuarantineError,
    Vnp46UnavailableError,
)


PROFILE = Path(__file__).resolve().parents[2] / "docs/skyglow/skyglow-v1-profile.json"
FIELDS = "HDFEOS/GRIDS/VIIRS_Grid_DNB_2d/Data Fields"


def _policy() -> Vnp46Policy:
    return Vnp46Policy.from_profile(json.loads(PROFILE.read_text(encoding="utf-8")))


def _fixture(path: Path, acquisition: date) -> tuple[Path, str]:
    day = (acquisition - date(acquisition.year, 1, 1)).days + 1
    filename = f"VNP46A2.A{acquisition.year}{day:03d}.h18v04.002.2026001000000.h5"
    file = path / filename
    with h5py.File(file, "w") as h5:
        meta = h5.create_group("HDFEOS/ADDITIONAL/FILE_ATTRIBUTES")
        meta.attrs["LocalGranuleID"] = filename
        meta.attrs["ShortName"] = "VNP46A2"
        meta.attrs["PlatformShortName"] = "SUOMI-NPP"
        meta.attrs["identifier_product_doi"] = "10.5067/VIIRS/VNP46A2.002"
        meta.attrs["AlgorithmVersion"] = "NPP_PR46A2 2.0"
        meta.attrs["PGEVersion"] = "2.0"
        meta.attrs["ProductionTime"] = "2026-01-01 00:00:00"
        meta.attrs["RangeBeginningDate"] = acquisition.isoformat()
        meta.attrs["RangeEndingDate"] = acquisition.isoformat()
        meta.attrs["ProcessingCenter"] = "LandSIPS"
        meta.attrs["VersionID"] = "002"
        meta.attrs["HorizontalTileNumber"] = "18"
        meta.attrs["VerticalTileNumber"] = "04"
        meta.attrs["InputPointer"] = ["VNP46A1.example.h5", "VNP04LGA.example.hdf"]
        fields = h5.create_group(FIELDS)
        raw = np.array([[12.5, 0.0001, -0.25, -999.9, 0.0, 5.0, 3.0, 2.0]], dtype="f4")
        radiance = fields.create_dataset("DNB_BRDF-Corrected_NTL", data=raw)
        radiance.attrs["units"] = "nWatts/(cm^2 sr) \n"
        radiance.attrs["_FillValue"] = np.float32(-999.9)
        radiance.attrs["valid_range"] = ">=0.0 \n"
        radiance.attrs["scale_factor"] = 1.0
        radiance.attrs["offset"] = 0.0
        qa = fields.create_dataset(
            "Mandatory_Quality_Flag", data=np.array([[0, 0, 0, 255, 0, 5, 1, 9]], dtype="u1")
        )
        qa.attrs["_FillValue"] = np.uint8(255)
        fields.create_dataset("QF_Cloud_Mask", data=np.array([[4] * 8], dtype="u2"))
        fields.create_dataset("Snow_Flag", data=np.array([[0] * 8], dtype="u1"))
        fields.create_dataset("Latest_High_Quality_Retrieval", data=np.array([[2] * 8], dtype="u1"))
        fields.create_dataset("lat", data=np.array([42.25], dtype="f8"))
        fields.create_dataset("lon", data=np.linspace(1.0, 1.7, 8, dtype="f8"))
        # Aquesta capa deliberada no pot substituir la capa primària.
        fields.create_dataset("Gap_Filled_DNB_BRDF-Corrected_NTL", data=np.full((1, 8), 100.0, dtype="f4"))
    return file, hashlib.sha256(file.read_bytes()).hexdigest()


def test_raw_values_quality_geolocation_and_serialization(tmp_path: Path) -> None:
    day = date(2024, 2, 29)
    path, digest = _fixture(tmp_path, day)
    adapter = Vnp46GranuleAdapter(path, policy=_policy(), expected_sha256=digest, source_url="https://example.test/granule")
    with adapter as opened:
        values = list(opened.iter_window(day, 0, 1, 0, 8))
        assert [item.classification for item in values] == [
            "candidate", "candidate", "outside_valid_range", "no_retrieval",
            "candidate", "diagnostic_only", "diagnostic_only", "unknown_quality",
        ]
        assert [item.source_inference_candidate for item in values] == [
            True, True, False, False, True, False, False, False,
        ]
        assert values[2].raw_radiance == -0.25
        assert values[3].raw_radiance == float(np.float32(-999.9))
        assert values[3].is_fill
        assert values[4].raw_radiance == 0.0  # Observació zero, no emissió nul·la demostrada.
        assert values[0].latitude_deg == 42.25
        assert values[0].longitude_deg == 1.0
        assert values[0].qf_cloud_mask == 4
        assert values[0].provenance.source_radiance_unit == "nWatts/(cm^2 sr) \n"
        assert values[0].provenance.sha256 == digest
        assert values[0].provenance.input_pointers == (
            "VNP46A1.example.h5", "VNP04LGA.example.hdf"
        )
        assert values[0].provenance.radiance_dataset_path.endswith("/DNB_BRDF-Corrected_NTL")
        encoded = json.dumps(values[1].to_dict(), allow_nan=False)
        assert json.loads(encoded)["rawRadiance"] == values[1].raw_radiance
        assert "emission" not in encoded.lower()
        assert "spd" not in encoded.lower()
    assert adapter._file is None


@pytest.mark.parametrize("day", [date(2016, 12, 31), date(2017, 1, 1)])
def test_cross_2017_preserves_small_positive_without_zero_point_correction(tmp_path: Path, day: date) -> None:
    path, digest = _fixture(tmp_path, day)
    with Vnp46GranuleAdapter(path, policy=_policy(), expected_sha256=digest) as reader:
        value = reader.read_pixel(day, 0, 1)
        assert value.raw_radiance == float(np.float32(0.0001))
        assert value.classification == "candidate"
        with pytest.raises(Vnp46UnavailableError):
            reader.read_pixel(day + timedelta(days=1), 0, 1)


def test_integrity_and_metadata_mismatch_quarantine(tmp_path: Path) -> None:
    day = date(2024, 2, 29)
    path, digest = _fixture(tmp_path, day)
    with pytest.raises(Vnp46QuarantineError, match="SHA-256"):
        with Vnp46GranuleAdapter(path, policy=_policy(), expected_sha256="0" * 64):
            pass
    with h5py.File(path, "r+") as h5:
        h5[FIELDS + "/DNB_BRDF-Corrected_NTL"].attrs["units"] = "W m^-2 sr^-1"
    changed_digest = hashlib.sha256(path.read_bytes()).hexdigest()
    with pytest.raises(Vnp46QuarantineError, match="Unitat"):
        with Vnp46GranuleAdapter(path, policy=_policy(), expected_sha256=changed_digest):
            pass
    assert digest != changed_digest


def test_missing_quality_and_missing_day_are_explicit(tmp_path: Path) -> None:
    day = date(2024, 2, 29)
    path, _ = _fixture(tmp_path, day)
    with h5py.File(path, "r+") as h5:
        del h5[FIELDS + "/Mandatory_Quality_Flag"]
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    with pytest.raises(Vnp46QuarantineError, match="Mandatory_Quality_Flag"):
        with Vnp46GranuleAdapter(path, policy=_policy(), expected_sha256=digest):
            pass
    assert Vnp46GranuleAdapter(path, policy=_policy(), expected_sha256=digest)._file is None
    with pytest.raises(Vnp46UnavailableError):
        with Vnp46GranuleAdapter(tmp_path / "missing.h5", policy=_policy(), expected_sha256=digest):
            pass


def test_cancellation_releases_file(tmp_path: Path) -> None:
    day = date(2024, 2, 29)
    path, digest = _fixture(tmp_path, day)
    calls = 0

    def cancelled() -> bool:
        nonlocal calls
        calls += 1
        return calls > 2

    with pytest.raises(Vnp46CancelledError):
        with Vnp46GranuleAdapter(path, policy=_policy(), expected_sha256=digest, cancelled=cancelled):
            pass
    with h5py.File(path, "r") as h5:
        assert FIELDS in h5


def test_inspection_entrypoint_prints_serializable_observation(tmp_path: Path) -> None:
    day = date(2024, 2, 29)
    path, digest = _fixture(tmp_path, day)
    script = PROFILE.parents[2] / "tools/inspect_vnp46_granule.py"
    result = subprocess.run(
        [
            sys.executable, str(script), str(path), "--sha256", digest,
            "--date", day.isoformat(), "--row", "0", "--column", "2",
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    payload = json.loads(result.stdout)
    assert payload["rawRadiance"] == -0.25
    assert payload["classification"] == "outside_valid_range"
    assert payload["provenance"]["sha256"] == digest


def test_quality_and_low_radiance_policy_invariant_for_all_flag_values() -> None:
    policy = _policy()
    for quality in range(256):
        for radiance in (-0.25, 0.0, 0.0001, 12.5):
            classification = policy.classify(radiance, quality, is_fill=False)
            assert (classification == "candidate") == (quality == 0 and radiance >= 0)
        assert policy.classify(float(np.float32(-999.9)), quality, is_fill=True) == "no_retrieval"


def test_collection_and_primary_layer_cannot_fall_back_silently(tmp_path: Path) -> None:
    day = date(2024, 2, 29)
    path, digest = _fixture(tmp_path, day)
    wrong_release = path.with_name(path.name.replace(".002.", ".001."))
    path.rename(wrong_release)
    with pytest.raises(Vnp46QuarantineError, match="col·lecció"):
        with Vnp46GranuleAdapter(wrong_release, policy=_policy(), expected_sha256=digest):
            pass
    wrong_release.rename(path)
    with h5py.File(path, "r+") as h5:
        del h5[FIELDS + "/DNB_BRDF-Corrected_NTL"]
    changed_digest = hashlib.sha256(path.read_bytes()).hexdigest()
    with pytest.raises(Vnp46QuarantineError, match="DNB_BRDF-Corrected_NTL"):
        with Vnp46GranuleAdapter(path, policy=_policy(), expected_sha256=changed_digest):
            pass
