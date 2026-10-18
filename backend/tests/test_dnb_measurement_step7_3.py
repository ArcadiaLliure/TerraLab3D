"""Proves del model DNB independent del grànul i de les dades externes."""

from __future__ import annotations

import hashlib
import json
from datetime import date
from pathlib import Path

import numpy as np
import pytest

from terralab3d.domain.light_pollution.dnb_measurement import (
    MEASUREMENT_OPERATOR_ID,
    MeasurementTarget,
    RADIANCE_UNIT,
    SpectralRadiance,
    ViirsDnbMeasurementModel,
)
from terralab3d.infrastructure.adapters.light_pollution.viirs_rsr import (
    LocalViirsSpectralResponseRepository,
    RsrQuarantineError,
    RsrUnavailableError,
)


def _entry(filename: str, sha256: str, *, release: str, start: str, end: str) -> dict[str, str]:
    return {
        "platform": "Suomi-NPP",
        "productId": "VNP46A2",
        "collection": "002",
        "releaseId": release,
        "gainStage": "night-aggregate",
        "application": "operational_vnp46",
        "validFrom": start,
        "validThrough": end,
        "fileName": filename,
        "wavelengthUnit": "nm",
        "responseUnit": "dimensionless",
        "sourceUrl": "https://example.invalid/fixture",
        "retrievedAt": "2026-10-17T00:00:00+00:00",
        "localSha256": sha256,
        "redistributionStatus": "FIXTURE",
    }


def _repo(tmp_path: Path, response: str = "0 0\n1 1\n2 0\n") -> tuple[LocalViirsSpectralResponseRepository, dict[str, str]]:
    path = tmp_path / "rsr.dat"
    path.write_text(response, encoding="utf-8")
    entry = _entry(path.name, hashlib.sha256(path.read_bytes()).hexdigest(), release="r1", start="2016-01-01", end="2016-12-31")
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps({"schemaVersion": 1, "responses": [entry]}), encoding="utf-8")
    return LocalViirsSpectralResponseRepository(manifest), entry


def _resolve(repo: LocalViirsSpectralResponseRepository, *, release: str = "r1", day: date = date(2016, 6, 1)):
    return repo.resolve(
        platform="Suomi-NPP", product_id="VNP46A2", collection="002",
        release_id=release, gain_stage="night-aggregate", acquisition_date=day,
        application="operational_vnp46",
    )


def test_band_integrated_matches_analytic_and_fine_reference(tmp_path: Path) -> None:
    repo, _ = _repo(tmp_path)
    response = _resolve(repo)
    spectrum = SpectralRadiance((0.0, 2.0), (2.0, 4.0))
    result = ViirsDnbMeasurementModel(response).measure(spectrum)
    assert result.radiance == pytest.approx(3.0)  # integral exacta de (2+λ)R(λ)
    fine_wavelengths = np.linspace(0, 2, 2001)
    fine = np.trapezoid(
        np.interp(fine_wavelengths, spectrum.wavelengths_nm, spectrum.values_per_nm)
        * np.interp(fine_wavelengths, response.wavelengths_nm, response.relative_response),
        fine_wavelengths,
    )
    step_nm = float(fine_wavelengths[1] - fine_wavelengths[0])
    # Cota del trapezi compost: (b-a)·h²·max|f''|/12; aquí b-a=2 i max|f''|=2.
    trapezoid_error_bound = 2 * step_nm**2 * 2 / 12
    assert abs(float(fine) - result.radiance) <= trapezoid_error_bound
    assert result.unit == RADIANCE_UNIT
    assert result.measurement_operator_id == MEASUREMENT_OPERATOR_ID
    assert result.rsr_release_id == "r1"
    assert result.rsr_gain_stage == "night-aggregate"
    assert result.rsr_local_sha256 == response.local_sha256


def test_rsr_not_divided_by_its_area(tmp_path: Path) -> None:
    repo, _ = _repo(tmp_path, "0 0\n1 2\n2 0\n")
    result = ViirsDnbMeasurementModel(_resolve(repo)).measure(SpectralRadiance((0.0, 2.0), (1.0, 1.0)))
    assert result.radiance == pytest.approx(2.0)


def test_signed_calibration_tail_is_preserved_without_clipping(tmp_path: Path) -> None:
    repo, _ = _repo(tmp_path, "0 0\n1 1\n2 -7.6964935e-71\n")
    response = _resolve(repo)
    assert response.relative_response[-1] == -7.6964935e-71
    assert not response.product_homologation_candidate


def test_release_and_acquisition_date_are_both_required(tmp_path: Path) -> None:
    repo, first = _repo(tmp_path)
    second = _entry("rsr2.dat", "", release="r2", start="2017-01-01", end="2017-12-31")
    second_path = tmp_path / second["fileName"]
    second_path.write_text("0 0\n1 2\n2 0\n", encoding="utf-8")
    second["localSha256"] = hashlib.sha256(second_path.read_bytes()).hexdigest()
    repo.manifest_path.write_text(json.dumps({"schemaVersion": 1, "responses": [first, second]}), encoding="utf-8")
    assert _resolve(repo, release="r2", day=date(2017, 6, 1)).relative_response[1] == 2
    with pytest.raises(RsrUnavailableError):
        _resolve(repo, release="r1", day=date(2017, 6, 1))
    with pytest.raises(RsrUnavailableError):
        _resolve(repo, release="r2", day=date(2016, 6, 1))
    with pytest.raises(RsrUnavailableError):
        _resolve(repo, release="r1", day=date(2026, 9, 13))


def test_ambiguous_and_diagnostic_rsr_never_fall_back(tmp_path: Path) -> None:
    repo, first = _repo(tmp_path)
    diagnostic = {**first, "application": "diagnostic_lgs"}
    repo.manifest_path.write_text(json.dumps({"schemaVersion": 1, "responses": [diagnostic]}), encoding="utf-8")
    with pytest.raises(RsrUnavailableError):
        _resolve(repo)
    repo.manifest_path.write_text(json.dumps({"schemaVersion": 1, "responses": [first, first]}), encoding="utf-8")
    with pytest.raises(RsrUnavailableError):
        _resolve(repo)


def test_checksum_units_and_shape_are_checked(tmp_path: Path) -> None:
    repo, entry = _repo(tmp_path)
    (tmp_path / "rsr.dat").write_text("0 0\n1 0.5\n2 0\n", encoding="utf-8")
    with pytest.raises(RsrQuarantineError, match="SHA-256"):
        _resolve(repo)
    (tmp_path / "rsr.dat").write_text("0 0\n1 1\n2 0\n", encoding="utf-8")
    entry["responseUnit"] = "per_nm"
    repo.manifest_path.write_text(json.dumps({"schemaVersion": 1, "responses": [entry]}), encoding="utf-8")
    with pytest.raises(RsrQuarantineError, match="Unitats"):
        _resolve(repo)
    entry["responseUnit"] = "dimensionless"
    (tmp_path / "rsr.dat").write_text("0 0\n1 1\n1 0\n", encoding="utf-8")
    entry["localSha256"] = hashlib.sha256((tmp_path / "rsr.dat").read_bytes()).hexdigest()
    repo.manifest_path.write_text(json.dumps({"schemaVersion": 1, "responses": [entry]}), encoding="utf-8")
    with pytest.raises(RsrQuarantineError, match="estrictament"):
        _resolve(repo)


def test_spectrum_requires_explicit_unit_and_full_coverage(tmp_path: Path) -> None:
    repo, _ = _repo(tmp_path)
    with pytest.raises(ValueError, match="Unitat"):
        SpectralRadiance((0.0, 2.0), (1.0, 1.0), unit="W m^-2 sr^-1 nm^-1")
    with pytest.raises(ValueError, match="no negativa"):
        SpectralRadiance((0.0, 2.0), (-1.0, 1.0))
    with pytest.raises(ValueError, match="cobreix"):
        ViirsDnbMeasurementModel(_resolve(repo)).measure(SpectralRadiance((0.5, 2.0), (1.0, 1.0)))


def test_measurement_target_rejects_other_platform_product_and_day(tmp_path: Path) -> None:
    repo, _ = _repo(tmp_path)
    response = _resolve(repo)
    valid = MeasurementTarget("Suomi-NPP", "VNP46A2", "002", date(2016, 6, 1))
    assert ViirsDnbMeasurementModel(response, valid).measure(
        SpectralRadiance((0.0, 2.0), (1.0, 1.0))
    ).physical_stage == "at_sensor_toa"
    for target in (
        MeasurementTarget("NOAA-20", "VNP46A2", "002", date(2016, 6, 1)),
        MeasurementTarget("Suomi-NPP", "VJ146A2", "002", date(2016, 6, 1)),
        MeasurementTarget("Suomi-NPP", "VNP46A2", "002", date(2026, 9, 13)),
    ):
        with pytest.raises(ValueError, match="correspon"):
            ViirsDnbMeasurementModel(response, target)


def test_measurement_serialization_preserves_rsr_provenance_and_toa_stage(tmp_path: Path) -> None:
    repo, entry = _repo(tmp_path)
    entry["sourceChecksum"] = "sha256:provider-published-value"
    entry["sourceArchiveSha256"] = "a" * 64
    entry["sourceMember"] = "RSR/DNB_MGS.txt"
    entry["sourceMemberSha256"] = "b" * 64
    repo.manifest_path.write_text(json.dumps({"schemaVersion": 1, "responses": [entry]}), encoding="utf-8")
    target = MeasurementTarget("Suomi-NPP", "VNP46A2", "002", date(2016, 6, 1))
    result = ViirsDnbMeasurementModel(_resolve(repo), target).measure(
        SpectralRadiance((0.0, 2.0), (1.0, 1.0))
    )
    dto = json.loads(json.dumps(result.to_dict()))
    assert dto["schemaVersion"] == 1
    assert dto["physicalStage"] == "at_sensor_toa"
    assert dto["acquisitionDate"] == "2016-06-01"
    assert dto["rsrValidFrom"] == "2016-01-01"
    assert dto["rsrSourceChecksum"] == "sha256:provider-published-value"
    assert dto["rsrLocalSha256"] == entry["localSha256"]
    assert dto["rsrSourceArchiveSha256"] == "a" * 64
    assert dto["rsrSourceMember"] == "RSR/DNB_MGS.txt"
    assert dto["rsrSourceMemberSha256"] == "b" * 64
    assert dto["rsrEvidenceClass"] == "diagnostic_historical"
    assert dto["l3LinkStatus"] == "unverified"
    assert dto["spectralUncertaintyStatus"] == "unquantified"


def test_diagnostic_curve_cannot_claim_product_homologation(tmp_path: Path) -> None:
    repo, entry = _repo(tmp_path)
    assert not _resolve(repo).product_homologation_candidate
    entry.update({
        "evidenceClass": "official_direct", "evidenceReference": "https://example.invalid/rsr",
        "l3LinkStatus": "verified", "spectralUncertaintyStatus": "quantified",
    })
    repo.manifest_path.write_text(json.dumps({"schemaVersion": 2, "responses": [entry]}), encoding="utf-8")
    with pytest.raises(RsrQuarantineError, match="vincle L3"):
        _resolve(repo)
    entry["l3LinkEvidence"] = "https://example.invalid/l3"
    with pytest.raises(RsrQuarantineError, match="incertesa"):
        repo.manifest_path.write_text(json.dumps({"schemaVersion": 2, "responses": [entry]}), encoding="utf-8")
        _resolve(repo)
    entry["spectralUncertaintyEvidence"] = "https://example.invalid/uncertainty"
    repo.manifest_path.write_text(json.dumps({"schemaVersion": 2, "responses": [entry]}), encoding="utf-8")
    assert not _resolve(repo).product_homologation_candidate  # falta el mapping de guany
    entry["gainMappingEvidence"] = "https://example.invalid/gain"
    entry["application"] = "operational_l3"
    repo.manifest_path.write_text(json.dumps({"schemaVersion": 2, "responses": [entry]}), encoding="utf-8")
    response = repo.resolve(
        platform="Suomi-NPP", product_id="VNP46A2", collection="002",
        release_id="r1", gain_stage="night-aggregate", acquisition_date=date(2016, 6, 1),
        application="operational_l3",
    )
    assert response.product_homologation_candidate
