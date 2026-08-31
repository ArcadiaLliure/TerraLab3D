"""Typed WebSocket payloads shared by refinement application use cases."""

from __future__ import annotations

from typing import Literal, NotRequired, TypedDict


GeoJsonGeometry = dict[str, object]


class RequestRefinementWorkspaceMessage(TypedDict):
    type: Literal["request_refinement_workspace"]
    requestId: str
    revision: int
    aoi: NotRequired[GeoJsonGeometry]


class QueryRefinementProductsMessage(TypedDict):
    type: Literal["query_refinement_products"]
    requestId: str
    revision: int
    categoryKey: str
    aoi: GeoJsonGeometry


class CancelRefinementQueryMessage(TypedDict):
    type: Literal["cancel_refinement_query"]
    requestId: str
    revision: int


class CalculateRefinementPlanMessage(TypedDict):
    type: Literal["calculate_refinement_plan"]
    requestId: str
    revision: int
    categoryKey: str
    aoi: GeoJsonGeometry
    productIds: list[str]


class ConfirmRefinementDownloadMessage(TypedDict):
    type: Literal["confirm_refinement_download"]
    requestId: str
    revision: int
    planId: str
    largeDownloadConfirmed: bool


class CancelRefinementDownloadMessage(TypedDict):
    type: Literal["cancel_refinement_download"]
    requestId: str
    revision: int
    planId: str


class RemoveRefinementInstallationMessage(TypedDict):
    type: Literal["remove_refinement_installation"]
    requestId: str
    revision: int
    installationId: str


class RefinementInstallationPayload(TypedDict):
    installationId: str
    provider: str
    product: str
    version: str


class RefinementWorkspaceNodePayload(TypedDict):
    categoryKey: str
    parentKey: str | None
    label: str
    depth: int
    state: str
    verifiedPercent: float
    plannedPercent: float
    installations: list[RefinementInstallationPayload]
    applicable: bool


class RefinementWorkspacePayload(TypedDict):
    taxonomyKey: str
    taxonomyVersion: str
    virtualRoot: Literal["surface"]
    aoi: GeoJsonGeometry | None
    nodes: list[RefinementWorkspaceNodePayload]


class RefinementWorkspaceSnapshotMessage(TypedDict):
    type: Literal["refinement_workspace_snapshot"]
    requestId: str
    revision: int
    workspace: RefinementWorkspacePayload


class RefinementProviderFailurePayload(TypedDict):
    providerId: str
    code: str
    message: str


class RefinementLicensePayload(TypedDict):
    licenseId: str
    officialUrl: str
    attribution: str
    commercialUse: Literal[True]
    checkedAt: str


class RefinementRemoteAssetPayload(TypedDict):
    assetId: str
    fileName: str
    footprint: GeoJsonGeometry
    order: int
    estimatedBytes: int | None
    checksumAlgorithm: Literal["md5", "sha256"] | None
    checksumValue: str | None
    requiresAuthentication: bool
    classAttribute: str | None


class RefinementCandidatePayload(TypedDict):
    candidateId: str
    providerId: str
    provider: str
    product: str
    version: str
    datasetIdentifier: str
    compatibleTlstNodes: list[str]
    footprint: GeoJsonGeometry
    resolutionM: float
    temporalStart: str | None
    temporalEnd: str | None
    format: str
    estimatedBytes: int | None
    availablePercent: float
    newEffectivePercent: float
    qualifierKey: str | None
    endpointVerified: bool
    license: RefinementLicensePayload
    assets: list[RefinementRemoteAssetPayload]
    installationId: str | None


class RefinementCandidatesMessage(TypedDict):
    type: Literal["refinement_candidates"]
    requestId: str
    revision: int
    categoryKey: str
    candidates: list[RefinementCandidatePayload]
    failures: list[RefinementProviderFailurePayload]


class RefinementCoveragePayload(TypedDict):
    existingPercent: float
    newEffectivePercent: float
    plannedPercent: float
    remainingPercent: float
    existing: GeoJsonGeometry | None
    planned: GeoJsonGeometry | None
    remaining: GeoJsonGeometry | None
    recommendedProductIds: list[str]


class FrozenRefinementAssetPayload(RefinementRemoteAssetPayload):
    providerId: str
    product: str
    version: str
    downloadUrl: str
    licenseId: str
    licenseUrl: str
    attribution: str
    provenanceUrl: str
    classTranslation: dict[str, str]
    nodataValues: list[int]
    qualifierKey: str | None


class RefinementDownloadPlanPayload(TypedDict):
    schemaVersion: Literal[4]
    planId: str
    requestId: str
    revision: int
    categoryKeys: list[str]
    productIds: list[str]
    aoi: GeoJsonGeometry
    assets: list[FrozenRefinementAssetPayload]
    processingOptions: dict[str, str | int | float | bool]
    estimatedBytes: int | None
    requiresLargeDownloadConfirmation: bool


class RefinementPlanSummaryMessage(TypedDict):
    type: Literal["refinement_plan_summary"]
    requestId: str
    revision: int
    categoryKey: str
    productIds: list[str]
    coverage: RefinementCoveragePayload
    plan: RefinementDownloadPlanPayload


class RefinementOutputsPayload(TypedDict):
    manifest: str | None
    mosaic: str | None
    source: str | None
    quality: str | None
    conflict: str | None


class RefinementDownloadProgressMessage(TypedDict):
    type: Literal["refinement_download_progress"]
    requestId: str
    revision: int
    planId: str
    jobId: str
    state: str
    downloadedBytes: int
    totalBytes: int | None
    progress: float | None
    currentFile: str | None
    assetProgress: list[dict[str, object]]
    outputs: RefinementOutputsPayload
    error: str | None


class RefinementCoverageUpdatedMessage(TypedDict):
    type: Literal["refinement_coverage_updated"]
    requestId: str
    revision: int
    categoryKey: str
    installationId: str
    verifiedPercent: float
    verifiedGeometry: GeoJsonGeometry | None
    outputs: RefinementOutputsPayload


class RefinementInstallationRemovedMessage(TypedDict):
    type: Literal["refinement_installation_removed"]
    requestId: str
    revision: int
    installationId: str


class RefinementOperationErrorMessage(TypedDict):
    type: Literal["refinement_operation_error"]
    requestId: str
    revision: int
    operation: Literal["workspace", "query", "plan", "confirm", "cancel", "remove"]
    code: str
    message: str
    providerId: NotRequired[str]


RefinementFrontendMessage = (
    RequestRefinementWorkspaceMessage
    | QueryRefinementProductsMessage
    | CancelRefinementQueryMessage
    | CalculateRefinementPlanMessage
    | ConfirmRefinementDownloadMessage
    | RemoveRefinementInstallationMessage
)

RefinementBackendMessage = (
    RefinementWorkspaceSnapshotMessage
    | RefinementCandidatesMessage
    | RefinementPlanSummaryMessage
    | RefinementDownloadProgressMessage
    | RefinementCoverageUpdatedMessage
    | RefinementInstallationRemovedMessage
    | RefinementOperationErrorMessage
)
