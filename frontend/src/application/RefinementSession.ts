import type {
  RefinementBackendMessage,
  RefinementDownloadProgressMessage,
  RefinementGeometry,
  RefinementPlanSummaryMessage,
  RefinementProductCandidate,
  RefinementProviderFailure,
  RefinementWorkspace,
  RefinementWorkspaceNode,
} from "../contracts/refinement_contracts";

export interface RefinementTreeNode extends RefinementWorkspaceNode {
  readonly children: readonly RefinementTreeNode[];
}

export interface RefinementSessionSnapshot {
  readonly requestId: string;
  readonly revision: number;
  readonly aoi: RefinementGeometry | null;
  readonly selectedCategoryKey: string | null;
  readonly workspace: RefinementWorkspace | null;
  readonly candidates: readonly RefinementProductCandidate[];
  readonly failures: readonly RefinementProviderFailure[];
  readonly selectedProductIds: ReadonlySet<string>;
  readonly planSummary: RefinementPlanSummaryMessage | null;
  readonly progress: RefinementDownloadProgressMessage | null;
  readonly operationProgress: { fraction: number; message: string } | null;
  readonly busyOperation: "workspace" | "query" | "plan" | "confirm" | "remove" | null;
  readonly error: string | null;
}

type SessionListener = (snapshot: RefinementSessionSnapshot) => void;

/** Revisioned UI state. Late provider replies can never overwrite a newer AOI or selection. */
export class RefinementSession {
  private revision = 0;
  private requestId = "refinement-0";
  private aoi: RefinementGeometry | null = null;
  private selectedCategoryKey: string | null = null;
  private workspace: RefinementWorkspace | null = null;
  private candidates: readonly RefinementProductCandidate[] = [];
  private failures: readonly RefinementProviderFailure[] = [];
  private selectedProductIds = new Set<string>();
  private planSummary: RefinementPlanSummaryMessage | null = null;
  private progress: RefinementDownloadProgressMessage | null = null;
  private operationProgress: { fraction: number; message: string } | null = null;
  private busyOperation: RefinementSessionSnapshot["busyOperation"] = null;
  private error: string | null = null;
  private readonly listeners = new Set<SessionListener>();

  public snapshot(): RefinementSessionSnapshot {
    return {
      requestId: this.requestId,
      revision: this.revision,
      aoi: this.aoi,
      selectedCategoryKey: this.selectedCategoryKey,
      workspace: this.workspace,
      candidates: this.candidates,
      failures: this.failures,
      selectedProductIds: new Set(this.selectedProductIds),
      planSummary: this.planSummary,
      progress: this.progress,
      operationProgress: this.operationProgress,
      busyOperation: this.busyOperation,
      error: this.error,
    };
  }

  public subscribe(listener: SessionListener): () => void {
    this.listeners.add(listener);
    return () => this.listeners.delete(listener);
  }

  public begin(operation: NonNullable<RefinementSessionSnapshot["busyOperation"]>): RefinementSessionSnapshot {
    this.busyOperation = operation;
    this.operationProgress = null;
    this.error = null;
    this.publish();
    return this.snapshot();
  }

  public setAoi(aoi: RefinementGeometry | null): RefinementSessionSnapshot {
    this.aoi = aoi;
    this.advanceRevision();
    this.clearDiscovery();
    this.publish();
    return this.snapshot();
  }

  public selectCategory(categoryKey: string): RefinementSessionSnapshot {
    if (this.selectedCategoryKey !== categoryKey) {
      this.selectedCategoryKey = categoryKey;
      this.advanceRevision();
      this.clearDiscovery();
      this.publish();
    }
    return this.snapshot();
  }

  public setProductSelected(productId: string, selected: boolean): RefinementSessionSnapshot {
    if (selected) this.selectedProductIds.add(productId);
    else this.selectedProductIds.delete(productId);
    this.planSummary = null;
    this.progress = null;
    this.error = null;
    this.publish();
    return this.snapshot();
  }

  public setProductsSelected(productIds: string[], selected: boolean): RefinementSessionSnapshot {
    for (const productId of productIds) {
      if (selected) this.selectedProductIds.add(productId);
      else this.selectedProductIds.delete(productId);
    }
    this.planSummary = null;
    this.progress = null;
    this.error = null;
    this.publish();
    return this.snapshot();
  }

  public accept(message: RefinementBackendMessage): boolean {
    if (message.revision !== this.revision || message.requestId !== this.requestId) return false;
    switch (message.type) {
      case "refinement_workspace_snapshot":
        this.workspace = message.workspace;
        this.busyOperation = null;
        this.operationProgress = null;
        break;
      case "refinement_candidates":
        if (message.categoryKey !== this.selectedCategoryKey) return false;
        this.candidates = message.candidates;
        this.failures = message.failures;
        this.selectedProductIds = new Set(
          message.candidates
            .filter((candidate) => candidate.newEffectivePercent > 0)
            .map((candidate) => candidate.candidateId),
        );
        this.planSummary = null;
        this.busyOperation = null;
        this.operationProgress = null;
        break;
      case "refinement_plan_summary":
        if (message.categoryKey !== this.selectedCategoryKey) return false;
        this.planSummary = message;
        this.busyOperation = null;
        this.operationProgress = null;
        break;
      case "refinement_download_progress":
        this.progress = message;
        this.busyOperation = message.state === "READY" || message.state === "ERROR" || message.state === "CANCELLED"
          ? null
          : "confirm";
        break;
      case "refinement_coverage_updated":
      case "refinement_installation_removed":
        this.busyOperation = null;
        this.operationProgress = null;
        break;
      case "refinement_operation_progress":
        if (message.operation !== this.busyOperation) return false;
        this.operationProgress = { fraction: message.progressFraction, message: message.message };
        break;
      case "refinement_operation_error":
        this.error = message.message;
        this.busyOperation = null;
        this.operationProgress = null;
        break;
    }
    this.publish();
    return true;
  }

  public clearError(): void {
    this.error = null;
    this.publish();
  }

  private advanceRevision(): void {
    this.revision += 1;
    this.requestId = `refinement-${Date.now().toString(36)}-${this.revision}`;
    this.busyOperation = null;
    this.operationProgress = null;
    this.error = null;
  }

  private clearDiscovery(): void {
    this.candidates = [];
    this.failures = [];
    this.selectedProductIds.clear();
    this.planSummary = null;
    this.progress = null;
    this.operationProgress = null;
  }

  private publish(): void {
    const snapshot = this.snapshot();
    for (const listener of this.listeners) listener(snapshot);
  }
}

export function buildRefinementTree(nodes: readonly RefinementWorkspaceNode[]): readonly RefinementTreeNode[] {
  const childrenByParent = new Map<string | null, RefinementWorkspaceNode[]>();
  for (const node of nodes) {
    const siblings = childrenByParent.get(node.parentKey) ?? [];
    siblings.push(node);
    childrenByParent.set(node.parentKey, siblings);
  }
  const build = (node: RefinementWorkspaceNode): RefinementTreeNode => ({
    ...node,
    children: (childrenByParent.get(node.categoryKey) ?? []).map(build),
  });
  return (childrenByParent.get("surface") ?? childrenByParent.get(null) ?? []).map(build);
}

