from __future__ import annotations

from dataclasses import replace
from datetime import date

import pytest

from terralab3d.domain.refinement.errors import LicenseRejectedError
from terralab3d.domain.refinement.licensing import (
    CommercialLicensePolicy,
    LicenseDecisionCode,
    LicenseMetadata,
    LicenseUseStage,
)


def _license(**overrides: object) -> LicenseMetadata:
    base = LicenseMetadata(
        license_id="CC-BY-4.0",
        official_url="https://creativecommons.org/licenses/by/4.0/",
        attribution_text="Contains Copernicus data (2026)",
        citation="Copernicus Land Monitoring Service",
        provider="Copernicus CLMS",
        product="HRL Croplands",
        version="2025-r1",
        checked_at=date(2026, 8, 25),
        provenance_url="https://land.copernicus.eu/",
        asset_fingerprints=("sha256:fixture",),
        commercial_use=True,
    )
    return replace(base, **overrides)


@pytest.mark.parametrize(
    "metadata",
    [
        _license(),
        _license(license_id="CC0-1.0"),
        _license(license_id="public-domain"),
        _license(license_id="copernicus-clms"),
        _license(license_id="OME-attribution", attribution_only_equivalent=True),
    ],
)
@pytest.mark.parametrize("stage", list(LicenseUseStage))
def test_verified_commercial_licenses_are_allowed_at_both_gates(
    metadata: LicenseMetadata,
    stage: LicenseUseStage,
) -> None:
    decision = CommercialLicensePolicy().evaluate(metadata, stage=stage)

    assert decision.allowed
    assert decision.code is LicenseDecisionCode.ALLOWED


@pytest.mark.parametrize(
    ("metadata", "code"),
    [
        (_license(license_id="ODbL-1.0", odbl=True), LicenseDecisionCode.ODBL),
        (_license(license_id="CC-BY-SA-4.0", share_alike=True), LicenseDecisionCode.SHARE_ALIKE),
        (
            _license(
                license_id="CC-BY-SA-4.0",
                provider="EuroCrops",
                product="EuroCrops",
                share_alike=True,
            ),
            LicenseDecisionCode.SHARE_ALIKE,
        ),
        (_license(license_id="unknown"), LicenseDecisionCode.UNKNOWN_LICENSE),
        (_license(research_only=True), LicenseDecisionCode.RESEARCH_ONLY),
        (_license(commercial_use=False), LicenseDecisionCode.COMMERCIAL_USE_FORBIDDEN),
        (_license(non_commercial=True), LicenseDecisionCode.NON_COMMERCIAL),
        (
            _license(derived_database_share_alike=True),
            LicenseDecisionCode.DERIVED_DATABASE_SHARE_ALIKE,
        ),
        (_license(attribution_text=""), LicenseDecisionCode.MISSING_ATTRIBUTION),
        (_license(asset_fingerprints=()), LicenseDecisionCode.INCOMPLETE_METADATA),
        (_license(metadata_complete=False), LicenseDecisionCode.INCOMPLETE_METADATA),
        (
            _license(
                license_id="CC0",
                upstream_licenses=("ODbL-1.0",),
                upstream_sources=("OpenStreetMap",),
            ),
            LicenseDecisionCode.ODBL,
        ),
        (
            _license(license_id="CC0", upstream_sources=("OSM highways",)),
            LicenseDecisionCode.FORBIDDEN_LINEAGE,
        ),
    ],
)
def test_incompatible_or_unverifiable_products_are_blocked(
    metadata: LicenseMetadata,
    code: LicenseDecisionCode,
) -> None:
    policy = CommercialLicensePolicy()

    decision = policy.evaluate(metadata, stage=LicenseUseStage.CATALOG_DISPLAY)

    assert not decision.allowed
    assert decision.code is code
    with pytest.raises(LicenseRejectedError, match=code.value):
        policy.require_allowed(metadata, stage=LicenseUseStage.JOB_START)
