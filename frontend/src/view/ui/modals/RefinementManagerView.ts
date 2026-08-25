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
  private opened = false;
  private disposed = false;

  constructor(
    private readonly manager: ResourceManager,
    private readonly callbacks: RefinementManagerCallbacks,
  ) {
    this.element.className = "refinement-manager";
    this.element.style.cssText = "display:flex;flex-direction:column;gap:12px;min-height:0;height:100%;color:var(--color-text,#e5e7eb)";
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

    this.columns.className = "refinement-columns";
    this.columns.style.cssText = "display:grid;grid-template-columns:minmax(300px,.8fr) minmax(420px,1.2fr);gap:12px;min-height:310px;flex:1";
    this.columns.append(this.treePanel, this.productPanel);
    this.element.append(this.mapView.element, legend, this.statusRegion, this.columns);
    this.layoutObserver = new ResizeObserver((entries) => {
      const width = entries[0]?.contentRect.width ?? this.element.clientWidth;
      this.applyResponsiveLayout(width);
    });
    this.layoutObserver.observe(this.element);

    this.unsubscribeManager = manager.subscribeRefinement((message) => {
      if (this.session.accept(message) && message.type === "refinement_coverage_updated") {
        const state = this.session.snapshot();
        this.manager.requestRefinementWorkspace(state.requestId, state.revision, state.aoi ?? undefined);
      }
    });
    this.unsubscribeSession = this.session.subscribe((snapshot) => this.render(snapshot));
    this.render(this.session.snapshot());
  }

  public open(): void {
    if (this.disposed) return;
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
    const compact = width > 0 && width < 780;
    this.columns.style.gridTemplateColumns = compact
      ? "minmax(0,1fr)"
      : "minmax(300px,.8fr) minmax(420px,1.2fr)";
    this.columns.style.overflowY = compact ? "auto" : "visible";
    this.treePanel.style.minHeight = compact ? "320px" : "0";
    this.productPanel.style.minHeight = compact ? "360px" : "0";
    this.mapView.element.style.gridTemplateRows = compact
      ? "auto minmax(200px,30vh) auto"
      : "auto minmax(220px,34vh) auto";
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
    this.renderStatus(snapshot);
    this.renderTree(snapshot);
    this.renderProducts(snapshot);
    this.mapView.setAoi(snapshot.aoi);
    this.mapView.setCandidates(snapshot.candidates, snapshot.selectedProductIds);
    const coverage = snapshot.planSummary?.coverage;
    if (coverage) this.mapView.setCoverage(coverage.existing, coverage.planned, coverage.remaining);
    else this.mapView.setCoverage(null, null, null);
  }

  private renderStatus(snapshot: RefinementSessionSnapshot): void {
    if (snapshot.error) {
      this.statusRegion.textContent = snapshot.error;
      this.statusRegion.style.color = "var(--color-error,#f87171)";
      return;
    }
    this.statusRegion.style.color = "var(--color-text-dim,#b6c0ca)";
    const messages: Record<NonNullable<RefinementSessionSnapshot["busyOperation"]>, string> = {
      workspace: "Calculant l'estat verificat de la jerarquia…",
      query: "Consultant els proveïdors compatibles…",
      plan: "Calculant cobertura efectiva i mosaic…",
      confirm: "Descarregant, verificant i processant…",
      remove: "Eliminant la instal·lació…",
    };
    this.statusRegion.textContent = snapshot.busyOperation
      ? messages[snapshot.busyOperation]
      : snapshot.aoi
        ? "AOI vàlida en EPSG:4326. Selecciona una categoria aplicable."
        : "Dibuixa o importa una AOI petita per començar; no es fan descàrregues continentals implícites.";
  }

  private renderTree(snapshot: RefinementSessionSnapshot): void {
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
    const percent = document.createElement("span");
    percent.textContent = node.state === "not_applicable" ? "—" : `${node.verifiedPercent.toFixed(0)}%`;
    percent.style.cssText = "font:10px var(--font-family-mono,monospace);color:var(--color-text-dim,#b6c0ca)";
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
    if (event.key === "ArrowDown" && items[index + 1]) items[index + 1]!.focus();
    else if (event.key === "ArrowUp" && items[index - 1]) items[index - 1]!.focus();
    else if (event.key === "ArrowRight" && node.children.length) this.expandedKeys.add(node.categoryKey);
    else if (event.key === "ArrowLeft" && node.children.length) this.expandedKeys.delete(node.categoryKey);
    else if (event.key === "Enter" || event.key === " ") this.session.selectCategory(node.categoryKey);
    else return;
    event.preventDefault();
    this.render(this.session.snapshot());
  }

  private toggleExpanded(categoryKey: string): void {
    if (this.expandedKeys.has(categoryKey)) this.expandedKeys.delete(categoryKey);
    else this.expandedKeys.add(categoryKey);
    this.render(this.session.snapshot());
  }

  private renderProducts(snapshot: RefinementSessionSnapshot): void {
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
    const discoverButton = actionButton("Descàrrega automàtica", true);
    discoverButton.disabled = !node.applicable || !snapshot.aoi || snapshot.busyOperation !== null;
    discoverButton.title = !snapshot.aoi
      ? "Cal definir una AOI"
      : !node.applicable ? "No hi ha cap proveïdor comercialitzable verificat per aquest node" : "Consulta el catàleg remot";
    discoverButton.onclick = () => this.discover(node);
    actions.append(importButton, discoverButton);
    this.productPanel.appendChild(actions);

    if (node.installationIds.length) this.productPanel.appendChild(this.installations(node, snapshot));
    if (snapshot.candidates.length) {
      const list = document.createElement("div");
      list.style.cssText = "display:flex;flex-direction:column;gap:8px;overflow:auto;min-height:0;max-height:300px;padding-right:4px";
      for (const candidate of snapshot.candidates) list.appendChild(this.productCard(candidate, snapshot));
      this.productPanel.appendChild(list);
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
    if (snapshot.planSummary) this.productPanel.appendChild(this.planSummary(snapshot.planSummary.plan, snapshot));
    if (snapshot.progress) this.productPanel.appendChild(this.progress(snapshot));
  }

  private installations(node: RefinementWorkspaceNode, snapshot: RefinementSessionSnapshot): HTMLElement {
    const box = document.createElement("div");
    box.style.cssText = "display:flex;flex-direction:column;gap:5px;padding:8px;border:1px solid rgba(74,222,128,.35);border-radius:5px;background:rgba(74,222,128,.06)";
    for (const installationId of node.installationIds) {
      const row = document.createElement("div");
      row.style.cssText = "display:flex;align-items:center;justify-content:space-between;gap:8px;font-size:10px";
      const label = document.createElement("span");
      label.textContent = `Instal·lació verificada · ${installationId}`;
      const remove = actionButton("Eliminar", false);
      remove.onclick = () => {
        if (!window.confirm("Eliminar aquesta instal·lació i recalcular la cobertura?")) return;
        this.session.begin("remove");
        this.manager.removeRefinementInstallation(snapshot.requestId, snapshot.revision, installationId);
      };
      row.append(label, remove);
      box.appendChild(row);
    }
    return box;
  }

  private productCard(candidate: RefinementProductCandidate, snapshot: RefinementSessionSnapshot): HTMLElement {
    const card = document.createElement("article");
    card.style.cssText = `padding:9px;border:1px solid ${snapshot.selectedProductIds.has(candidate.candidateId) ? "#22d3ee" : "var(--color-border,#3a4350)"};border-radius:5px;background:var(--color-surface,#141a22)`;
    const heading = document.createElement("label");
    heading.style.cssText = "display:grid;grid-template-columns:auto minmax(0,1fr) auto;gap:8px;align-items:start;cursor:pointer";
    const checkbox = document.createElement("input");
    checkbox.type = "checkbox";
    checkbox.checked = snapshot.selectedProductIds.has(candidate.candidateId);
    checkbox.ariaLabel = `Seleccionar ${candidate.product}`;
    checkbox.onchange = () => {
      const next = this.session.setProductSelected(candidate.candidateId, checkbox.checked);
      this.schedulePlan(next);
    };
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
    gain.textContent = `+${candidate.newEffectivePercent.toFixed(1)}%`;
    gain.title = `${candidate.availablePercent.toFixed(1)}% disponible dins l'AOI`;
    gain.style.cssText = "font:600 11px var(--font-family-mono,monospace);color:#22d3ee";
    heading.append(checkbox, identity, gain);

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
    card.append(heading, facts, license);
    return card;
  }

  private planSummary(plan: RefinementDownloadPlan, snapshot: RefinementSessionSnapshot): HTMLElement {
    const coverage = snapshot.planSummary!.coverage;
    const section = document.createElement("section");
    section.style.cssText = "display:flex;flex-direction:column;gap:7px;padding:10px;border:1px solid rgba(250,204,21,.45);border-radius:5px;background:rgba(250,204,21,.05)";
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
    const detail = note(`${plan.assets.length} fitxers · ${formatBytes(plan.estimatedBytes)} · pla ${plan.planId}`);
    const confirm = actionButton("Confirmar descàrrega i processament", true);
    const large = document.createElement("label");
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
    section.append(title, metrics, detail, large, confirm);
    return section;
  }

  private progress(snapshot: RefinementSessionSnapshot): HTMLElement {
    const progress = snapshot.progress!;
    const section = document.createElement("section");
    section.style.cssText = "display:flex;flex-direction:column;gap:5px;font-size:10px";
    const header = document.createElement("div");
    header.textContent = `${technicalStateLabel(progress.state)} · ${formatBytes(progress.downloadedBytes)}${progress.totalBytes ? ` / ${formatBytes(progress.totalBytes)}` : ""}`;
    const track = document.createElement("div");
    track.setAttribute("role", "progressbar");
    track.setAttribute("aria-valuemin", "0");
    track.setAttribute("aria-valuemax", "100");
    track.setAttribute("aria-valuenow", String(Math.round((progress.progress ?? 0) * 100)));
    track.style.cssText = "height:5px;border-radius:3px;overflow:hidden;background:var(--color-surface-hover,#2a3440)";
    const fill = document.createElement("div");
    fill.style.cssText = `height:100%;width:${Math.round((progress.progress ?? 0) * 100)}%;background:#facc15;transition:width 120ms linear`;
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
    DOWNLOADING: "Descarregant",
    VERIFYING: "Verificant",
    PROCESSING: "Processant mosaic",
    READY: "Preparat",
    ERROR: "Error",
    CANCELLED: "Cancel·lat",
  };
  return labels[state];
}
