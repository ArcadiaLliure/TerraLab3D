import type { ResourceManager } from "../../../application/ResourceManager";
import {
  buildRefinementTree,
  RefinementSession,
  type RefinementSessionSnapshot,
  type RefinementTreeNode,
} from "../../../application/RefinementSession";
import type {
  RefinementDownloadPlan,
  RefinementProductCandidate,
  RefinementWorkspaceNode,
} from "../../../contracts/refinement_contracts";
import { RefinementMapView } from "./RefinementMapView";

export interface RefinementManagerCallbacks {
  readonly onImportRequested: (categoryKey: string) => void;
}

export interface RefinementRenderImpact {
  readonly tree: boolean;
  readonly products: boolean;
  readonly mapAoi: boolean;
  readonly mapCandidates: boolean;
  readonly mapCoverage: boolean;
}

/** Identify which stable UI regions actually changed between session publications. */
export function refinementRenderImpact(
  previous: RefinementSessionSnapshot | null,
  next: RefinementSessionSnapshot,
): RefinementRenderImpact {
  if (!previous) {
    return { tree: true, products: true, mapAoi: true, mapCandidates: true, mapCoverage: true };
  }
  const selectionChanged = !sameStringSet(previous.selectedProductIds, next.selectedProductIds);
  return {
    tree: previous.workspace !== next.workspace
      || previous.selectedCategoryKey !== next.selectedCategoryKey,
    products: previous.workspace !== next.workspace
      || previous.selectedCategoryKey !== next.selectedCategoryKey
      || previous.candidates !== next.candidates
      || previous.failures !== next.failures
      || selectionChanged,
    mapAoi: previous.aoi !== next.aoi,
    mapCandidates: previous.candidates !== next.candidates || selectionChanged,
    mapCoverage: previous.planSummary !== next.planSummary,
  };
}

/** Full TLST refinement capability hosted by the existing resource modal. */
export class RefinementManagerView {
  public readonly element = document.createElement("div");
  private readonly session = new RefinementSession();
  private readonly mapView: RefinementMapView;
  private readonly treePanel = document.createElement("section");
  private readonly productPanel = document.createElement("section");
  private readonly columns = document.createElement("div");
  private readonly statusRegion = document.createElement("div");
  private readonly unsubscribeManager: () => void;
  private readonly unsubscribeSession: () => void;
  private readonly layoutObserver: ResizeObserver;
  private readonly expandedKeys = new Set<string>(["artificial", "agriculture", "tree_cover"]);
  private planTimer: ReturnType<typeof setTimeout> | null = null;
  private groupByDataset = true;
  private renderedSnapshot: RefinementSessionSnapshot | null = null;
  private renderedListCandidates: RefinementSessionSnapshot["candidates"] | null = null;
  private renderedListWorkspace: RefinementSessionSnapshot["workspace"] = null;
  private renderedListCategory: string | null = null;
  private renderedListSelection = "";
  private renderedListGrouped = true;
  private renderedPlanSummary: RefinementSessionSnapshot["planSummary"] = null;
  private opened = false;
  private disposed = false;

  constructor(
    private readonly manager: ResourceManager,
    private readonly callbacks: RefinementManagerCallbacks,
  ) {
    this.element.className = "refinement-manager";
    this.element.style.cssText = "display:flex;flex-direction:row;gap:16px;min-height:0;height:100%;color:var(--color-text,#e5e7eb);overflow:hidden";
    this.mapView = new RefinementMapView((aoi) => this.changeAoi(aoi));
    this.treePanel.style.cssText = panelStyle();
    this.treePanel.setAttribute("aria-label", "Jerarquia TLST");
    this.productPanel.style.cssText = panelStyle();
    this.productPanel.setAttribute("aria-label", "Productes de refinament");
    this.statusRegion.setAttribute("role", "status");
    this.statusRegion.setAttribute("aria-live", "polite");
    this.statusRegion.style.cssText = "min-height:18px;font-size:11px;color:var(--color-text-dim,#b6c0ca)";

    const legend = document.createElement("div");
    legend.style.cssText = "display:flex;flex-wrap:wrap;gap:12px;font-size:10px;color:var(--color-text-dim,#b6c0ca)";
    for (const [color, label] of [
      ["#22d3ee", "Disponibilitat seleccionada"],
      ["#4ade80", "Cobertura local verificada"],
      ["#facc15", "Cobertura nova efectiva"],
      ["#f87171", "Buit restant"],
      ["#fbbf24", "AOI"],
    ] as const) legend.appendChild(legendItem(color, label));

    const leftCol = document.createElement("div");
    leftCol.className = "refinement-left";
    leftCol.style.cssText = "display:flex;flex-direction:column;gap:8px;min-height:0;flex:1.2";
    leftCol.append(this.mapView.element, legend, this.statusRegion);

    this.columns.className = "refinement-columns";
    this.columns.style.cssText = "display:grid;grid-template-columns:minmax(250px,.8fr) minmax(350px,1.2fr);gap:12px;flex:1.8;min-height:0";
    this.columns.append(this.treePanel, this.productPanel);
    this.element.append(leftCol, this.columns);
    this.layoutObserver = new ResizeObserver((entries) => {
      const width = entries[0]?.contentRect.width ?? this.element.clientWidth;
      this.applyResponsiveLayout(width);
    });
    this.layoutObserver.observe(this.element);

    this.unsubscribeManager = manager.subscribeRefinement((message) => {
      if (this.session.accept(message) && (message.type === "refinement_coverage_updated" || message.type === "refinement_installation_removed")) {
        const state = this.session.snapshot();
        this.manager.requestRefinementWorkspace(state.requestId, state.revision, state.aoi ?? undefined);
      }
    });
    this.unsubscribeSession = this.session.subscribe((snapshot) => this.render(snapshot));
    this.render(this.session.snapshot());
  }

  public open(): void {
    if (this.disposed || this.opened) return;
    this.opened = true;
    const snapshot = this.session.begin("workspace");
    this.manager.requestRefinementWorkspace(snapshot.requestId, snapshot.revision, snapshot.aoi ?? undefined);
    queueMicrotask(() => window.dispatchEvent(new Event("resize")));
  }

  public dispose(): void {
    if (this.disposed) return;
    this.disposed = true;
    const snapshot = this.session.snapshot();
    if (snapshot.busyOperation === "query") {
      this.manager.cancelRefinementQuery(snapshot.requestId, snapshot.revision);
    }
    if (this.planTimer) clearTimeout(this.planTimer);
    this.planTimer = null;
    this.unsubscribeSession();
    this.unsubscribeManager();
    this.layoutObserver.disconnect();
    this.mapView.dispose();
    this.element.remove();
  }

  private applyResponsiveLayout(width: number): void {
    const compact = width > 0 && width < 900;
    this.element.style.flexDirection = compact ? "column" : "row";
    this.element.style.overflowY = compact ? "auto" : "hidden";

    this.columns.style.gridTemplateColumns = compact
      ? "minmax(0,1fr)"
      : "minmax(250px,.8fr) minmax(350px,1.2fr)";
    this.treePanel.style.minHeight = compact ? "320px" : "0";
    this.productPanel.style.minHeight = compact ? "360px" : "0";

    this.mapView.element.style.gridTemplateRows = compact
      ? "auto minmax(200px,30vh) auto"
      : "auto minmax(200px,1fr) auto";
    this.mapView.updateSize();
  }

  private changeAoi(aoi: RefinementSessionSnapshot["aoi"]): void {
    const previous = this.session.snapshot();
    if (previous.busyOperation === "query") {
      this.manager.cancelRefinementQuery(previous.requestId, previous.revision);
    }
    const next = this.session.setAoi(aoi);
    if (this.planTimer) clearTimeout(this.planTimer);
    this.planTimer = null;
    const loading = this.session.begin("workspace");
    this.manager.requestRefinementWorkspace(loading.requestId, loading.revision, next.aoi ?? undefined);
  }

  private render(snapshot: RefinementSessionSnapshot): void {
    const impact = refinementRenderImpact(this.renderedSnapshot, snapshot);
    this.renderStatus(snapshot);
    if (impact.tree) this.renderTree(snapshot);
    if (impact.products) this.renderProducts(snapshot);
    else this.updateProductLiveState(snapshot);
    if (impact.mapAoi) this.mapView.setAoi(snapshot.aoi);
    if (impact.mapCandidates) this.mapView.setCandidates(snapshot.candidates, snapshot.selectedProductIds);
    if (impact.mapCoverage || impact.products) {
      const coverage = snapshot.planSummary?.coverage;
      if (coverage) {
        this.mapView.setCoverage(coverage.existing, coverage.planned, coverage.remaining);
      } else {
        this.mapView.setCoverage(null, null, null);
        const node = snapshot.workspace?.nodes.find((item) => item.categoryKey === snapshot.selectedCategoryKey);
        if (node && node.installations.length > 0) {
          this.mapView.setInstalled(node.installations);
        }
      }
    }
    this.renderedSnapshot = snapshot;

    // Auto-calculate plan when candidates arrive "de saque"
    if (
      snapshot.candidates.length > 0 &&
      snapshot.planSummary === null &&
      snapshot.busyOperation === null &&
      !this.planTimer &&
      snapshot.selectedProductIds.size > 0
    ) {
      this.schedulePlan(snapshot);
    }
  }

  private renderStatus(snapshot: RefinementSessionSnapshot): void {
    if (snapshot.error) {
      this.statusRegion.textContent = snapshot.error;
      this.statusRegion.style.color = "var(--color-error,#f87171)";
      return;
    }
    this.statusRegion.style.color = "var(--color-text-dim,#b6c0ca)";
    if (snapshot.busyOperation === "confirm") {
      this.renderDownloadStatus(snapshot);
      return;
    }
    const messages: Record<NonNullable<RefinementSessionSnapshot["busyOperation"]>, string> = {
      workspace: "Calculant l'estat verificat de la jerarquia…",
      query: "Consultant els proveïdors compatibles…",
      plan: "Calculant cobertura efectiva i mosaic…",
      confirm: "Preparant la descàrrega…",
      remove: "Eliminant la instal·lació…",
    };
    if (snapshot.busyOperation) {
      let message = messages[snapshot.busyOperation];
      if (snapshot.operationProgress) {
        message = `${message} (${snapshot.operationProgress.message})`;
      }
      this.statusRegion.replaceChildren(
        document.createTextNode(message),
        this.buildProgressBar(snapshot.operationProgress?.fraction ?? null)
      );
    } else {
      this.statusRegion.textContent = snapshot.aoi
        ? "AOI vàlida en EPSG:4326. Selecciona una categoria aplicable."
        : "Dibuixa o importa una AOI petita per començar; no es fan descàrregues continentals implícites.";
    }
  }

  private renderDownloadStatus(snapshot: RefinementSessionSnapshot): void {
    const progress = snapshot.progress;
    if (!progress) {
      const message = snapshot.operationProgress?.message
        ?? "Sol·licitud enviada; esperant confirmació del backend…";
      this.statusRegion.replaceChildren(
        document.createTextNode(message),
        this.buildProgressBar(null),
      );
      return;
    }

    const fraction = progress.progress === null
      ? null
      : Math.max(0, Math.min(1, progress.progress));
    const percentage = fraction === null ? null : Math.round(fraction * 100);
    const transferred = progress.totalBytes === null
      ? formatBytes(progress.downloadedBytes)
      : `${formatBytes(progress.downloadedBytes)} / ${formatBytes(progress.totalBytes)}`;
    const messages: Record<typeof progress.state, string> = {
      QUEUED: "Descàrrega en cua; encara no s'han rebut dades.",
      AUTHENTICATING: "Esperant l'autenticació de Copernicus; la descàrrega encara no ha començat.",
      DOWNLOADING: percentage === null
        ? `Descarregant ${transferred}; el servidor no ha informat la mida total.`
        : `Descarregant: ${percentage}% · ${transferred}`,
      VERIFYING: "Descàrrega completada; verificant mida i integritat…",
      PROCESSING: "Descàrrega verificada; refinant i generant el mosaic local…",
      READY: "Descàrrega, verificació i refinament completats.",
      ERROR: progress.error ? `La descàrrega ha fallat: ${progress.error}` : "La descàrrega ha fallat.",
      CANCELLED: "Descàrrega cancel·lada; els fitxers parcials es conserven.",
    };
    const children: Node[] = [document.createTextNode(messages[progress.state])];
    if (!["ERROR", "CANCELLED"].includes(progress.state)) {
      children.push(this.buildProgressBar(fraction));
    }
    this.statusRegion.replaceChildren(...children);
  }

  private buildProgressBar(fraction: number | null): HTMLElement {
    const track = document.createElement("div");
    track.setAttribute("role", "progressbar");
    track.setAttribute("aria-valuemin", "0");
    track.setAttribute("aria-valuemax", "100");
    track.style.cssText = "display:inline-block;vertical-align:middle;margin-left:8px;width:100px;height:4px;background:rgba(255,255,255,0.1);border-radius:2px;overflow:hidden;position:relative";
    const bar = document.createElement("div");

    if (fraction !== null) {
      const normalized = Math.max(0, Math.min(1, fraction));
      const percentage = (normalized * 100).toFixed(1);
      track.setAttribute("aria-valuenow", String(Math.round(normalized * 100)));
      bar.style.cssText = `position:absolute;top:0;left:0;bottom:0;width:${percentage}%;background:#facc15;border-radius:2px;transition:width 100ms linear`;
    } else {
      bar.style.cssText = "position:absolute;top:0;left:0;bottom:0;width:30%;background:var(--color-primary,#3b82f6);border-radius:2px;animation:refinement-indeterminate 1.5s infinite linear";
      if (!document.getElementById("refinement-indeterminate-style")) {
        const style = document.createElement("style");
        style.id = "refinement-indeterminate-style";
        style.textContent = `@keyframes refinement-indeterminate { 0% { left: -30%; } 100% { left: 100%; } }`;
        document.head.appendChild(style);
      }
    }

    track.appendChild(bar);
    return track;
  }

  private renderTree(snapshot: RefinementSessionSnapshot): void {
    const existingTree = this.treePanel.querySelector('[role="tree"]') as HTMLDivElement | null;
    const scrollPos = existingTree ? existingTree.scrollTop : 0;

    this.treePanel.replaceChildren();
    const header = panelHeader("Jerarquia canònica TLST", snapshot.workspace
      ? `${snapshot.workspace.taxonomyKey} ${snapshot.workspace.taxonomyVersion}`
      : "Carregant…");
    this.treePanel.appendChild(header);
    if (!snapshot.workspace) return;

    const tree = document.createElement("div");
    tree.setAttribute("role", "tree");
    tree.ariaLabel = "Categories de superfície TLST";
    tree.style.cssText = "overflow:auto;min-height:0;flex:1;padding-right:4px";
    for (const root of buildRefinementTree(snapshot.workspace.nodes)) {
      tree.appendChild(this.treeItem(root, snapshot, 1));
    }
    this.treePanel.appendChild(tree);
    tree.scrollTop = scrollPos;
  }

  private treeItem(node: RefinementTreeNode, snapshot: RefinementSessionSnapshot, level: number): HTMLElement {
    const wrapper = document.createElement("div");
    const row = document.createElement("div");
    row.setAttribute("role", "treeitem");
    row.setAttribute("aria-level", String(level));
    row.setAttribute("aria-selected", String(snapshot.selectedCategoryKey === node.categoryKey));
    if (node.children.length) row.setAttribute("aria-expanded", String(this.expandedKeys.has(node.categoryKey)));
    row.tabIndex = snapshot.selectedCategoryKey === node.categoryKey ? 0 : -1;
    row.style.cssText = `display:grid;grid-template-columns:18px 14px minmax(0,1fr) auto;gap:4px;align-items:center;min-height:28px;padding:2px 6px 2px ${Math.max(0, level - 1) * 14 + 4}px;border-radius:4px;cursor:pointer;background:${snapshot.selectedCategoryKey === node.categoryKey ? "var(--color-surface-hover,#2a3440)" : "transparent"}`;

    const expander = document.createElement("button");
    expander.type = "button";
    expander.textContent = node.children.length ? (this.expandedKeys.has(node.categoryKey) ? "▾" : "▸") : "";
    expander.ariaLabel = node.children.length ? `Expandir o plegar ${node.label}` : "Sense subcategories";
    expander.style.cssText = treeControlStyle();
    expander.onclick = (event) => {
      event.stopPropagation();
      this.toggleExpanded(node.categoryKey);
    };
    const state = document.createElement("span");
    state.textContent = stateGlyph(node.state);
    state.title = stateLabel(node.state);
    state.style.color = stateColor(node.state);
    const label = document.createElement("span");
    label.textContent = node.label;
    label.title = node.categoryKey;
    label.style.cssText = "overflow:hidden;text-overflow:ellipsis;white-space:nowrap;font-size:11px";
    const stateLabelText = node.state === "complete" ? "Completa" : node.state === "partial" ? "Parcial" : node.state === "absent" ? "Buit" : "—";
    const percent = document.createElement("span");
    percent.textContent = stateLabelText;
    percent.style.cssText = "font:10px var(--font-family-sans,sans-serif);color:var(--color-text-dim,#b6c0ca)";
    row.append(expander, state, label, percent);
    row.onclick = () => this.session.selectCategory(node.categoryKey);
    row.onkeydown = (event) => this.handleTreeKey(event, node, row);
    wrapper.appendChild(row);

    if (node.children.length && this.expandedKeys.has(node.categoryKey)) {
      const group = document.createElement("div");
      group.setAttribute("role", "group");
      for (const child of node.children) group.appendChild(this.treeItem(child, snapshot, level + 1));
      wrapper.appendChild(group);
    }
    return wrapper;
  }

  private handleTreeKey(event: KeyboardEvent, node: RefinementTreeNode, row: HTMLElement): void {
    const items = Array.from(this.treePanel.querySelectorAll<HTMLElement>("[role=treeitem]"));
    const index = items.indexOf(row);
    let treeChanged = false;
    if (event.key === "ArrowDown" && items[index + 1]) items[index + 1]!.focus();
    else if (event.key === "ArrowUp" && items[index - 1]) items[index - 1]!.focus();
    else if (event.key === "ArrowRight" && node.children.length) {
      const size = this.expandedKeys.size;
      this.expandedKeys.add(node.categoryKey);
      treeChanged = this.expandedKeys.size !== size;
    }
    else if (event.key === "ArrowLeft" && node.children.length) treeChanged = this.expandedKeys.delete(node.categoryKey);
    else if (event.key === "Enter" || event.key === " ") this.session.selectCategory(node.categoryKey);
    else return;
    event.preventDefault();
    if (treeChanged) this.renderTree(this.session.snapshot());
  }

  private toggleExpanded(categoryKey: string): void {
    if (this.expandedKeys.has(categoryKey)) this.expandedKeys.delete(categoryKey);
    else this.expandedKeys.add(categoryKey);
    this.renderTree(this.session.snapshot());
  }

  private renderProducts(snapshot: RefinementSessionSnapshot): void {
    const existingList = this.productPanel.querySelector('[data-id="product-list"]') as HTMLDivElement | null;
    const scrollPos = existingList ? existingList.scrollTop : 0;

    existingList?.remove();

    this.productPanel.replaceChildren();
    const node = snapshot.workspace?.nodes.find((item) => item.categoryKey === snapshot.selectedCategoryKey) ?? null;
    this.productPanel.appendChild(panelHeader(node?.label ?? "Productes i cobertura", node?.categoryKey ?? "Selecciona una categoria"));
    if (!node) {
      this.productPanel.appendChild(note("Selecciona un node de la jerarquia per veure les accions disponibles."));
      return;
    }

    const actions = document.createElement("div");
    actions.style.cssText = "display:flex;flex-wrap:wrap;gap:8px";
    const importButton = actionButton("Importar raster", false);
    importButton.onclick = () => this.callbacks.onImportRequested(node.categoryKey);
    const discoverButton = actionButton("Cercar proveïdors...", true);
    discoverButton.setAttribute("data-id", "discover-products");
    discoverButton.disabled = !node.applicable || !snapshot.aoi || snapshot.busyOperation !== null;
    discoverButton.title = !snapshot.aoi
      ? "Cal definir una AOI"
      : !node.applicable ? "No hi ha cap proveïdor comercialitzable verificat per aquest node" : "Consulta el catàleg remot";
    discoverButton.onclick = () => this.discover(node);
    actions.append(importButton, discoverButton);
    this.productPanel.appendChild(actions);

    const hasCandidates = snapshot.candidates.length > 0;
    const hasInstallations = node.installations.length > 0;

    if (hasCandidates || hasInstallations) {
      const controls = document.createElement("div");
      controls.style.cssText = "display:flex;flex-wrap:wrap;align-items:center;justify-content:space-between;gap:8px;padding:8px;background:rgba(255,255,255,0.02);border-radius:5px;font-size:11px";

      const totalCoverage = snapshot.planSummary?.coverage.plannedPercent.toFixed(1) ?? "—";
      const totalLabel = document.createElement("strong");
      totalLabel.setAttribute("data-id", "selected-coverage");
      totalLabel.textContent = hasCandidates 
        ? `Cobertura local: ${node.verifiedPercent.toFixed(1)}% | Seleccionada: ${totalCoverage}%`
        : `Cobertura local: ${node.verifiedPercent.toFixed(1)}%`;
      totalLabel.style.color = "#4ade80";

      const actionsGroup = document.createElement("div");
      actionsGroup.style.cssText = "display:flex;align-items:center;gap:8px";

      const selectAll = document.createElement("button");
      selectAll.textContent = "Seleccionar tot";
      selectAll.style.cssText = "background:none;border:none;color:#22d3ee;cursor:pointer;text-decoration:underline";
      selectAll.onclick = () => {
        const next = this.session.setProductsSelected(snapshot.candidates.map(c => c.candidateId), true);
        this.schedulePlan(next);
      };

      const selectNone = document.createElement("button");
      selectNone.textContent = "Netejar";
      selectNone.style.cssText = "background:none;border:none;color:#f87171;cursor:pointer;text-decoration:underline";
      selectNone.onclick = () => {
        const next = this.session.setProductsSelected(snapshot.candidates.map(c => c.candidateId), false);
        this.schedulePlan(next);
      };

      const groupLabel = document.createElement("label");
      groupLabel.style.cssText = "display:flex;align-items:center;gap:4px;cursor:pointer;color:var(--color-text-dim,#b6c0ca)";
      const groupToggle = document.createElement("input");
      groupToggle.type = "checkbox";
      groupToggle.checked = this.groupByDataset;
      groupToggle.onchange = () => {
        this.groupByDataset = groupToggle.checked;
        this.renderProducts(this.session.snapshot());
      };
      groupLabel.append(groupToggle, document.createTextNode("Agrupar per dataset"));

      if (hasCandidates) {
        actionsGroup.append(selectAll, selectNone, document.createTextNode(" | "), groupLabel);
      } else {
        actionsGroup.append(groupLabel);
      }
      controls.append(totalLabel, actionsGroup);
      this.productPanel.appendChild(controls);

      const selectionKey = selectedIdsKey(snapshot.selectedProductIds);
      const canReuseList = existingList !== null
        && this.renderedListCandidates === snapshot.candidates
        && this.renderedListWorkspace === snapshot.workspace
        && this.renderedListCategory === snapshot.selectedCategoryKey
        && this.renderedListSelection === selectionKey
        && this.renderedListGrouped === this.groupByDataset;
      const list = existingList ?? document.createElement("div");
      list.setAttribute("data-id", "product-list");
      list.style.cssText = "display:flex;flex-direction:column;gap:8px;overflow-y:auto;min-height:0;flex:1;padding-right:4px;padding-bottom:4px;";

      if (!canReuseList) {
        const cards: HTMLElement[] = [];
        const candidateKeys = new Set<string>();

        if (hasCandidates) {
          if (this.groupByDataset) {
            const groups = new Map<string, RefinementProductCandidate[]>();
            for (const candidate of snapshot.candidates) {
              const key = `${candidate.provider}|${candidate.product}|${candidate.version}`;
              candidateKeys.add(key);
              if (!groups.has(key)) groups.set(key, []);
              groups.get(key)!.push(candidate);
            }
            for (const group of groups.values()) cards.push(this.productGroupCard(group, snapshot));
          } else {
            for (const candidate of snapshot.candidates) {
              candidateKeys.add(`${candidate.provider}|${candidate.product}|${candidate.version}`);
              cards.push(this.productCard(candidate, snapshot));
            }
          }
        }

        // Add standalone installations not covered by candidates
        if (this.groupByDataset) {
          const standaloneGroups = new Map<
            string,
            Array<RefinementWorkspaceNode['installations'][number]>
          >();
          for (const inst of node.installations) {
            const key = `${inst.provider}|${inst.product}|${inst.version}`;
            if (!candidateKeys.has(key)) {
              if (!standaloneGroups.has(key)) standaloneGroups.set(key, []);
              standaloneGroups.get(key)!.push(inst);
            }
          }
          for (const group of standaloneGroups.values()) {
            cards.push(this.standaloneInstallationGroupCard(group, snapshot));
          }
        } else {
          for (const inst of node.installations) {
            const key = `${inst.provider}|${inst.product}|${inst.version}`;
            if (!candidateKeys.has(key)) {
              cards.push(this.standaloneInstallationCard(inst, snapshot));
            }
          }
        }
        
        list.replaceChildren(...cards);
      }
      this.productPanel.appendChild(list);
      list.scrollTop = scrollPos;
      requestAnimationFrame(() => {
        if (list.isConnected) list.scrollTop = scrollPos;
      });
      this.renderedListCandidates = snapshot.candidates;
      this.renderedListWorkspace = snapshot.workspace;
      this.renderedListCategory = snapshot.selectedCategoryKey;
      this.renderedListSelection = selectionKey;
      this.renderedListGrouped = this.groupByDataset;
    } else if (!snapshot.busyOperation) {
      this.productPanel.appendChild(note(node.applicable
        ? "Consulta els proveïdors per obtenir productes que intersectin l'AOI."
        : "Aquest node continua disponible per importació manual; cap font automàtica aprovada el cobreix encara."));
    }

    for (const failure of snapshot.failures) {
      const warning = note(`${failure.providerId}: ${failure.message}`);
      warning.style.color = "var(--color-warning,#fbbf24)";
      this.productPanel.appendChild(warning);
    }
    const planSlot = document.createElement("div");
    planSlot.setAttribute("data-id", "plan-summary-slot");
    const progressSlot = document.createElement("div");
    progressSlot.setAttribute("data-id", "download-progress-slot");
    this.productPanel.append(planSlot, progressSlot);
    this.updateProductLiveState(snapshot);
  }



  private productGroupCard(candidates: RefinementProductCandidate[], snapshot: RefinementSessionSnapshot): HTMLElement {
    const card = document.createElement("article");
    const firstCandidate = candidates[0];
    if (!firstCandidate) return card;
    card.setAttribute("data-refinement-candidate-ids", JSON.stringify(candidates.map((candidate) => candidate.candidateId)));
    const allSelected = candidates.every(c => snapshot.selectedProductIds.has(c.candidateId));
    const someSelected = candidates.some(c => snapshot.selectedProductIds.has(c.candidateId));
    card.style.cssText = `padding:9px;border:1px solid ${allSelected ? "#22d3ee" : someSelected ? "#3b82f6" : "var(--color-border,#3a4350)"};border-radius:5px;background:var(--color-surface,#141a22)`;

    const heading = document.createElement("label");
    heading.style.cssText = "display:grid;grid-template-columns:auto minmax(0,1fr) auto;gap:8px;align-items:start;cursor:pointer";

    const isInstalled = firstCandidate.installationId !== null;

    let selectorOrAction: HTMLElement;
    if (isInstalled) {
      selectorOrAction = document.createElement("div");
      selectorOrAction.title = "Ja està instal·lat";
      selectorOrAction.innerHTML = `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#4ade80" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M20 6L9 17l-5-5"/></svg>`;
    } else {
      const checkbox = document.createElement("input");
      checkbox.type = "checkbox";
      checkbox.checked = allSelected;
      checkbox.indeterminate = someSelected && !allSelected;
      checkbox.ariaLabel = `Seleccionar dataset ${firstCandidate.product}`;
      checkbox.onchange = () => {
        const ids = candidates.map(c => c.candidateId);
        const next = this.session.setProductsSelected(ids, checkbox.checked);
        this.schedulePlan(next);
      };
      selectorOrAction = checkbox;
    }

    const identity = document.createElement("span");
    identity.style.cssText = "min-width:0";
    const name = document.createElement("strong");
    name.textContent = firstCandidate.product;
    name.style.cssText = "display:block;font-size:11px;font-weight:600;overflow:hidden;text-overflow:ellipsis";
    const provider = document.createElement("span");
    provider.textContent = `${firstCandidate.provider} · ${firstCandidate.version}`;
    provider.style.cssText = "display:block;margin-top:2px;font-size:10px;color:var(--color-text-dim,#b6c0ca)";
    identity.append(name, provider);

    let knownBytes = 0;
    let hasUnknownBytes = false;
    let totalAssets = 0;
    let sumGain = 0;
    let minStart = firstCandidate.temporalStart;
    let maxEnd = firstCandidate.temporalEnd;

    for (const c of candidates) {
      if (c.estimatedBytes === null) hasUnknownBytes = true;
      else knownBytes += c.estimatedBytes;
      totalAssets += c.assets.length;
      sumGain += c.newEffectivePercent;
      if (c.temporalStart !== null && (minStart === null || c.temporalStart < minStart)) minStart = c.temporalStart;
      if (c.temporalEnd !== null && (maxEnd === null || c.temporalEnd > maxEnd)) maxEnd = c.temporalEnd;
    }
    const displayGain = Math.min(sumGain, 100).toFixed(1);

    const gain = document.createElement("span");
    if (isInstalled) {
      gain.textContent = "Instal·lat";
      gain.style.cssText = "font:600 11px var(--font-family-mono,monospace);color:#4ade80;text-align:right";
    } else {
      gain.textContent = `+${displayGain}% (aprox)`;
      gain.title = "Cobertura acumulada màxima si s'importen totes les tessel·les";
      gain.style.cssText = "font:600 11px var(--font-family-mono,monospace);color:#22d3ee;text-align:right";
    }
    heading.append(selectorOrAction, identity, gain);

    const facts = document.createElement("div");
    facts.style.cssText = "display:flex;flex-wrap:wrap;gap:5px 10px;margin:7px 0 0 23px;font-size:9px;color:var(--color-text-muted,#94a3b8)";
    facts.append(
      fact(`${firstCandidate.resolutionM} m`),
      fact(firstCandidate.format),
      fact(hasUnknownBytes ? (knownBytes > 0 ? `> ${formatBytes(knownBytes)}` : "mida pendent") : formatBytes(knownBytes)),
      fact(formatDates(minStart, maxEnd)),
      fact(`${totalAssets} fitxer${totalAssets === 1 ? "" : "s"} en ${candidates.length} target${candidates.length === 1 ? "a" : "es"}`),
    );

    const license = document.createElement("a");
    license.href = firstCandidate.license.officialUrl;
    license.target = "_blank";
    license.rel = "noopener noreferrer";
    license.textContent = `${firstCandidate.license.licenseId} · ús comercial admès`;
    license.title = firstCandidate.license.attribution;
    license.style.cssText = "display:inline-block;margin:6px 0 0 23px;font-size:9px;color:#67e8f9";

    const tags = document.createElement("div");
    if (firstCandidate.compatibleTlstNodes.length > 0) {
      const labels = firstCandidate.compatibleTlstNodes.map(k => snapshot.workspace?.nodes.find(n => n.categoryKey === k)?.label ?? k);
      const displayTags = labels.slice(0, 4).join(", ");
      const more = labels.length > 4 ? ` i ${labels.length - 4} més` : "";
      tags.textContent = `Llegenda: ${displayTags}${more}`;
      tags.title = labels.join(", ");
      tags.style.cssText = "margin:6px 0 0 23px;font-size:9px;color:var(--color-text-muted,#94a3b8);font-style:italic";
    }

    card.append(heading, facts, license);
    if (tags.textContent) card.append(tags);

    if (isInstalled) {
      const removeContainer = document.createElement("div");
      removeContainer.style.cssText = "margin:8px 0 0 23px;display:flex;justify-content:flex-end";
      const removeBtn = document.createElement("button");
      removeBtn.innerHTML = `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 6h18"/><path d="M19 6v14c0 1-1 2-2 2H7c-1 0-2-1-2-2V6"/><path d="M8 6V4c0-1 1-2 2-2h4c1 0 2 1 2 2v2"/><line x1="10" y1="11" x2="10" y2="17"/><line x1="14" y1="11" x2="14" y2="17"/></svg>`;
      removeBtn.title = "Eliminar instal·lació";
      removeBtn.style.cssText = "background:rgba(248,113,113,0.1);border:1px solid rgba(248,113,113,0.3);color:#f87171;padding:4px 8px;border-radius:4px;cursor:pointer;display:flex;align-items:center;justify-content:center;transition:background 0.2s";
      removeBtn.onmouseover = () => { removeBtn.style.background = "rgba(248,113,113,0.2)"; };
      removeBtn.onmouseout = () => { removeBtn.style.background = "rgba(248,113,113,0.1)"; };
      removeBtn.onclick = () => {
        const datasetKey = `${firstCandidate.provider}|${firstCandidate.product}|${firstCandidate.version}`;
        const installedIds = snapshot.workspace?.nodes.find(n => n.categoryKey === snapshot.selectedCategoryKey)?.installations.filter(i => `${i.provider}|${i.product}|${i.version}` === datasetKey).map(i => i.installationId) ?? [];
        const isMultiple = installedIds.length > 1;
        const msg = isMultiple 
          ? `Vols eliminar aquestes ${installedIds.length} instal·lacions de ${firstCandidate.product} i recalcular la cobertura espacial de la base de dades?`
          : `Vols eliminar aquesta instal·lació (${firstCandidate.product}) i recalcular la cobertura espacial de la base de dades?`;
        
        if (!window.confirm(msg)) return;
        this.session.begin("remove");
        if (installedIds.length > 0) {
           for (const id of installedIds) {
             this.manager.removeRefinementInstallation(snapshot.requestId, snapshot.revision, id);
           }
        } else if (firstCandidate.installationId) {
           this.manager.removeRefinementInstallation(snapshot.requestId, snapshot.revision, firstCandidate.installationId);
        }
      };
      removeContainer.appendChild(removeBtn);
      card.appendChild(removeContainer);
    }

    const prog = this.candidateProgress(candidates, snapshot);
    if (prog) card.appendChild(prog);

    return card;
  }

  private productCard(candidate: RefinementProductCandidate, snapshot: RefinementSessionSnapshot): HTMLElement {
    const card = document.createElement("article");
    card.setAttribute("data-refinement-candidate-ids", JSON.stringify([candidate.candidateId]));
    card.style.cssText = `padding:9px;border:1px solid ${snapshot.selectedProductIds.has(candidate.candidateId) ? "#22d3ee" : "var(--color-border,#3a4350)"};border-radius:5px;background:var(--color-surface,#141a22)`;
    const heading = document.createElement("label");
    heading.style.cssText = "display:grid;grid-template-columns:auto minmax(0,1fr) auto;gap:8px;align-items:start;cursor:pointer";
    
    const isInstalled = candidate.installationId !== null;
    let selectorOrAction: HTMLElement;
    if (isInstalled) {
      selectorOrAction = document.createElement("div");
      selectorOrAction.title = "Ja està instal·lat";
      selectorOrAction.innerHTML = `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#4ade80" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M20 6L9 17l-5-5"/></svg>`;
    } else {
      const checkbox = document.createElement("input");
      checkbox.type = "checkbox";
      checkbox.checked = snapshot.selectedProductIds.has(candidate.candidateId);
      checkbox.ariaLabel = `Seleccionar ${candidate.product}`;
      checkbox.onchange = () => {
        const next = this.session.setProductSelected(candidate.candidateId, checkbox.checked);
        this.schedulePlan(next);
      };
      selectorOrAction = checkbox;
    }
    const identity = document.createElement("span");
    identity.style.cssText = "min-width:0";
    const name = document.createElement("strong");
    name.textContent = candidate.product;
    name.style.cssText = "display:block;font-size:11px;font-weight:600;overflow:hidden;text-overflow:ellipsis";
    const provider = document.createElement("span");
    provider.textContent = `${candidate.provider} · ${candidate.version}`;
    provider.style.cssText = "display:block;margin-top:2px;font-size:10px;color:var(--color-text-dim,#b6c0ca)";
    identity.append(name, provider);
    const gain = document.createElement("span");
    if (isInstalled) {
      gain.textContent = "Instal·lat";
      gain.style.cssText = "font:600 11px var(--font-family-mono,monospace);color:#4ade80";
    } else {
      gain.textContent = `+${candidate.newEffectivePercent.toFixed(1)}%`;
      gain.title = `${candidate.availablePercent.toFixed(1)}% disponible dins l'AOI`;
      gain.style.cssText = "font:600 11px var(--font-family-mono,monospace);color:#22d3ee";
    }
    heading.append(selectorOrAction, identity, gain);

    const facts = document.createElement("div");
    facts.style.cssText = "display:flex;flex-wrap:wrap;gap:5px 10px;margin:7px 0 0 23px;font-size:9px;color:var(--color-text-muted,#94a3b8)";
    facts.append(
      fact(`${candidate.resolutionM} m`),
      fact(candidate.format),
      fact(formatBytes(candidate.estimatedBytes)),
      fact(formatDates(candidate.temporalStart, candidate.temporalEnd)),
      fact(`${candidate.assets.length} fitxer${candidate.assets.length === 1 ? "" : "s"}`),
    );
    const license = document.createElement("a");
    license.href = candidate.license.officialUrl;
    license.target = "_blank";
    license.rel = "noopener noreferrer";
    license.textContent = `${candidate.license.licenseId} · ús comercial admès`;
    license.title = candidate.license.attribution;
    license.style.cssText = "display:inline-block;margin:6px 0 0 23px;font-size:9px;color:#67e8f9";

    const tags = document.createElement("div");
    if (candidate.compatibleTlstNodes && candidate.compatibleTlstNodes.length > 0) {
      const labels = candidate.compatibleTlstNodes.map(k => snapshot.workspace?.nodes.find(n => n.categoryKey === k)?.label ?? k);
      const displayTags = labels.slice(0, 4).join(", ");
      const more = labels.length > 4 ? ` i ${labels.length - 4} més` : "";
      tags.textContent = `Llegenda: ${displayTags}${more}`;
      tags.title = labels.join(", ");
      tags.style.cssText = "margin:6px 0 0 23px;font-size:9px;color:var(--color-text-muted,#94a3b8);font-style:italic";
    }

    card.append(heading, facts, license);
    if (tags.textContent) card.append(tags);

    if (isInstalled) {
      const removeContainer = document.createElement("div");
      removeContainer.style.cssText = "margin:8px 0 0 23px;display:flex;justify-content:flex-end";
      const removeBtn = document.createElement("button");
      removeBtn.innerHTML = `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 6h18"/><path d="M19 6v14c0 1-1 2-2 2H7c-1 0-2-1-2-2V6"/><path d="M8 6V4c0-1 1-2 2-2h4c1 0 2 1 2 2v2"/><line x1="10" y1="11" x2="10" y2="17"/><line x1="14" y1="11" x2="14" y2="17"/></svg>`;
      removeBtn.title = "Eliminar instal·lació";
      removeBtn.style.cssText = "background:rgba(248,113,113,0.1);border:1px solid rgba(248,113,113,0.3);color:#f87171;padding:4px 8px;border-radius:4px;cursor:pointer;display:flex;align-items:center;justify-content:center;transition:background 0.2s";
      removeBtn.onmouseover = () => { removeBtn.style.background = "rgba(248,113,113,0.2)"; };
      removeBtn.onmouseout = () => { removeBtn.style.background = "rgba(248,113,113,0.1)"; };
      removeBtn.onclick = () => {
        const datasetKey = `${candidate.provider}|${candidate.product}|${candidate.version}`;
        const installedIds = snapshot.workspace?.nodes.find(n => n.categoryKey === snapshot.selectedCategoryKey)?.installations.filter(i => `${i.provider}|${i.product}|${i.version}` === datasetKey).map(i => i.installationId) ?? [];
        const isMultiple = installedIds.length > 1;
        const msg = isMultiple 
          ? `Vols eliminar aquestes ${installedIds.length} instal·lacions de ${candidate.product} i recalcular la cobertura espacial de la base de dades?`
          : `Vols eliminar aquesta instal·lació (${candidate.product}) i recalcular la cobertura espacial de la base de dades?`;

        if (!window.confirm(msg)) return;
        this.session.begin("remove");
        if (installedIds.length > 0) {
           for (const id of installedIds) {
             this.manager.removeRefinementInstallation(snapshot.requestId, snapshot.revision, id);
           }
        } else if (candidate.installationId) {
           this.manager.removeRefinementInstallation(snapshot.requestId, snapshot.revision, candidate.installationId);
        }
      };
      removeContainer.appendChild(removeBtn);
      card.appendChild(removeContainer);
    }

    const prog = this.candidateProgress([candidate], snapshot);
    if (prog) card.appendChild(prog);

    return card;
  }

  private standaloneInstallationCard(inst: RefinementWorkspaceNode['installations'][0], snapshot: RefinementSessionSnapshot): HTMLElement {
    const card = document.createElement("article");
    card.style.cssText = "padding:9px;border:1px solid rgba(74,222,128,0.3);border-radius:5px;background:rgba(74,222,128,0.05)";

    const heading = document.createElement("label");
    heading.style.cssText = "display:grid;grid-template-columns:auto minmax(0,1fr) auto;gap:8px;align-items:start";

    const icon = document.createElement("div");
    icon.title = "Instal·lació local offline";
    icon.innerHTML = `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#4ade80" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M20 6L9 17l-5-5"/></svg>`;
    
    const identity = document.createElement("span");
    identity.style.cssText = "min-width:0";
    const name = document.createElement("strong");
    name.textContent = inst.product;
    name.style.cssText = "display:block;font-size:11px;font-weight:600;overflow:hidden;text-overflow:ellipsis";
    const provider = document.createElement("span");
    provider.textContent = `${inst.provider} · ${inst.version}`;
    provider.style.cssText = "display:block;margin-top:2px;font-size:10px;color:var(--color-text-dim,#b6c0ca)";
    identity.append(name, provider);

    const gain = document.createElement("span");
    gain.textContent = "Instal·lat";
    gain.style.cssText = "font:600 11px var(--font-family-mono,monospace);color:#4ade80;text-align:right";
    
    heading.append(icon, identity, gain);
    card.appendChild(heading);

    const removeContainer = document.createElement("div");
    removeContainer.style.cssText = "margin:8px 0 0 23px;display:flex;justify-content:flex-end";
    const removeBtn = document.createElement("button");
    removeBtn.innerHTML = `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 6h18"/><path d="M19 6v14c0 1-1 2-2 2H7c-1 0-2-1-2-2V6"/><path d="M8 6V4c0-1 1-2 2-2h4c1 0 2 1 2 2v2"/><line x1="10" y1="11" x2="10" y2="17"/><line x1="14" y1="11" x2="14" y2="17"/></svg>`;
    removeBtn.title = "Eliminar instal·lació";
    removeBtn.style.cssText = "background:rgba(248,113,113,0.1);border:1px solid rgba(248,113,113,0.3);color:#f87171;padding:4px 8px;border-radius:4px;cursor:pointer;display:flex;align-items:center;justify-content:center;transition:background 0.2s";
    removeBtn.onmouseover = () => { removeBtn.style.background = "rgba(248,113,113,0.2)"; };
    removeBtn.onmouseout = () => { removeBtn.style.background = "rgba(248,113,113,0.1)"; };
    removeBtn.onclick = () => {
      if (!window.confirm(`Vols eliminar aquesta instal·lació (${inst.product}) i recalcular la cobertura espacial de la base de dades?`)) return;
      this.session.begin("remove");
      this.manager.removeRefinementInstallation(snapshot.requestId, snapshot.revision, inst.installationId);
    };
    removeContainer.appendChild(removeBtn);
    card.appendChild(removeContainer);

    return card;
  }

  private standaloneInstallationGroupCard(insts: RefinementWorkspaceNode['installations'], snapshot: RefinementSessionSnapshot): HTMLElement {
    const card = document.createElement("article");
    card.style.cssText = "padding:9px;border:1px solid rgba(74,222,128,0.3);border-radius:5px;background:rgba(74,222,128,0.05)";

    const inst = insts[0]!;
    const heading = document.createElement("label");
    heading.style.cssText = "display:grid;grid-template-columns:auto minmax(0,1fr) auto;gap:8px;align-items:start";

    const icon = document.createElement("div");
    icon.title = "Instal·lació local offline";
    icon.innerHTML = `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#4ade80" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M20 6L9 17l-5-5"/></svg>`;
    
    const identity = document.createElement("span");
    identity.style.cssText = "min-width:0";
    const name = document.createElement("strong");
    name.textContent = inst.product;
    name.style.cssText = "display:block;font-size:11px;font-weight:600;overflow:hidden;text-overflow:ellipsis";
    const provider = document.createElement("span");
    provider.textContent = `${inst.provider} · ${inst.version}`;
    provider.style.cssText = "display:block;margin-top:2px;font-size:10px;color:var(--color-text-dim,#b6c0ca)";
    
    const countBadge = document.createElement("span");
    if (insts.length > 1) {
      countBadge.textContent = `${insts.length} tessel·les independents`;
      countBadge.style.cssText = "display:inline-block;margin-top:4px;font-size:9px;color:#94a3b8;background:rgba(255,255,255,0.1);padding:2px 4px;border-radius:3px";
      provider.appendChild(document.createElement("br"));
      provider.appendChild(countBadge);
    }
    
    identity.append(name, provider);

    const gain = document.createElement("span");
    gain.textContent = "Instal·lat";
    gain.style.cssText = "font:600 11px var(--font-family-mono,monospace);color:#4ade80;text-align:right";
    
    heading.append(icon, identity, gain);
    card.appendChild(heading);

    const removeContainer = document.createElement("div");
    removeContainer.style.cssText = "margin:8px 0 0 23px;display:flex;justify-content:flex-end";
    const removeBtn = document.createElement("button");
    removeBtn.innerHTML = `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 6h18"/><path d="M19 6v14c0 1-1 2-2 2H7c-1 0-2-1-2-2V6"/><path d="M8 6V4c0-1 1-2 2-2h4c1 0 2 1 2 2v2"/><line x1="10" y1="11" x2="10" y2="17"/><line x1="14" y1="11" x2="14" y2="17"/></svg>`;
    removeBtn.title = "Eliminar instal·lació";
    removeBtn.style.cssText = "background:rgba(248,113,113,0.1);border:1px solid rgba(248,113,113,0.3);color:#f87171;padding:4px 8px;border-radius:4px;cursor:pointer;display:flex;align-items:center;justify-content:center;transition:background 0.2s";
    removeBtn.onmouseover = () => { removeBtn.style.background = "rgba(248,113,113,0.2)"; };
    removeBtn.onmouseout = () => { removeBtn.style.background = "rgba(248,113,113,0.1)"; };
    removeBtn.onclick = () => {
      const isMultiple = insts.length > 1;
      const msg = isMultiple
        ? `Vols eliminar aquestes ${insts.length} instal·lacions de ${inst.product} i recalcular la cobertura espacial de la base de dades?`
        : `Vols eliminar aquesta instal·lació (${inst.product}) i recalcular la cobertura espacial de la base de dades?`;
      if (!window.confirm(msg)) return;
      this.session.begin("remove");
      for (const i of insts) {
         this.manager.removeRefinementInstallation(snapshot.requestId, snapshot.revision, i.installationId);
      }
    };
    removeContainer.appendChild(removeBtn);
    card.appendChild(removeContainer);

    return card;
  }

  private candidateProgress(candidates: RefinementProductCandidate[], snapshot: RefinementSessionSnapshot): HTMLElement | null {
    if (!snapshot.progress || !snapshot.planSummary) return null;
    if (["READY", "ERROR", "CANCELLED"].includes(snapshot.progress.state)) return null;

    const planAssets = snapshot.planSummary.plan.assets;
    if (!planAssets || planAssets.length === 0) return null;

    const candidateFileNames = new Set(candidates.flatMap(c => c.assets.map(a => a.fileName)));
    const myAssets = planAssets.filter(asset => candidateFileNames.has(asset.fileName));

    if (myAssets.length === 0) return null;

    const container = document.createElement("div");
    container.setAttribute("data-id", "candidate-progress");
    container.style.cssText = "margin:8px 0 0 23px;font-size:10px";

    let stateLabel = "";
    let fillPercent = 0;

    const assetProgress = new Map(
      snapshot.progress.assetProgress.map(asset => [asset.fileName, asset]),
    );
    const knownAssets = myAssets
      .map(asset => assetProgress.get(asset.fileName))
      .filter((asset): asset is NonNullable<typeof asset> => asset !== undefined);
    const knownTotal = knownAssets.reduce((sum, asset) => sum + (asset.totalBytes ?? 0), 0);
    const knownDownloaded = knownAssets.reduce((sum, asset) => sum + asset.downloadedBytes, 0);

    if (knownAssets.length > 0 && knownTotal > 0) {
      fillPercent = Math.max(0, Math.min(100, (knownDownloaded / knownTotal) * 100));
      stateLabel = fillPercent >= 100 ? "Descarregat" : `Descarregant ${Math.round(fillPercent)}%`;
    } else if (snapshot.progress.state === "AUTHENTICATING") {
      stateLabel = "Esperant autenticació";
      fillPercent = 0;
    } else if (
      ["VERIFYING", "PROCESSING"].includes(snapshot.progress.state)
    ) {
      stateLabel = "Descarregat";
      fillPercent = 100;
    } else if (snapshot.progress.state === "QUEUED") {
      stateLabel = "En cua";
      fillPercent = 0;
    } else {
      stateLabel = "Descarregant...";
      fillPercent = 0;
    }

    const header = document.createElement("div");
    header.style.color = "var(--color-text-dim,#b6c0ca)";
    header.textContent = stateLabel;

    const track = document.createElement("div");
    track.style.cssText = "height:4px;border-radius:2px;overflow:hidden;background:rgba(255,255,255,0.1);margin-top:3px";

    const fill = document.createElement("div");
    fill.style.cssText = `height:100%;width:${fillPercent}%;background:${stateLabel === "Descarregat" ? "#4ade80" : "#facc15"};transition:width 200ms linear`;

    track.appendChild(fill);
    container.append(header, track);
    return container;
  }

  private planSummary(plan: RefinementDownloadPlan, snapshot: RefinementSessionSnapshot): HTMLElement {
    const coverage = snapshot.planSummary!.coverage;
    const section = document.createElement("section");
    section.style.cssText = "display:flex;flex-direction:column;gap:7px;padding:10px;border:1px solid rgba(250,204,21,.45);border-radius:5px;background:rgba(250,204,21,.05);flex-shrink:0;margin-top:4px;";
    const title = document.createElement("strong");
    title.textContent = "Resum del pla immutable";
    title.style.fontSize = "11px";
    const metrics = document.createElement("div");
    metrics.style.cssText = "display:grid;grid-template-columns:repeat(4,1fr);gap:5px;font:10px var(--font-family-mono,monospace)";
    metrics.append(
      metric("Local", coverage.existingPercent),
      metric("Nova", coverage.newEffectivePercent),
      metric("Total", coverage.plannedPercent),
      metric("Buit", coverage.remainingPercent),
    );
    let displayBytes = "mida pendent";
    if (plan.estimatedBytes !== null) {
      displayBytes = formatBytes(plan.estimatedBytes);
    } else {
      let sum = 0;
      let someUnknown = false;
      for (const asset of plan.assets) {
        if (asset.estimatedBytes !== null) sum += asset.estimatedBytes;
        else someUnknown = true;
      }
      if (sum > 0) displayBytes = `> ${formatBytes(sum)}`;
    }
    const detail = note(`${plan.assets.length} fitxers · ${displayBytes} · pla ${plan.planId}`);
    const confirm = actionButton("Confirmar descàrrega i processament", true);
    confirm.setAttribute("data-id", "confirm-download");
    const large = document.createElement("label");
    large.setAttribute("data-id", "large-download-confirmation");
    large.setAttribute("data-required", String(plan.requiresLargeDownloadConfirmation));
    large.style.cssText = "display:flex;gap:7px;align-items:center;font-size:10px";
    const largeCheckbox = document.createElement("input");
    largeCheckbox.type = "checkbox";
    large.append(largeCheckbox, document.createTextNode("Confirmo explícitament la descàrrega gran"));
    large.style.display = plan.requiresLargeDownloadConfirmation ? "flex" : "none";
    confirm.disabled = snapshot.busyOperation !== null;
    confirm.onclick = () => {
      if (plan.requiresLargeDownloadConfirmation && !largeCheckbox.checked) {
        window.alert("Cal confirmar explícitament la descàrrega gran.");
        return;
      }
      this.session.begin("confirm");
      this.manager.confirmRefinementDownload(snapshot.requestId, snapshot.revision, plan.planId, largeCheckbox.checked);
    };

    if (snapshot.progress && !["READY", "ERROR", "CANCELLED"].includes(snapshot.progress.state)) {
      confirm.style.display = "none";
      large.style.display = "none";
    }

    section.append(title, metrics, detail, large, confirm);
    return section;
  }

  private updateProductLiveState(snapshot: RefinementSessionSnapshot): void {
    const node = snapshot.workspace?.nodes.find((item) => item.categoryKey === snapshot.selectedCategoryKey) ?? null;
    const discoverButton = this.productPanel.querySelector<HTMLButtonElement>('[data-id="discover-products"]');
    if (discoverButton && node) {
      discoverButton.disabled = !node.applicable || !snapshot.aoi || snapshot.busyOperation !== null;
      discoverButton.title = !snapshot.aoi
        ? "Cal definir una AOI"
        : !node.applicable
          ? "No hi ha cap proveïdor comercialitzable verificat per aquest node"
          : "Consulta el catàleg remot";
    }

    const coverageLabel = this.productPanel.querySelector<HTMLElement>('[data-id="selected-coverage"]');
    if (coverageLabel && node) {
      const hasCandidates = snapshot.candidates.length > 0;
      const totalCoverage = snapshot.planSummary?.coverage.plannedPercent.toFixed(1) ?? "—";
      coverageLabel.textContent = hasCandidates 
        ? `Cobertura local: ${node.verifiedPercent.toFixed(1)}% | Seleccionada: ${totalCoverage}%`
        : `Cobertura local: ${node.verifiedPercent.toFixed(1)}%`;
    }

    const planSlot = this.productPanel.querySelector<HTMLElement>('[data-id="plan-summary-slot"]');
    if (planSlot && (this.renderedPlanSummary !== snapshot.planSummary || planSlot.childElementCount === 0)) {
      planSlot.replaceChildren(
        ...(snapshot.planSummary ? [this.planSummary(snapshot.planSummary.plan, snapshot)] : []),
      );
      this.renderedPlanSummary = snapshot.planSummary;
    }

    const activeProgress = snapshot.progress !== null
      && !["READY", "ERROR", "CANCELLED"].includes(snapshot.progress.state);
    const confirm = this.productPanel.querySelector<HTMLButtonElement>('[data-id="confirm-download"]');
    if (confirm) {
      confirm.disabled = snapshot.busyOperation !== null;
      confirm.style.display = activeProgress ? "none" : "";
    }
    const large = this.productPanel.querySelector<HTMLElement>('[data-id="large-download-confirmation"]');
    if (large) {
      large.style.display = activeProgress
        ? "none"
        : large.getAttribute("data-required") === "true" ? "flex" : "none";
    }

    const progressSlot = this.productPanel.querySelector<HTMLElement>('[data-id="download-progress-slot"]');
    if (progressSlot) {
      progressSlot.replaceChildren(...(snapshot.progress ? [this.progress(snapshot)] : []));
    }
    this.updateCandidateProgress(snapshot);
  }

  private updateCandidateProgress(snapshot: RefinementSessionSnapshot): void {
    const candidatesById = new Map(snapshot.candidates.map((candidate) => [candidate.candidateId, candidate]));
    for (const card of this.productPanel.querySelectorAll<HTMLElement>("[data-refinement-candidate-ids]")) {
      const rawIds = card.getAttribute("data-refinement-candidate-ids");
      let ids: string[] = [];
      try {
        const parsed: unknown = JSON.parse(rawIds ?? "[]");
        if (Array.isArray(parsed) && parsed.every((value) => typeof value === "string")) ids = parsed;
      } catch {
        ids = [];
      }
      const candidates = ids
        .map((id) => candidatesById.get(id))
        .filter((candidate): candidate is RefinementProductCandidate => candidate !== undefined);
      const current = card.querySelector<HTMLElement>(':scope > [data-id="candidate-progress"]');
      const next = this.candidateProgress(candidates, snapshot);
      if (current && next) current.replaceWith(next);
      else if (current) current.remove();
      else if (next) card.appendChild(next);
    }
  }

  private progress(snapshot: RefinementSessionSnapshot): HTMLElement {
    const progress = snapshot.progress!;
    const section = document.createElement("section");
    section.style.cssText = "display:flex;flex-direction:column;gap:5px;font-size:10px";
    const header = document.createElement("div");
    const percentage = progress.progress === null
      ? null
      : Math.round(Math.max(0, Math.min(1, progress.progress)) * 100);
    header.textContent = `${technicalStateLabel(progress.state)}${percentage === null ? "" : ` · ${percentage}%`} · ${formatBytes(progress.downloadedBytes)}${progress.totalBytes !== null ? ` / ${formatBytes(progress.totalBytes)}` : ""}`;
    const track = document.createElement("div");
    track.setAttribute("role", "progressbar");
    track.setAttribute("aria-valuemin", "0");
    track.setAttribute("aria-valuemax", "100");
    if (percentage !== null) track.setAttribute("aria-valuenow", String(percentage));
    track.style.cssText = "height:5px;border-radius:3px;overflow:hidden;background:var(--color-surface-hover,#2a3440);position:relative";
    const fill = document.createElement("div");
    if (percentage === null) {
      fill.style.cssText = "position:absolute;top:0;bottom:0;left:0;width:30%;background:var(--color-primary,#3b82f6);animation:refinement-indeterminate 1.5s infinite linear";
    } else {
      fill.style.cssText = `height:100%;width:${percentage}%;background:#facc15;transition:width 120ms linear`;
    }
    track.appendChild(fill);
    const file = note(progress.currentFile ?? progress.error ?? "Preparant fitxers…");
    section.append(header, track, file);
    if (!["READY", "ERROR", "CANCELLED"].includes(progress.state)) {
      const cancel = actionButton("Cancel·lar descàrrega", false);
      cancel.onclick = () => {
        if (!window.confirm("Cancel·lar la descàrrega? Els parcials es conservaran per reprendre-la.")) return;
        this.manager.cancelRefinementDownload(
          snapshot.requestId,
          snapshot.revision,
          progress.planId,
        );
      };
      section.appendChild(cancel);
    }
    return section;
  }

  private discover(node: RefinementWorkspaceNode): void {
    const snapshot = this.session.snapshot();
    if (!snapshot.aoi) return;
    const next = this.session.begin("query");
    this.manager.queryRefinementProducts(next.requestId, next.revision, node.categoryKey, snapshot.aoi);
  }

  private schedulePlan(snapshot: RefinementSessionSnapshot): void {
    if (this.planTimer) clearTimeout(this.planTimer);
    if (!snapshot.aoi || !snapshot.selectedCategoryKey || snapshot.selectedProductIds.size === 0) return;
    this.planTimer = setTimeout(() => {
      const current = this.session.begin("plan");
      if (!current.aoi || !current.selectedCategoryKey) return;
      this.manager.calculateRefinementPlan(
        current.requestId,
        current.revision,
        current.selectedCategoryKey,
        current.aoi,
        [...current.selectedProductIds],
      );
    }, 180);
  }
}

function panelStyle(): string {
  return "display:flex;flex-direction:column;gap:9px;min-height:0;overflow:hidden;padding:10px;border:1px solid var(--color-border,#3a4350);border-radius:6px;background:var(--color-surface-raised,#202833)";
}

function panelHeader(title: string, detail: string): HTMLElement {
  const header = document.createElement("header");
  header.style.cssText = "display:flex;justify-content:space-between;align-items:baseline;gap:8px;padding-bottom:7px;border-bottom:1px solid var(--color-border,#3a4350)";
  const heading = document.createElement("h3");
  heading.textContent = title;
  heading.style.cssText = "margin:0;font-size:12px;font-weight:600;color:var(--color-text-bright,#fff)";
  const metadata = document.createElement("span");
  metadata.textContent = detail;
  metadata.style.cssText = "font:9px var(--font-family-mono,monospace);color:var(--color-text-muted,#94a3b8);overflow:hidden;text-overflow:ellipsis;white-space:nowrap";
  header.append(heading, metadata);
  return header;
}

function actionButton(label: string, primary: boolean): HTMLButtonElement {
  const button = document.createElement("button");
  button.type = "button";
  button.textContent = label;
  button.style.cssText = `padding:7px 11px;border-radius:4px;border:1px solid ${primary ? "#facc15" : "var(--color-border,#3a4350)"};background:${primary ? "#facc15" : "transparent"};color:${primary ? "#111827" : "var(--color-text,#e5e7eb)"};font-size:10px;font-weight:${primary ? "600" : "400"};cursor:pointer`;
  return button;
}

function note(text: string): HTMLDivElement {
  const element = document.createElement("div");
  element.textContent = text;
  element.style.cssText = "font-size:10px;line-height:1.45;color:var(--color-text-dim,#b6c0ca)";
  return element;
}

function legendItem(color: string, label: string): HTMLElement {
  const item = document.createElement("span");
  item.style.cssText = "display:inline-flex;align-items:center;gap:5px";
  const swatch = document.createElement("i");
  swatch.style.cssText = `display:inline-block;width:14px;height:8px;border:1px solid ${color};background:${color}33;border-radius:2px`;
  item.append(swatch, document.createTextNode(label));
  return item;
}

function fact(text: string): HTMLElement {
  const value = document.createElement("span");
  value.textContent = text;
  return value;
}

function metric(label: string, value: number): HTMLElement {
  const item = document.createElement("span");
  item.textContent = `${label} ${value.toFixed(1)}%`;
  return item;
}

function sameStringSet(left: ReadonlySet<string>, right: ReadonlySet<string>): boolean {
  if (left.size !== right.size) return false;
  for (const value of left) {
    if (!right.has(value)) return false;
  }
  return true;
}

function selectedIdsKey(ids: ReadonlySet<string>): string {
  return [...ids].sort().join("\u001f");
}

function stateGlyph(state: RefinementWorkspaceNode["state"]): string {
  return state === "complete" ? "●" : state === "partial" ? "◐" : state === "absent" ? "○" : "–";
}

function stateColor(state: RefinementWorkspaceNode["state"]): string {
  return state === "complete" ? "#4ade80" : state === "partial" ? "#facc15" : state === "absent" ? "#94a3b8" : "#64748b";
}

function stateLabel(state: RefinementWorkspaceNode["state"]): string {
  return state === "complete" ? "Cobertura completa" : state === "partial" ? "Cobertura parcial" : state === "absent" ? "Sense cobertura" : "No aplicable";
}

function treeControlStyle(): string {
  return "width:18px;height:22px;padding:0;border:0;background:transparent;color:var(--color-text-dim,#b6c0ca);cursor:pointer";
}

function formatBytes(bytes: number | null): string {
  if (bytes === null) return "mida pendent";
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1048576) return `${(bytes / 1024).toFixed(1)} KiB`;
  if (bytes < 1073741824) return `${(bytes / 1048576).toFixed(1)} MiB`;
  return `${(bytes / 1073741824).toFixed(2)} GiB`;
}

function formatDates(start: string | null, end: string | null): string {
  if (!start && !end) return "data no declarada";
  return start === end || !end ? (start ?? end ?? "") : `${start ?? "…"} – ${end}`;
}

function technicalStateLabel(state: RefinementSessionSnapshot["progress"] extends infer _ ? import("../../../contracts/refinement_contracts").RefinementTechnicalState : never): string {
  const labels: Record<import("../../../contracts/refinement_contracts").RefinementTechnicalState, string> = {
    QUEUED: "En cua",
    AUTHENTICATING: "Esperant autenticació CDSE",
    DOWNLOADING: "Descarregant",
    VERIFYING: "Verificant",
    PROCESSING: "Processant mosaic",
    READY: "Preparat",
    ERROR: "Error",
    CANCELLED: "Cancel·lat",
  };
  return labels[state];
}
