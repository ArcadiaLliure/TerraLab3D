/** Provider-neutral bridge contracts for hierarchical TLST refinements. */

export type RefinementCoverageState =
  | "complete"
  | "partial"
  | "absent"
  | "not_applicable";

export type RefinementTechnicalState =
  | "QUEUED"
  | "DOWNLOADING"
  | "VERIFYING"
  | "PROCESSING"
  | "READY"
  | "ERROR"
  | "CANCELLED";

export type GeoJsonPosition = readonly [number, number] | readonly [number, number, number];

export interface GeoJsonPolygon {
  readonly type: "Polygon";
  readonly coordinates: ReadonlyArray<ReadonlyArray<GeoJsonPosition>>;
}

export interface GeoJsonMultiPolygon {
  readonly type: "MultiPolygon";
  readonly coordinates: ReadonlyArray<
    ReadonlyArray<ReadonlyArray<GeoJsonPosition>>
  >;
}

export type RefinementGeometry = GeoJsonPolygon | GeoJsonMultiPolygon;

export interface RefinementWorkspaceNode {
  readonly categoryKey: string;
  readonly parentKey: string | null;
  readonly label: string;
  readonly depth: number;
  readonly state: RefinementCoverageState;
  readonly verifiedPercent: number;
  readonly plannedPercent: number;
  readonly installationIds: readonly string[];
  readonly applicable: boolean;
}

export interface RefinementWorkspace {
  readonly taxonomyKey: string;
  readonly taxonomyVersion: string;
  readonly virtualRoot: "surface";
  readonly aoi: RefinementGeometry | null;
  readonly nodes: readonly RefinementWorkspaceNode[];
}

export interface RefinementLicenseSummary {
  readonly licenseId: string;
  readonly officialUrl: string;
  readonly attribution: string;
  readonly commercialUse: true;
  readonly checkedAt: string;
}

export interface RefinementRemoteAsset {
  readonly assetId: string;
  readonly fileName: string;
  readonly footprint: RefinementGeometry;
  readonly order: number;
  readonly estimatedBytes: number | null;
  readonly checksumAlgorithm: "md5" | "sha256" | null;
  readonly checksumValue: string | null;
  readonly requiresAuthentication: boolean;
  readonly classAttribute: string | null;
}

export interface RefinementProductCandidate {
  readonly candidateId: string;
  readonly providerId: string;
  readonly provider: string;
  readonly product: string;
  readonly version: string;
  readonly datasetIdentifier: string;
  readonly compatibleTlstNodes: readonly string[];
  readonly footprint: RefinementGeometry;
  readonly resolutionM: number;
  readonly temporalStart: string | null;
  readonly temporalEnd: string | null;
  readonly format: string;
  readonly estimatedBytes: number | null;
  readonly availablePercent: number;
  readonly newEffectivePercent: number;
  readonly qualifierKey: string | null;
  readonly endpointVerified: boolean;
  readonly license: RefinementLicenseSummary;
  readonly assets: readonly RefinementRemoteAsset[];
}

export interface RefinementProviderFailure {
  readonly providerId: string;
  readonly code: string;
  readonly message: string;
}

export interface RefinementCoverageSummary {
  readonly existingPercent: number;
  readonly newEffectivePercent: number;
  readonly plannedPercent: number;
  readonly remainingPercent: number;
  readonly existing: RefinementGeometry | null;
  readonly planned: RefinementGeometry | null;
  readonly remaining: RefinementGeometry | null;
  readonly recommendedProductIds: readonly string[];
}

export interface FrozenRefinementAsset extends RefinementRemoteAsset {
  readonly providerId: string;
  readonly product: string;
  readonly version: string;
  readonly downloadUrl: string;
  readonly licenseId: string;
  readonly licenseUrl: string;
  readonly attribution: string;
  readonly provenanceUrl: string;
  readonly classTranslation: Readonly<Record<string, string>>;
  readonly nodataValues: readonly number[];
  readonly qualifierKey: string | null;
}

export interface RefinementDownloadPlan {
  readonly schemaVersion: 4;
  readonly planId: string;
  readonly requestId: string;
  readonly revision: number;
  readonly categoryKeys: readonly string[];
  readonly aoi: RefinementGeometry;
  readonly productIds: readonly string[];
  readonly assets: readonly FrozenRefinementAsset[];
  readonly processingOptions: Readonly<Record<string, string | number | boolean>>;
  readonly estimatedBytes: number | null;
  readonly requiresLargeDownloadConfirmation: boolean;
}

export interface RefinementDerivedOutputs {
  readonly manifest: string | null;
  readonly mosaic: string | null;
  readonly source: string | null;
  readonly quality: string | null;
  readonly conflict: string | null;
}

// Frontend → Python

export interface RequestRefinementWorkspaceMessage {
  readonly type: "request_refinement_workspace";
  readonly requestId: string;
  readonly revision: number;
  readonly aoi?: RefinementGeometry;
}

export interface QueryRefinementProductsMessage {
  readonly type: "query_refinement_products";
  readonly requestId: string;
  readonly revision: number;
  readonly categoryKey: string;
  readonly aoi: RefinementGeometry;
}

export interface CancelRefinementQueryMessage {
  readonly type: "cancel_refinement_query";
  readonly requestId: string;
  readonly revision: number;
}

export interface CalculateRefinementPlanMessage {
  readonly type: "calculate_refinement_plan";
  readonly requestId: string;
  readonly revision: number;
  readonly categoryKey: string;
  readonly aoi: RefinementGeometry;
  readonly productIds: readonly string[];
}

export interface ConfirmRefinementDownloadMessage {
  readonly type: "confirm_refinement_download";
  readonly requestId: string;
  readonly revision: number;
  readonly planId: string;
  readonly largeDownloadConfirmed: boolean;
}

export interface RemoveRefinementInstallationMessage {
  readonly type: "remove_refinement_installation";
  readonly requestId: string;
  readonly revision: number;
  readonly installationId: string;
}

// Python → Frontend

export interface RefinementWorkspaceSnapshotMessage {
  readonly type: "refinement_workspace_snapshot";
  readonly requestId: string;
  readonly revision: number;
  readonly workspace: RefinementWorkspace;
}

export interface RefinementCandidatesMessage {
  readonly type: "refinement_candidates";
  readonly requestId: string;
  readonly revision: number;
  readonly categoryKey: string;
  readonly candidates: readonly RefinementProductCandidate[];
  readonly failures: readonly RefinementProviderFailure[];
}

export interface RefinementPlanSummaryMessage {
  readonly type: "refinement_plan_summary";
  readonly requestId: string;
  readonly revision: number;
  readonly categoryKey: string;
  readonly productIds: readonly string[];
  readonly coverage: RefinementCoverageSummary;
  readonly plan: RefinementDownloadPlan;
}

export interface RefinementDownloadProgressMessage {
  readonly type: "refinement_download_progress";
  readonly requestId: string;
  readonly revision: number;
  readonly planId: string;
  readonly jobId: string;
  readonly state: RefinementTechnicalState;
  readonly downloadedBytes: number;
  readonly totalBytes: number | null;
  readonly progress: number | null;
  readonly currentFile: string | null;
  readonly outputs: RefinementDerivedOutputs;
  readonly error: string | null;
}

export interface RefinementCoverageUpdatedMessage {
  readonly type: "refinement_coverage_updated";
  readonly requestId: string;
  readonly revision: number;
  readonly categoryKey: string;
  readonly installationId: string;
  readonly verifiedPercent: number;
  readonly verifiedGeometry: RefinementGeometry | null;
  readonly outputs: RefinementDerivedOutputs;
}

export interface RefinementInstallationRemovedMessage {
  readonly type: "refinement_installation_removed";
  readonly requestId: string;
  readonly revision: number;
  readonly installationId: string;
}

export interface RefinementOperationErrorMessage {
  readonly type: "refinement_operation_error";
  readonly requestId: string;
  readonly revision: number;
  readonly operation: "workspace" | "query" | "plan" | "confirm" | "remove";
  readonly code: string;
  readonly message: string;
  readonly providerId?: string;
}

export type RefinementFrontendMessage =
  | RequestRefinementWorkspaceMessage
  | QueryRefinementProductsMessage
  | CancelRefinementQueryMessage
  | CalculateRefinementPlanMessage
  | ConfirmRefinementDownloadMessage
  | RemoveRefinementInstallationMessage;

export type RefinementBackendMessage =
  | RefinementWorkspaceSnapshotMessage
  | RefinementCandidatesMessage
  | RefinementPlanSummaryMessage
  | RefinementDownloadProgressMessage
  | RefinementCoverageUpdatedMessage
  | RefinementInstallationRemovedMessage
  | RefinementOperationErrorMessage;
