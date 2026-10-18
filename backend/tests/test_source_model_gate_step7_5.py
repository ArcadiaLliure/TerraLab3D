"""El gate de 7.5 no promou observacions o RSR diagnòstiques a fonts físiques."""

from __future__ import annotations

from dataclasses import replace
from datetime import date

import numpy as np
import pytest

from terralab3d.domain.light_pollution.dnb_measurement import (
    RADIANCE_UNIT,
    ViirsSpectralResponse,
)
from terralab3d.domain.light_pollution.source_model import (
    AngularEmissionProfile,
    assess_vnp46_measurement_basis,
)
from terralab3d.domain.light_pollution.vnp46 import Vnp46Observation, Vnp46Provenance


def _observation(*, quality: str = "candidate", radiance: float = 1.0) -> Vnp46Observation:
    provenance = Vnp46Provenance(
        granule_id="VNP46A2.A2026256.h18v04.002.example.h5",
        sha256="a" * 64,
        source_url=None,
        product_url="https://ladsweb.modaps.eosdis.nasa.gov/missions-and-measurements/products/VNP46A2",
        doi="10.5067/VIIRS/VNP46A2.002",
        algorithm_version="fixture",
        pge_version="fixture",
        production_time="fixture",
        range_beginning_date="2026-09-13",
        range_ending_date="2026-09-13",
        processing_center=None,
        version_id="002",
        tile_id="h18v04",
        horizontal_tile="18",
        vertical_tile="04",
        input_pointers=(),
        radiance_dataset_path="HDFEOS/GRIDS/VIIRS_Grid_DNB_2d/Data Fields/DNB_BRDF-Corrected_NTL",
        source_radiance_unit="nWatts/(cm^2 sr)",
        source_fill_value=-999.9,
        source_valid_range=">=0.0",
        source_scale_factor=1.0,
        source_offset=0.0,
    )
    return Vnp46Observation(
        schema_version=1,
        profile_id="skyglow-v1",
        product_id="VNP46A2",
        collection="002",
        acquisition_date=date(2026, 9, 13),
        row=0,
        column=0,
        latitude_deg=0.0,
        longitude_deg=0.0,
        raw_radiance=radiance,
        radiance_unit=RADIANCE_UNIT,
        quality_flag=0 if quality == "candidate" else 2,
        qf_cloud_mask=0,
        snow_flag=0,
        latest_high_quality_retrieval=0,
        is_fill=False,
        classification=quality,
        provenance=provenance,
    )


def _response() -> ViirsSpectralResponse:
    return ViirsSpectralResponse(
        platform="Suomi-NPP",
        product_id="VNP46A2",
        collection="002",
        release_id="synthetic_2026_fixture",
        gain_stage="documented_effective_gain_fixture",
        application="operational_l3",
        valid_from=date(2026, 1, 1),
        valid_through=date(2026, 12, 31),
        wavelengths_nm=(500.0, 600.0, 700.0),
        relative_response=(0.0, 1.0, 0.0),
        source_url="https://example.invalid/synthetic-fixture",
        retrieved_at="fixture",
        local_sha256="b" * 64,
        redistribution_status="FIXTURE",
        evidence_class="official_direct",
        l3_link_status="verified",
        gain_mapping_evidence="synthetic fixture only",
        evidence_reference="synthetic fixture only",
        l3_link_evidence="synthetic fixture only",
    )


def test_missing_and_historical_rsr_remain_unavailable() -> None:
    observation = _observation()
    missing = assess_vnp46_measurement_basis(observation, None)
    assert missing.status == "unavailable_for_physical_inference"
    assert missing.reasons == ("operational_rsr_unavailable",)
    assert missing.granule_sha256 == observation.provenance.sha256

    historical = replace(
        _response(), evidence_class="diagnostic_historical", application="VIIRS_DNB_TOA",
        l3_link_status="unverified", gain_mapping_evidence=None,
    )
    rejected = assess_vnp46_measurement_basis(observation, historical)
    assert "rsr_l3_gain_chain_not_accredited" in rejected.reasons
    assert not rejected.measurement_basis_admissible
    assert rejected.rsr_evidence_class == "diagnostic_historical"
    assert rejected.rsr_application == "VIIRS_DNB_TOA"


def test_quality_zero_signal_and_mismatched_day_are_distinct() -> None:
    response = _response()
    assert "quality_not_source_candidate" in assess_vnp46_measurement_basis(
        _observation(quality="diagnostic_only"), response,
    ).reasons
    assert "no_positive_l3_constraint" in assess_vnp46_measurement_basis(
        _observation(radiance=0.0), response,
    ).reasons
    wrong_day = replace(response, valid_from=date(2025, 1, 1), valid_through=date(2025, 12, 31))
    assert "rsr_product_or_date_mismatch" in assess_vnp46_measurement_basis(
        _observation(), wrong_day,
    ).reasons


def test_fixture_only_can_satisfy_measurement_basis_without_invented_sigma() -> None:
    response = _response()
    assessment = assess_vnp46_measurement_basis(_observation(), response)
    assert assessment.measurement_basis_admissible
    assert not response.product_homologation_candidate
    assert response.spectral_uncertainty_status == "unquantified"
    assert not assess_vnp46_measurement_basis(
        _observation(), replace(response, gain_mapping_evidence=" "),
    ).measurement_basis_admissible
    # Una base de mesura admissible encara no és un SourceModel: falten SPD,
    # angularitat, inversió L3 i incertesa estructural de la font.


def test_angular_profile_is_explicit_and_hemispherically_normalized() -> None:
    uniform = AngularEmissionProfile("synthetic_uniform", "fixture analítica", (0.0, 90.0), (1.0, 1.0))
    assert uniform.solid_angle_integral == pytest.approx(2 * np.pi)
    assert uniform.density_per_sr(30.0) == pytest.approx(1 / (2 * np.pi))

    horizon_weighted = AngularEmissionProfile(
        "synthetic_horizon", "fixture analítica", (0.0, 25.0, 80.0, 90.0),
        (0.0, 0.2, 1.0, 0.5),
    )
    nodes, weights = np.polynomial.legendre.leggauss(32)
    terms = []
    for left_deg, right_deg in zip(horizon_weighted.zenith_deg, horizon_weighted.zenith_deg[1:]):
        left, right = np.radians((left_deg, right_deg))
        angles = (left + right) / 2 + (right - left) * nodes / 2
        terms.append(2 * np.pi * (right - left) / 2 * np.dot(
            weights,
            [horizon_weighted.density_per_sr(float(np.degrees(angle))) * np.sin(angle) for angle in angles],
        ))
    assert sum(terms) == pytest.approx(1.0, rel=1e-12)
    assert horizon_weighted.density_per_sr(80.0) > horizon_weighted.density_per_sr(0.0)
    with pytest.raises(ValueError, match="procedència"):
        AngularEmissionProfile("missing", "", (0.0, 90.0), (1.0, 1.0))
