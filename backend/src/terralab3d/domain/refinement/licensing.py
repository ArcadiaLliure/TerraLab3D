"""Fail-closed commercial licensing policy for refinement products."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date
from enum import Enum

from .errors import LicenseRejectedError


class LicenseUseStage(str, Enum):
    CATALOG_DISPLAY = "catalog_display"
    JOB_START = "job_start"


class LicenseDecisionCode(str, Enum):
    ALLOWED = "allowed"
    INCOMPLETE_METADATA = "incomplete_metadata"
    COMMERCIAL_USE_FORBIDDEN = "commercial_use_forbidden"
    NON_COMMERCIAL = "non_commercial"
    SHARE_ALIKE = "share_alike"
    ODBL = "odbl"
    DERIVED_DATABASE_SHARE_ALIKE = "derived_database_share_alike"
    RESEARCH_ONLY = "research_only"
    UNKNOWN_LICENSE = "unknown_license"
    MISSING_ATTRIBUTION = "missing_attribution"
    FORBIDDEN_LINEAGE = "forbidden_lineage"


@dataclass(frozen=True, slots=True)
class LicenseMetadata:
    license_id: str
    official_url: str
    attribution_text: str
    citation: str
    provider: str
    product: str
    version: str
    checked_at: date | None
    provenance_url: str
    asset_fingerprints: tuple[str, ...]
    commercial_use: bool | None
    non_commercial: bool = False
    share_alike: bool = False
    odbl: bool = False
    derived_database_share_alike: bool = False
    research_only: bool = False
    attribution_only_equivalent: bool = False
    metadata_complete: bool = True
    upstream_licenses: tuple[str, ...] = ()
    upstream_sources: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class LicenseDecision:
    allowed: bool
    code: LicenseDecisionCode
    stage: LicenseUseStage
    reason: str


class CommercialLicensePolicy:
    """Approve only licenses compatible with commercial derived products."""

    _ALLOWED_IDS = frozenset(
        {
            "public-domain",
            "public_domain",
            "cc0",
            "cc0-1.0",
            "cc-by-4.0",
            "cc_by_4_0",
            "copernicus-clms",
            "copernicus-data-policy",
        }
    )

    def evaluate(
        self,
        metadata: LicenseMetadata,
        *,
        stage: LicenseUseStage,
    ) -> LicenseDecision:
        required = (
            metadata.license_id,
            metadata.official_url,
            metadata.provider,
            metadata.product,
            metadata.version,
            metadata.provenance_url,
        )
        if (
            not metadata.metadata_complete
            or any(not value.strip() for value in required)
            or metadata.checked_at is None
            or not metadata.asset_fingerprints
        ):
            return self._reject(
                LicenseDecisionCode.INCOMPLETE_METADATA,
                stage,
                "License provenance is incomplete or cannot be verified",
            )
        normalized = _normalize_license_id(metadata.license_id)
        lineage = " ".join(
            (
                metadata.license_id,
                metadata.provider,
                metadata.product,
                metadata.provenance_url,
                *metadata.upstream_licenses,
                *metadata.upstream_sources,
            )
        ).lower()
        if metadata.research_only or "research only" in lineage:
            return self._reject(
                LicenseDecisionCode.RESEARCH_ONLY,
                stage,
                "The product is restricted to research use",
            )
        if metadata.non_commercial or re.search(r"\bcc[-_ ]?by[-_ ]?nc\b|noncommercial|non-commercial", lineage):
            return self._reject(
                LicenseDecisionCode.NON_COMMERCIAL,
                stage,
                "The product contains a NonCommercial restriction",
            )
        if metadata.odbl or "odbl" in lineage:
            return self._reject(
                LicenseDecisionCode.ODBL,
                stage,
                "ODbL products are outside the commercial redistribution policy",
            )
        if "openstreetmap" in lineage or re.search(r"\bosm\b", lineage):
            return self._reject(
                LicenseDecisionCode.FORBIDDEN_LINEAGE,
                stage,
                "The product lineage contains OpenStreetMap/ODbL data",
            )
        if metadata.share_alike or "sharealike" in lineage or re.search(r"\bcc[-_ ]?by[-_ ]?sa\b", lineage):
            return self._reject(
                LicenseDecisionCode.SHARE_ALIKE,
                stage,
                "ShareAlike obligations are not accepted",
            )
        if metadata.derived_database_share_alike:
            return self._reject(
                LicenseDecisionCode.DERIVED_DATABASE_SHARE_ALIKE,
                stage,
                "Derived databases would inherit a reciprocal license",
            )
        if metadata.commercial_use is not True:
            return self._reject(
                LicenseDecisionCode.COMMERCIAL_USE_FORBIDDEN,
                stage,
                "Commercial use is not explicitly permitted",
            )
        if not metadata.attribution_text.strip():
            return self._reject(
                LicenseDecisionCode.MISSING_ATTRIBUTION,
                stage,
                "Attribution text must be storable with the installation",
            )
        if normalized not in self._ALLOWED_IDS and not metadata.attribution_only_equivalent:
            return self._reject(
                LicenseDecisionCode.UNKNOWN_LICENSE,
                stage,
                "The license is not in the verified allow-list",
            )
        return LicenseDecision(
            allowed=True,
            code=LicenseDecisionCode.ALLOWED,
            stage=stage,
            reason="Commercial use, derivatives and local persistence are permitted",
        )

    def require_allowed(
        self,
        metadata: LicenseMetadata,
        *,
        stage: LicenseUseStage,
    ) -> None:
        decision = self.evaluate(metadata, stage=stage)
        if not decision.allowed:
            raise LicenseRejectedError(f"{decision.code.value}: {decision.reason}")

    @staticmethod
    def _reject(
        code: LicenseDecisionCode,
        stage: LicenseUseStage,
        reason: str,
    ) -> LicenseDecision:
        return LicenseDecision(False, code, stage, reason)


def _normalize_license_id(value: str) -> str:
    return value.strip().lower().replace(" ", "-")
