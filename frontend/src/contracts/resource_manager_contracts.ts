export type ResourceInstallState =
    | "NOT_INSTALLED"
    | "PARTIAL"
    | "QUEUED"
    | "AUTHENTICATING"
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
    sourceUrls?: string[] | null;
    format?: string | null;
    mimeType?: string | null;
    width?: number | null;
    height?: number | null;
    publishedSizeLabel?: string | null;
    expectedBytes?: number | null;
    metadata: Record<string, string | number | boolean>;
}

export type ResourceDomain = "sky" | "earth";

export type ResourceCategory = 
    | "solar_system" 
    | "deep_sky" 
    | "elevation" 
    | "land_cover" 
    | "light_pollution";


export interface ResourceDescriptor {
    id: string;
    name: string;
    description: string;
    domain: ResourceDomain;
    category: ResourceCategory;
    provider: string;
    acquisitionKind: AcquisitionKind;
    citation: string;
    license: string;
    originalSourceUrl?: string | null;
    directUrl?: string | null;
    variants: ResourceVariant[];
    credits: string[];
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
    assetProgress: readonly DownloadAssetProgress[];
}

export interface DownloadAssetProgress {
    fileName: string;
    downloadedBytes: number;
    totalBytes: number | null;
}
