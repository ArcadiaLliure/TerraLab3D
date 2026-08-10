export type ResourceInstallState =
    | "NOT_INSTALLED"
    | "PARTIAL"
    | "QUEUED"
    | "DOWNLOADING"
    | "PAUSED"
    | "VERIFYING"
    | "PROCESSING"
    | "READY"
    | "INVALID"
    | "UPDATE_AVAILABLE"
    | "ERROR";

export type AcquisitionKind =
    | "STATIC_FILE"
    | "HTTP_BUNDLE"
    | "TAP_QUERY"
    | "GENERATED_DATASET"
    | "PARAMETRIC_DOWNLOAD"
    | "EXTERNAL_FILE";

export interface ResourceVariant {
    id: string;
    title: string;
    sourceUrl?: string | null;
    format?: string | null;
    mimeType?: string | null;
    width?: number | null;
    height?: number | null;
    publishedSizeLabel?: string | null;
    expectedBytes?: number | null;
    metadata: Record<string, string | number | boolean>;
}

export interface ResourceDescriptor {
    id: string;
    title: string;
    provider: string;
    acquisitionKind: AcquisitionKind;
    sourcePageUrl?: string | null;
    variants: ResourceVariant[];
    credits: string[];
    license?: string | null;
    dependencies: string[];
    metadata: Record<string, string | number | boolean>;
}

export interface DownloadJobSnapshot {
    jobId: string;
    resourceId: string;
    variantId: string | null;
    state: ResourceInstallState;
    downloadedBytes: number;
    totalBytes: number | null;
    progress: number | null;
    currentFile: string | null;
    errorCode: string | null;
    errorMessage: string | null;
}
