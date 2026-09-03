import type { WebSocketBridge } from "../bridge/WebSocketBridge";
import type { 
    ResourceCatalogSnapshotMessage, 
    DownloadJobSnapshotMessage 
} from "../contracts/bridge_messages";
import type { 
    ResourceDescriptor, 
    ResourceInstallState 
} from "../contracts/resource_manager_contracts";

export interface ResourceState {
    status: ResourceInstallState;
    variantId: string | null;
    downloadedBytes: number;
    verifiedAt: string | null;
    error: string | null;
    manifestData: Record<string, string | number | boolean> | null;
}

export type CatalogUpdateListener = () => void;
export type JobUpdateListener = (jobSnapshot: DownloadJobSnapshotMessage) => void;

export class ResourceManager {
    private descriptors: Map<string, ResourceDescriptor> = new Map();
    private installedStates: Map<string, ResourceState> = new Map();
    private jobStates: Map<string, DownloadJobSnapshotMessage> = new Map();

    private catalogListeners: Set<CatalogUpdateListener> = new Set();
    private jobListeners: Set<JobUpdateListener> = new Set();

    constructor(private bridge: WebSocketBridge) {
        bridge.addMessageListener({
            onResourceCatalogSnapshot: (msg) => this.handleCatalogSnapshot(msg),
            onDownloadJobSnapshot: (msg) => this.handleJobSnapshot(msg)
        });
    }

    public requestCatalog(): void {
        this.bridge.requestCatalogSnapshot();
    }

    public startDownload(resourceId: string, variantId: string): void {
        this.bridge.requestResourceDownload(resourceId, variantId);
        this.optimisticUpdate(resourceId, variantId, "DOWNLOADING");
    }

    public pauseDownload(resourceId: string, variantId: string): void {
        this.bridge.pauseDownload(resourceId, variantId);
        this.optimisticUpdate(resourceId, variantId, "PAUSED");
    }

    public cancelDownload(resourceId: string, variantId: string): void {
        this.bridge.cancelDownload(resourceId, variantId);
        this.optimisticUpdate(resourceId, variantId, "NOT_INSTALLED");
    }

    public deleteResource(resourceId: string, variantId: string): void {
        this.bridge.deleteResource(resourceId, variantId);
        this.optimisticUpdate(resourceId, variantId, "NOT_INSTALLED");
    }

    public getDescriptor(resourceId: string): ResourceDescriptor | undefined {
        return this.descriptors.get(resourceId);
    }

    public getAllDescriptors(): ResourceDescriptor[] {
        return Array.from(this.descriptors.values());
    }

    public getInstallState(resourceId: string, variantId: string): ResourceState {
        const key = `${resourceId}::${variantId}`;
        return this.installedStates.get(key) || {
            status: "NOT_INSTALLED",
            variantId: variantId,
            downloadedBytes: 0,
            verifiedAt: null,
            error: null,
            manifestData: null,
        };
    }

    public getEffectiveInstallState(resourceId: string, preferredVariantId?: string): ResourceState {
        if (preferredVariantId) {
            return this.getInstallState(resourceId, preferredVariantId);
        }

        const descriptor = this.getDescriptor(resourceId);
        const variantStates = descriptor?.variants.map(
            (variant) => this.getInstallState(resourceId, variant.id),
        ) ?? [];

        return variantStates.find((state) => state.status === "READY")
            ?? variantStates.find((state) => state.status !== "NOT_INSTALLED")
            ?? variantStates[0]
            ?? {
                status: "NOT_INSTALLED",
                variantId: null,
                downloadedBytes: 0,
                verifiedAt: null,
                error: null,
                manifestData: null,
            };
    }

    public getJobState(jobId: string): DownloadJobSnapshotMessage | undefined {
        return this.jobStates.get(jobId);
    }

    public subscribeCatalog(listener: CatalogUpdateListener): () => void {
        this.catalogListeners.add(listener);
        return () => this.catalogListeners.delete(listener);
    }

    public subscribeJobs(listener: JobUpdateListener): () => void {
        this.jobListeners.add(listener);
        return () => this.jobListeners.delete(listener);
    }

    private handleCatalogSnapshot(msg: ResourceCatalogSnapshotMessage): void {
        this.descriptors.clear();
        for (const desc of msg.descriptors) {
            this.descriptors.set(desc.id, desc);
        }
        
        this.installedStates.clear();
        for (const [resId, state] of Object.entries(msg.installedStates)) {
            this.installedStates.set(resId, state);
        }

        for (const l of this.catalogListeners) l();
    }

    private handleJobSnapshot(msg: DownloadJobSnapshotMessage): void {
        this.jobStates.set(msg.jobId, msg);
        
        // Optimistic update of local installed state
        if (msg.variantId) {
            const key = `${msg.resourceId}::${msg.variantId}`;
            const current = this.getInstallState(msg.resourceId, msg.variantId);
            this.installedStates.set(key, {
                ...current,
                status: msg.state,
                variantId: msg.variantId,
                downloadedBytes: msg.downloadedBytes
            });
        }
        
        for (const l of this.jobListeners) l(msg);
        for (const l of this.catalogListeners) l(); // Notify UI to refresh rows
    }

    private optimisticUpdate(resourceId: string, variantId: string, status: ResourceInstallState): void {
        const key = `${resourceId}::${variantId}`;
        const current = this.getInstallState(resourceId, variantId);
        
        this.installedStates.set(key, {
            ...current,
            status,
            variantId
        });
        
        const jobId = `${resourceId}_${variantId}`;
        const existingJob = this.jobStates.get(jobId);
        
        const newJob: DownloadJobSnapshotMessage = existingJob ? {
            ...existingJob,
            state: status
        } : {
            type: "download_job_snapshot",
            jobId,
            resourceId,
            variantId,
            state: status,
            downloadedBytes: current.downloadedBytes || 0,
            totalBytes: null,
            progress: null,
            currentFile: null,
            errorCode: null,
            errorMessage: null
        };
        
        this.jobStates.set(jobId, newJob);
        
        for (const l of this.jobListeners) l(newJob);
        for (const l of this.catalogListeners) l();
    }
}
