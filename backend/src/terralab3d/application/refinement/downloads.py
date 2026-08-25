"""Freeze reviewed discovery candidates into executable resource plans."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import PurePosixPath
from urllib.parse import urlsplit

from terralab3d.domain.identifiers import ResourceId, VariantId
from terralab3d.domain.refinement.discovery import (
    DiscoveredRefinementProduct,
    DiscoveryRequest,
)
from terralab3d.domain.refinement.downloads import (
    FrozenDownloadAsset,
    ParametricDownloadPlan,
)
from terralab3d.domain.refinement.errors import RefinementValidationError
from terralab3d.domain.refinement.licensing import CommercialLicensePolicy, LicenseUseStage
from terralab3d.domain.resources.models import (
    AcquisitionKind,
    ResourceCategory,
    ResourceDescriptor,
    ResourceDomain,
    ResourceVariant,
)


def freeze_parametric_plan(
    request: DiscoveryRequest,
    candidates: Sequence[DiscoveredRefinementProduct],
    product_ids: Sequence[str],
    license_policy: CommercialLicensePolicy,
    *,
    plan_id: str,
    processing_options: Mapping[str, str | int | float | bool] | None = None,
    large_download_threshold_bytes: int = 5_000_000_000,
) -> ParametricDownloadPlan:
    selected_ids = tuple(dict.fromkeys(product_ids))
    selected = [item for item in candidates if item.candidate_id in selected_ids]
    if len(selected) != len(selected_ids) or not selected:
        raise RefinementValidationError("All selected product ids must come from discovery")
    for candidate in selected:
        license_policy.require_allowed(
            candidate.license,
            stage=LicenseUseStage.JOB_START,
        )
    frozen_assets: list[FrozenDownloadAsset] = []
    for candidate in selected:
        for asset in candidate.assets:
            frozen_assets.append(
                FrozenDownloadAsset(
                    asset_id=asset.asset_id,
                    provider_id=candidate.provider_id,
                    product=candidate.product,
                    version=candidate.version,
                    download_url=asset.download_url,
                    file_name=_asset_file_name(asset.s3_path, asset.download_url, asset.asset_id),
                    footprint=asset.footprint,
                    order=len(frozen_assets),
                    expected_bytes=asset.estimated_bytes,
                    checksum_algorithm=asset.checksum_algorithm,
                    checksum_value=asset.checksum_value,
                    license_id=candidate.license.license_id,
                    license_url=candidate.license.official_url,
                    attribution=candidate.license.attribution_text,
                    provenance_url=candidate.license.provenance_url,
                    requires_authentication=asset.requires_authentication,
                )
            )
    known_sizes = [asset.expected_bytes for asset in frozen_assets]
    estimated_bytes = (
        sum(size for size in known_sizes if size is not None)
        if all(size is not None for size in known_sizes)
        else None
    )
    return ParametricDownloadPlan(
        plan_id=plan_id,
        request_id=request.request_id,
        revision=request.revision,
        category_keys=(request.category_key,),
        aoi_geojson=request.aoi_geojson,
        assets=tuple(frozen_assets),
        processing_options=dict(processing_options or {}),
        estimated_bytes=estimated_bytes,
        requires_large_download_confirmation=(
            estimated_bytes is not None
            and estimated_bytes >= large_download_threshold_bytes
        ),
    )


def resource_descriptor_from_plan(plan: ParametricDownloadPlan) -> ResourceDescriptor:
    resource_id = ResourceId(f"earth.refinement.{_safe_id(plan.plan_id)}")
    variant_id = VariantId(f"plan-r{plan.revision}")
    providers = sorted({asset.provider_id for asset in plan.assets})
    licenses = sorted({asset.license_id for asset in plan.assets})
    attributions = tuple(dict.fromkeys(asset.attribution for asset in plan.assets))
    return ResourceDescriptor(
        id=resource_id,
        name=f"Refinament TLST {plan.plan_id}",
        description=f"Pla congelat per {', '.join(plan.category_keys)}",
        domain=ResourceDomain.EARTH,
        category=ResourceCategory.LAND_COVER,
        provider=", ".join(providers),
        acquisition_kind=AcquisitionKind.PARAMETRIC_DOWNLOAD,
        citation="; ".join(attributions),
        license=", ".join(licenses),
        variants=(
            ResourceVariant(
                id=variant_id,
                title=f"Revisió {plan.revision}",
                source_urls=tuple(asset.download_url for asset in plan.assets),
                format="provider-assets",
                expected_bytes=plan.estimated_bytes,
                metadata=(("parametricPlan", plan.to_json()),),
            ),
        ),
        credits=attributions,
        metadata=(
            ("requestId", plan.request_id),
            ("revision", plan.revision),
            ("requiresLargeDownloadConfirmation", plan.requires_large_download_confirmation),
        ),
    )


def _safe_id(value: str) -> str:
    normalized = "".join(
        character.lower() if character.isalnum() else "_"
        for character in value.strip()
    ).strip("_")
    if not normalized:
        raise RefinementValidationError("Plan id cannot form a resource id")
    return normalized


def _asset_file_name(s3_path: str | None, download_url: str, asset_id: str) -> str:
    candidates = (
        PurePosixPath(s3_path).name if s3_path else "",
        PurePosixPath(urlsplit(download_url).path).name,
    )
    file_name = next(
        (candidate for candidate in candidates if candidate and candidate != "$value"),
        f"{_safe_id(asset_id)}.bin",
    )
    if file_name in {".", ".."} or "/" in file_name or "\\" in file_name:
        raise RefinementValidationError("Asset filename is unsafe")
    return file_name
