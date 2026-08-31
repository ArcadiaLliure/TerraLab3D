import type { WebSocketBridge } from "../bridge/WebSocketBridge";
import type { 
    ResourceCatalogSnapshotMessage, 
    DownloadJobSnapshotMessage 
} from "../contracts/bridge_messages";
import type { OperationProgressedEvent } from "../contracts/events";
import type { 
    ResourceDescriptor, 
    ResourceInstallState 
} from "../contracts/resource_manager_contracts";
import type {
    RefinementBackendMessage,
    RefinementDownloadProgressMessage,
    RefinementGeometry,
    RefinementWorkspace,
} from "../contracts/refinement_contracts";

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
export type OperationProgressListener = (event: OperationProgressedEvent) => void;
export type RefinementUpdateListener = (event: RefinementBackendMessage) => void;

export class ResourceManager {
    private descriptors: Map<string, ResourceDescriptor> = new Map();
    private installedStates: Map<string, ResourceState> = new Map();
    private jobStates: Map<string, DownloadJobSnapshotMessage> = new Map();

    private catalogListeners: Set<CatalogUpdateListener> = new Set();
    private jobListeners: Set<JobUpdateListener> = new Set();
    private operationListeners: Set<OperationProgressListener> = new Set();
    private refinementListeners: Set<RefinementUpdateListener> = new Set();
    private refinementWorkspace: RefinementWorkspace | null = null;
    private refinementJobs: Map<string, RefinementDownloadProgressMessage> = new Map();

    constructor(private bridge: WebSocketBridge) {
        bridge.addMessageListener({
            onResourceCatalogSnapshot: (msg) => this.handleCatalogSnapshot(msg),
            onDownloadJobSnapshot: (msg) => this.handleJobSnapshot(msg),
            onOperationProgressed: (msg) => this.handleOperationProgressed(msg),
            onRefinementWorkspaceSnapshot: (msg) => {
                this.refinementWorkspace = msg.workspace;
                this.publishRefinement(msg);
            },
            onRefinementCandidates: (msg) => this.publishRefinement(msg),
            onRefinementPlanSummary: (msg) => this.publishRefinement(msg),
            onRefinementDownloadProgress: (msg) => this.publishRefinement(msg),
            onRefinementCoverageUpdated: (msg) => this.publishRefinement(msg),
            onRefinementInstallationRemoved: (msg) => this.publishRefinement(msg),
            onRefinementOperationError: (msg) => this.publishRefinement(msg),
            onCdseAuthRequired: () => this.handleCdseAuthRequired(),
        });
    }

    private async handleCdseAuthRequired(): Promise<void> {
        console.warn("MGP: [ResourceManager] Received cdse_auth_required! Launching CdseLoginDialog");
        // Dynamically import to avoid circular dependencies
        const { CdseLoginDialog } = await import("../view/ui/modals/CdseLoginDialog");
        const dialog = new CdseLoginDialog();
        const result = await dialog.prompt();
        if (result.action === "submit") {
            this.bridge.sendSubmitCdseCredentials({
                username: result.username,
                password: result.password,
                totp: result.totp,
                remember: result.remember,
            });
        } else if (result.action === "forget") {
            this.bridge.sendForgetCdseCredentials();
            // Also submit cancel to resume any pending Future with False
            this.bridge.sendSubmitCdseCredentials({ username: "", password: "", remember: false });
        } else {
            // Cancel
            this.bridge.sendSubmitCdseCredentials({ username: "", password: "", remember: false });
        }
    }

    public requestCatalog(): void {
        this.bridge.requestCatalogSnapshot();
    }

    public getRefinementWorkspace(): RefinementWorkspace | null {
        return this.refinementWorkspace;
    }

    public requestRefinementWorkspace(requestId: string, revision: number, aoi?: RefinementGeometry): void {
        this.bridge.requestRefinementWorkspace({
            type: "request_refinement_workspace",
            requestId,
            revision,
            ...(aoi ? { aoi } : {}),
        });
    }

    public queryRefinementProducts(
        requestId: string,
        revision: number,
        categoryKey: string,
        aoi: RefinementGeometry,
    ): void {
        this.bridge.queryRefinementProducts({
            type: "query_refinement_products", requestId, revision, categoryKey, aoi,
        });
    }

    public cancelRefinementQuery(requestId: string, revision: number): void {
        this.bridge.cancelRefinementQuery({ type: "cancel_refinement_query", requestId, revision });
    }

    public calculateRefinementPlan(
        requestId: string,
        revision: number,
        categoryKey: string,
        aoi: RefinementGeometry,
        productIds: readonly string[],
    ): void {
        this.bridge.calculateRefinementPlan({
            type: "calculate_refinement_plan", requestId, revision, categoryKey, aoi, productIds,
        });
    }

    public confirmRefinementDownload(
        requestId: string,
        revision: number,
        planId: string,
        largeDownloadConfirmed: boolean,
    ): void {
        this.bridge.confirmRefinementDownload({
            type: "confirm_refinement_download",
            requestId,
            revision,
            planId,
            largeDownloadConfirmed,
        });
    }

    public cancelRefinementDownload(
        requestId: string,
        revision: number,
        planId: string,
    ): void {
        this.bridge.cancelRefinementDownload({
            type: "cancel_refinement_download", requestId, revision, planId,
        });
    }

    public removeRefinementInstallation(
        requestId: string,
        revision: number,
        installationId: string,
    ): void {
        this.bridge.removeRefinementInstallation({
            type: "remove_refinement_installation", requestId, revision, installationId,
        });
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

    public subscribeOperationProgress(listener: OperationProgressListener): () => void {
        this.operationListeners.add(listener);
        return () => this.operationListeners.delete(listener);
    }

    public subscribeRefinement(listener: RefinementUpdateListener): () => void {
        this.refinementListeners.add(listener);
        return () => this.refinementListeners.delete(listener);
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
        const refinement = this.refinementJobs.get(msg.jobId);
        const state = refinementTechnicalState(msg.state);
        if (refinement && state) {
            const progress: RefinementDownloadProgressMessage = {
                ...refinement,
                state,
                downloadedBytes: msg.downloadedBytes,
                totalBytes: msg.totalBytes,
                progress: msg.progress,
                currentFile: msg.currentFile,
                error: msg.errorMessage,
                assetProgress: msg.assetProgress,
            };
            this.publishRefinement(progress);
            if (state === "READY") {
                this.bridge.requestRefinementWorkspace({
                    type: "request_refinement_workspace",
                    requestId: progress.requestId,
                    revision: progress.revision,
                    ...(this.refinementWorkspace?.aoi ? { aoi: this.refinementWorkspace.aoi } : {}),
                });
            }
            if (state === "READY" || state === "ERROR" || state === "CANCELLED") {
                this.refinementJobs.delete(msg.jobId);
            }
        }
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
            errorMessage: null,
            assetProgress: [],
        };
        
        this.jobStates.set(jobId, newJob);
        
        for (const l of this.jobListeners) l(newJob);
        for (const l of this.catalogListeners) l();
    }

    private handleOperationProgressed(msg: OperationProgressedEvent): void {
        for (const l of this.operationListeners) l(msg);
    }

    private publishRefinement(msg: RefinementBackendMessage): void {
        if (msg.type === "refinement_download_progress") {
            if (msg.state === "QUEUED" || msg.state === "AUTHENTICATING" || msg.state === "DOWNLOADING") {
                this.refinementJobs.set(msg.jobId, msg);
            } else if (msg.state === "READY" || msg.state === "ERROR" || msg.state === "CANCELLED") {
                this.refinementJobs.delete(msg.jobId);
            }
        }
        for (const listener of this.refinementListeners) listener(msg);
    }
}

function refinementTechnicalState(state: ResourceInstallState): RefinementDownloadProgressMessage["state"] | null {
    if (state === "QUEUED" || state === "AUTHENTICATING" || state === "DOWNLOADING" || state === "VERIFYING" || state === "PROCESSING" || state === "READY" || state === "ERROR") {
        return state;
    }
    if (state === "INVALID") return "ERROR";
    if (state === "PARTIAL" || state === "PAUSED" || state === "NOT_INSTALLED") return "CANCELLED";
    return null;
}
