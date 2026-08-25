import { ResourceManager } from "../../../application/ResourceManager";
import type { ResourceDescriptor, ResourceVariant } from "../../../contracts/resource_manager_contracts";
import { CategoricalImportView } from "./CategoricalImportView";

type EarthTab = "elevation" | "categorical" | "refinement";
type ResourceDomain = "sky" | "earth";

export interface ResourceImportAction {
  readonly available: boolean;
  readonly title: string;
}

/** User-facing availability of local imports for the selected resource area. */
export function resourceImportAction(
  domain: ResourceDomain,
  earthTab: EarthTab,
): ResourceImportAction {
  if (domain !== "earth") {
    return { available: false, title: "" };
  }
  if (earthTab === "elevation") {
    return { available: true, title: "Importar una font raster d'elevació" };
  }
  if (earthTab === "categorical") {
    return {
      available: true,
      title: "Importar una classificació de cobertes del sòl",
    };
  }
  return {
    available: false,
    title: "La importació de refinaments encara no està disponible",
  };
}

interface RasterInspection {
  readonly driver: string;
  readonly width: number;
  readonly height: number;
  readonly crs: string | null;
  readonly sourceDtype: string | null;
  readonly subdatasets: string[];
  readonly bands: { index: number; dtype: string; description: string | null }[];
  readonly metadataSuggestions: { verticalUnit: string | null; requiresUnitConfirmation: boolean };
}

/** Resource catalogue plus one progressive, recoverable elevation import surface. */
export class ResourceManagerModal {
  private readonly element = document.createElement("div");
  private readonly contentBox = document.createElement("div");
  private readonly tabsContainer = document.createElement("div");
  private readonly listContainer = document.createElement("div");
  private readonly footer = document.createElement("div");
  private readonly importButton = document.createElement("button");
  private readonly closeButton = document.createElement("button");
  private readonly unsubCatalog: () => void;
  private readonly unsubJobs: () => void;
  private readonly unsubOperation: () => void;

  private activeDomain: ResourceDomain = "sky";
  private activeCategorySky = "solar_system";
  private activeCategoryEarth: EarthTab = "elevation";
  private importStates: Record<string, boolean> = {};
  
  private get importVisible(): boolean {
    return this.activeDomain === "earth" && Boolean(this.importStates[this.activeCategoryEarth]);
  }
  private set importVisible(value: boolean) {
    if (this.activeDomain === "earth") {
      this.importStates[this.activeCategoryEarth] = value;
    }
  }

  private importId: string | null = null;
  private importInspection: RasterInspection | null = null;
  private importInspectedSubdataset: string | null = null;
  private importFiles: File[] = [];
  private importBusy = false;
  private categoricalImport: CategoricalImportView | null = null;
  private elevationImportForm: HTMLDivElement | null = null;
  private importAbortController: AbortController | null = null;

  constructor(private readonly manager: ResourceManager) {
    this.element.style.cssText = `
      position: fixed; inset: 0; background: rgba(0,0,0,.7); backdrop-filter: blur(4px);
      display: flex; justify-content: center; align-items: center; z-index: 10000;
      font-family: var(--font-family-sans, sans-serif);
    `;
    this.contentBox.style.cssText = `
      width: 760px; max-width: 92vw; height: min(760px, 88vh);
      background: var(--color-surface, #1a1a1a); border: 1px solid var(--color-border, #333);
      border-radius: 8px; display: flex; flex-direction: column; overflow: hidden;
      box-shadow: 0 10px 30px rgba(0,0,0,.5);
    `;

    const header = document.createElement("div");
    header.style.cssText = `
      flex: 0 0 auto; padding: 16px 20px; border-bottom: 1px solid var(--color-border, #333);
      display: flex; justify-content: space-between; align-items: center;
      background: var(--color-surface-raised, #222);
    `;
    const title = document.createElement("h2");
    title.textContent = "Gestor de recursos i capes";
    title.style.cssText = "margin:0;font-size:16px;color:var(--color-text-bright,#fff);font-weight:500";
    const closeIcon = document.createElement("button");
    closeIcon.textContent = "×";
    closeIcon.ariaLabel = "Tancar";
    closeIcon.style.cssText = "background:none;border:0;color:#aaa;font-size:24px;cursor:pointer";
    closeIcon.onclick = () => this.close();
    header.append(title, closeIcon);

    this.tabsContainer.style.cssText = `
      flex: 0 0 auto; display: flex; flex-direction: column;
      border-bottom: 1px solid var(--color-border, #333);
    `;
    this.listContainer.style.cssText = `
      flex: 1 1 auto; min-height: 0; overflow-y: auto; padding: 16px 20px;
      display: flex; flex-direction: column; gap: 14px;
    `;
    this.footer.style.cssText = `
      flex: 0 0 auto; display: flex; justify-content: space-between; padding: 12px 20px;
      border-top: 1px solid var(--color-border, #333); background: var(--color-surface-raised, #222);
    `;
    this.importButton.textContent = "+ Importar";
    this.importButton.style.cssText = buttonStyle();
    this.importButton.onclick = () => {
      this.importVisible = true;
      this.renderFooter();
      this.renderList();
    };
    this.closeButton.textContent = "Tancar";
    this.closeButton.style.cssText = buttonStyle();
    this.closeButton.onclick = () => this.close();
    this.footer.append(this.importButton, this.closeButton);
    this.contentBox.append(header, this.tabsContainer, this.listContainer, this.footer);
    this.element.appendChild(this.contentBox);

    this.unsubCatalog = this.manager.subscribeCatalog(() => {
      this.renderTabs();
      if (!this.importVisible) {
        this.renderList();
      }
    });
    this.unsubJobs = this.manager.subscribeJobs(() => {
      if (!this.importVisible) {
        this.renderList();
      }
    });
    this.unsubOperation = this.manager.subscribeOperationProgress((msg) => {
      if (this.categoricalImport) {
        this.categoricalImport.handleOperationProgress(msg);
      }
    });
    this.renderTabs();
    this.renderFooter();
    this.renderList();
  }

  public open(): void {
    document.body.appendChild(this.element);
    this.manager.requestCatalog();
  }

  public close(): void {
    if (this.importId) void this.cancelImportSession();
    void this.releaseCategoricalImport();
    this.element.remove();
  }

  public dispose(): void {
    if (this.importId) void this.cancelImportSession();
    void this.releaseCategoricalImport();
    this.element.remove();
    this.unsubCatalog();
    this.unsubJobs();
    this.unsubOperation();
  }

  private renderTabs(): void {
    this.tabsContainer.replaceChildren();
    const domainBar = document.createElement("div");
    domainBar.style.cssText = "display:flex;border-bottom:1px solid var(--color-border,#333)";
    for (const domain of [{ id: "sky", label: "CEL" }, { id: "earth", label: "TERRA" }] as const) {
      const button = tabButton(domain.label, this.activeDomain === domain.id, true);
      button.onclick = () => {
        this.activeDomain = domain.id;
        this.renderTabs();
        this.renderFooter();
        this.renderList();
      };
      domainBar.appendChild(button);
    }

    const categoryBar = document.createElement("div");
    categoryBar.style.cssText = "display:flex;background:var(--color-surface-raised,#222);padding:0 16px";
    const categories = this.activeDomain === "sky"
      ? [{ id: "solar_system", label: "Sistema solar" }, { id: "deep_sky", label: "Espai profund" }]
      : [{ id: "elevation", label: "Elevació" }, { id: "categorical", label: "Categòric" }, { id: "refinement", label: "Refinament" }];
    const active = this.activeDomain === "sky" ? this.activeCategorySky : this.activeCategoryEarth;
    for (const category of categories) {
      const button = tabButton(category.label, category.id === active, false);
      button.onclick = () => {
        if (this.activeDomain === "sky") this.activeCategorySky = category.id;
        else this.activeCategoryEarth = category.id as EarthTab;
        this.renderTabs();
        this.renderFooter();
        this.renderList();
      };
      categoryBar.appendChild(button);
    }
    this.tabsContainer.append(domainBar, categoryBar);
  }

  private renderFooter(): void {
    const earth = this.activeDomain === "earth";
    const action = resourceImportAction(this.activeDomain, this.activeCategoryEarth);
    this.importButton.style.display = earth ? "inline-block" : "none";
    this.importButton.disabled = !action.available || this.importVisible;
    this.importButton.style.opacity = this.importButton.disabled ? ".45" : "1";
    this.importButton.title = action.title;
  }

  private renderList(): void {
    this.listContainer.replaceChildren();
    if (this.importVisible) {
      if (this.activeCategoryEarth === "categorical") {
        if (!this.categoricalImport) {
          this.categoricalImport = new CategoricalImportView({
            onCommitted: () => {
              this.categoricalImport = null;
              this.importVisible = false;
              this.manager.requestCatalog();
              this.renderFooter();
              this.renderList();
            },
            onBack: () => {
              void this.releaseCategoricalImport();
              this.importVisible = false;
              this.renderFooter();
              this.renderList();
            },
          });
        }
        this.listContainer.appendChild(this.categoricalImport.element);
        return;
      } else if (this.activeCategoryEarth === "elevation") {
        if (!this.elevationImportForm) {
          this.elevationImportForm = document.createElement("div");
          this.renderImportForm(this.elevationImportForm);
        }
        this.listContainer.appendChild(this.elevationImportForm);
      }
      return;
    }
    const descriptors = this.manager.getAllDescriptors();
    if (descriptors.length === 0) {
      this.listContainer.appendChild(message("Carregant catàleg…"));
      return;
    }
    const category = this.activeDomain === "sky"
      ? this.activeCategorySky
      : this.activeCategoryEarth === "categorical"
        ? "land_cover"
        : this.activeCategoryEarth === "refinement"
          ? "light_pollution"
          : "elevation";
    const filtered = descriptors.filter(value => value.domain === this.activeDomain && value.category === category);
    if (filtered.length === 0) {
      this.listContainer.appendChild(message("No hi ha recursos en aquesta categoria."));
      return;
    }
    for (const descriptor of filtered) this.listContainer.appendChild(this.resourceCard(descriptor));
  }

  private resourceCard(descriptor: ResourceDescriptor): HTMLElement {
    const card = document.createElement("article");
    card.style.cssText = "border:1px solid var(--color-border,#333);border-radius:6px;padding:12px;background:var(--color-surface-raised,#222)";
    const heading = document.createElement("div");
    heading.style.cssText = "display:flex;justify-content:space-between;gap:12px;margin-bottom:8px";
    const identity = document.createElement("div");
    const title = document.createElement("div");
    title.textContent = descriptor.name;
    title.style.cssText = "font-weight:500;font-size:14px;color:var(--color-text-bright,#fff)";
    const provider = document.createElement("div");
    provider.textContent = `${descriptor.provider} · ${descriptor.category}`;
    provider.style.cssText = "font-size:11px;color:var(--color-text-muted,#888);margin-top:2px";
    identity.append(title, provider);
    if (["elevation", "land_cover"].includes(descriptor.category) && descriptor.metadata.sourceId) {
      const role = document.createElement("div");
      const ownership = descriptor.metadata.ownership === "managed" ? "gestionada" : "externa";
      role.textContent = descriptor.metadata.active === true
        ? `Font activa · propietat ${ownership}`
        : descriptor.metadata.fallback === true
          ? `Fallback ${Number(descriptor.metadata.fallbackOrder) || 1} · propietat ${ownership}`
          : `Propietat ${ownership}`;
      role.style.cssText = "font-size:11px;color:#4ade80;margin-top:3px";
      identity.appendChild(role);
    }
    const states = descriptor.variants.map(variant => this.manager.getInstallState(descriptor.id, variant.id).status);
    const status = states.includes("DOWNLOADING") ? "DOWNLOADING"
      : states.includes("ERROR") ? "ERROR"
        : states.includes("READY") ? "READY" : "NOT_INSTALLED";
    const badge = document.createElement("span");
    badge.textContent = status;
    badge.style.cssText = `font-size:10px;padding:2px 6px;border-radius:4px;border:1px solid ${status === "READY" ? "#4ade80" : "#555"};color:${status === "READY" ? "#4ade80" : "#aaa"};align-self:flex-start`;
    heading.append(identity, badge);
    card.appendChild(heading);
    const facts = document.createElement("div");
    facts.style.cssText = "font-size:11px;color:var(--color-text-dim,#aaa);border-left:2px solid var(--color-border,#333);padding-left:10px;margin-bottom:10px";
    appendFact(facts, descriptor.description);
    appendFact(facts, descriptor.license ? `Llicència: ${descriptor.license}` : "");
    appendFact(facts, descriptor.citation ? `Citació: ${descriptor.citation}` : "");
    if (descriptor.credits.length) appendFact(facts, `Crèdits: ${descriptor.credits.join(", ")}`);
    card.appendChild(facts);
    const variants = document.createElement("div");
    variants.style.cssText = "display:flex;flex-direction:column;gap:8px";
    for (const variant of descriptor.variants) variants.appendChild(this.variantRow(descriptor, variant));
    card.appendChild(variants);
    return card;
  }

  private variantRow(descriptor: ResourceDescriptor, variant: ResourceVariant): HTMLElement {
    const row = document.createElement("div");
    row.style.cssText = "display:flex;justify-content:space-between;align-items:center;gap:10px;background:var(--color-surface,#1a1a1a);padding:8px;border-radius:4px;border:1px solid var(--color-border,#333)";
    const info = document.createElement("div");
    const title = document.createElement("div");
    title.textContent = variant.title;
    title.style.cssText = "font-size:11px;color:#fff";
    const details = document.createElement("div");
    details.textContent = [variant.format?.toUpperCase(), variant.width && variant.height ? `${variant.width} × ${variant.height}` : null, variant.publishedSizeLabel ?? formatBytes(variant.expectedBytes)].filter(Boolean).join(" · ");
    details.style.cssText = "font-size:10px;color:#888";
    info.append(title, details);
    const actions = document.createElement("div");
    const state = this.manager.getInstallState(descriptor.id, variant.id);
    if (state.status === "READY") {
      const ready = document.createElement("span");
      ready.textContent = "Instal·lat";
      ready.style.cssText = "font-size:11px;color:#4ade80";
      const remove = actionButton("Eliminar");
      remove.style.color = "#ff8a80";
      remove.onclick = () => {
        if (window.confirm(`Vols eliminar ${descriptor.name} (${variant.title})?`)) {
          this.manager.deleteResource(descriptor.id, variant.id);
        }
      };
      actions.append(ready, remove);
    } else if (["DOWNLOADING", "PAUSED"].includes(state.status)) {
      const toggle = actionButton(state.status === "PAUSED" ? "Reprendre" : "Pausar");
      toggle.onclick = () => state.status === "PAUSED"
        ? this.manager.startDownload(descriptor.id, variant.id)
        : this.manager.pauseDownload(descriptor.id, variant.id);
      const cancel = actionButton("Cancel·lar");
      cancel.onclick = () => this.manager.cancelDownload(descriptor.id, variant.id);
      actions.append(toggle, cancel);
    } else if (["VERIFYING", "PROCESSING"].includes(state.status)) {
      actions.appendChild(message(state.status === "VERIFYING" ? "Verificant…" : "Processant…"));
    } else {
      const downloadable = descriptor.acquisitionKind !== "EXTERNAL_FILE"
        && (Boolean(variant.sourceUrl) || Boolean(variant.sourceUrls?.length) || !["HTTP_BUNDLE", "STATIC_FILE"].includes(descriptor.acquisitionKind));
      if (downloadable) {
        const download = actionButton("Descàrrega automàtica");
        download.onclick = () => this.manager.startDownload(descriptor.id, variant.id);
        actions.appendChild(download);
      }
      if (descriptor.originalSourceUrl || descriptor.directUrl) {
        const link = document.createElement("a");
        link.textContent = "Font original";
        link.href = descriptor.originalSourceUrl || descriptor.directUrl || "#";
        link.target = "_blank";
        link.rel = "noopener noreferrer";
        link.style.cssText = `${buttonStyle()};text-decoration:none`;
        actions.appendChild(link);
      }
    }
    actions.style.cssText = "display:flex;align-items:center;gap:8px";
    row.append(info, actions);
    return row;
  }

  private renderImportForm(form: HTMLDivElement): void {
    form.style.cssText = "display:flex;flex-direction:column;gap:10px";
    const title = document.createElement("h3");
    title.textContent = "Importar elevació raster";
    title.style.cssText = "margin:0;font-size:15px;color:#fff";
    const note = message("La font nova serà primària dins la seva cobertura; les fonts anteriors es conservaran com a fallback.");
    const name = labelledInput("Nom", "text", "Nom descriptiu del DEM", "raster-import-name");
    const ownership = labelledSelect("Propietat", [["managed", "Gestionada (copiar a la biblioteca)"], ["external", "Externa (no copiar ni eliminar)"]], "raster-import-ownership");
    const sourceBox = document.createElement("div");
    const renderSource = () => {
      sourceBox.replaceChildren();
      if (ownership.select.value === "external") {
        const path = labelledInput("Ruta absoluta", "text", "C:\\dades\\mi_dem.tif", "raster-import-external-path");
        path.input.oninput = () => {
          const textOptions = document.getElementById("raster-import-text-options") as HTMLDetailsElement | null;
          if (textOptions && /\.(txt|csv|xyz)$/i.test(path.input.value)) textOptions.open = true;
        };
        sourceBox.appendChild(path.root);
      } else {
        const label = document.createElement("label");
        label.textContent = "Fitxer o bundle";
        label.style.cssText = labelStyle();
        const input = document.createElement("input");
        input.type = "file";
        input.multiple = true;
        input.id = "raster-import-files";
        input.style.cssText = inputStyle();
        input.onchange = () => {
          this.importFiles = Array.from(input.files ?? []);
          this.importInspection = null;
          const textOptions = document.getElementById("raster-import-text-options") as HTMLDetailsElement | null;
          if (textOptions && this.importFiles.some(file => /\.(txt|csv|xyz)$/i.test(file.name))) {
            textOptions.open = true;
          }
        };
        const directoryLabel = document.createElement("label");
        directoryLabel.textContent = "o carpeta bundle (conserva sidecars i subdirectoris)";
        directoryLabel.style.cssText = labelStyle();
        const directory = document.createElement("input");
        directory.type = "file";
        directory.multiple = true;
        directory.setAttribute("webkitdirectory", "");
        directory.style.cssText = inputStyle();
        directory.onchange = () => {
          this.importFiles = Array.from(directory.files ?? []);
          this.importInspection = null;
        };
        sourceBox.append(label, input, directoryLabel, directory);
      }
    };
    ownership.select.onchange = () => {
      this.importFiles = [];
      this.importInspection = null;
      renderSource();
    };
    renderSource();
    form.append(title, note, name.root, ownership.root, sourceBox);
    if (this.importInspection) form.appendChild(this.renderInspection(this.importInspection));
    else form.appendChild(this.renderPreInspectionAdvanced());

    const actions = document.createElement("div");
    actions.style.cssText = "display:flex;justify-content:space-between;margin-top:4px";
    const back = actionButton("Tornar");
    back.onclick = () => void this.cancelImportSession();
    const rightSide = document.createElement("div");
    rightSide.style.cssText = "display:flex;align-items:center;gap:12px;";

    const statusContainer = document.createElement("div");
    statusContainer.style.cssText = "display:flex;flex-direction:column;align-items:flex-end;gap:4px;margin-right:12px;";

    const statusMsg = document.createElement("div");
    statusMsg.id = "raster-import-status";
    statusMsg.style.cssText = "font-size:12px;color:var(--color-gold,#facc15);display:none;";

    const progressTrack = document.createElement("div");
    progressTrack.id = "raster-import-progress-track";
    progressTrack.style.cssText = "width:100%;height:4px;background:rgba(255,255,255,0.1);border-radius:2px;overflow:hidden;display:none;";
    
    const progressFill = document.createElement("div");
    progressFill.id = "raster-import-progress-fill";
    progressFill.style.cssText = "width:0%;height:100%;background:var(--color-gold,#facc15);transition:width 0.1s linear;";
    progressTrack.appendChild(progressFill);
    
    statusContainer.append(statusMsg, progressTrack);

    const cancelOp = actionButton("Cancel·lar procés");
    cancelOp.id = "raster-import-cancel";
    cancelOp.style.color = "#ff8a80";
    cancelOp.style.display = "none";
    cancelOp.onclick = () => {
      if (this.importAbortController) this.importAbortController.abort();
    };

    const submit = actionButton(
      this.importInspection?.subdatasets.length
        ? "Analitzar dataset seleccionat"
        : this.importInspection ? "Importar" : "Inspeccionar i continuar",
      true,
    );
    submit.id = "raster-import-submit";
    submit.disabled = this.importBusy;
    submit.onclick = () => void this.submitImport();

    rightSide.append(statusContainer, cancelOp, submit);
    actions.append(back, rightSide);
    form.appendChild(actions);
  }

  private renderPreInspectionAdvanced(): HTMLElement {
    const details = document.createElement("details");
    details.id = "raster-import-text-options";
    const summary = document.createElement("summary");
    summary.textContent = "Text/CSV: layout i georeferència";
    summary.style.cssText = "cursor:pointer;font-size:12px;color:#aaa";
    const layout = labelledSelect("Layout textual", [["", "Confirma el layout…"], ["matrix", "Matriu"], ["xyz", "XYZ regular"]], "raster-import-text-layout");
    const header = labelledSelect("Capçalera", [["", "Detectar i demanar si és ambigu"], ["false", "No"], ["true", "Sí"]], "raster-import-text-header");
    const crs = labelledInput("CRS", "text", "EPSG:25831", "raster-import-crs");
    const transform = labelledInput("Transform matriu (a,b,c,d,e,f)", "text", "5,0,0,0,-5,0", "raster-import-transform");
    details.append(summary, layout.root, header.root, crs.root, transform.root);
    return details;
  }

  private renderInspection(inspection: RasterInspection): HTMLElement {
    const section = document.createElement("section");
    section.style.cssText = "border:1px solid var(--color-border,#333);border-radius:6px;padding:12px";
    const metadata = message(`${inspection.driver} · ${inspection.width} × ${inspection.height} · ${inspection.sourceDtype ?? "dtype mixt"} · ${inspection.crs ?? "CRS pendent"}`);
    metadata.style.color = "#fff";
    section.appendChild(metadata);
    if (inspection.subdatasets.length) section.appendChild(labelledSelect("Dataset", inspection.subdatasets.map(value => [value, value]), "raster-import-subdataset").root);
    if (inspection.bands.length > 1) section.appendChild(labelledSelect(
      "Banda",
      [["", "Selecciona una banda…"], ...inspection.bands.map(value => [String(value.index), `${value.index} · ${value.description ?? value.dtype}`] as const)],
      "raster-import-band",
    ).root);
    const unit = labelledSelect("Unitat vertical", [["metre", "Metre"], ["international_foot", "Peu internacional"], ["us_survey_foot", "Peu topogràfic EUA"], ["custom", "Factor personalitzat"]], "raster-import-unit");
    unit.select.value = inspection.metadataSuggestions.verticalUnit ?? "metre";
    const custom = labelledInput("Factor a metres", "number", "0.001", "raster-import-custom-factor");
    custom.root.style.display = unit.select.value === "custom" ? "block" : "none";
    unit.select.onchange = () => custom.root.style.display = unit.select.value === "custom" ? "block" : "none";
    const confirmation = document.createElement("label");
    confirmation.style.cssText = "display:flex;gap:8px;align-items:center;font-size:12px;color:#fff;margin-top:8px";
    const checkbox = document.createElement("input");
    checkbox.type = "checkbox";
    checkbox.id = "raster-import-unit-confirmed";
    confirmation.append(checkbox, document.createTextNode("Confirmo explícitament aquesta unitat vertical"));
    section.append(unit.root, custom.root, confirmation);
    const advanced = document.createElement("details");
    advanced.open = !inspection.crs;
    const summary = document.createElement("summary");
    summary.textContent = "Avançat: CRS, transform i NoData";
    summary.style.cssText = "cursor:pointer;font-size:12px;color:#aaa;margin-top:8px";
    advanced.append(summary,
      labelledInput("CRS override", "text", "EPSG:25831", "raster-import-crs").root,
      labelledInput("Transform (a,b,c,d,e,f)", "text", "5,0,0,0,-5,0", "raster-import-transform").root,
      labelledInput("Bounds (oest,sud,est,nord)", "text", "0,0,1000,1000", "raster-import-bounds").root,
      labelledInput("NoData override", "number", "-9999", "raster-import-nodata").root,
    );
    section.appendChild(advanced);
    return section;
  }

  private async submitImport(): Promise<void> {
    if (this.importBusy) return;
    const preservedName = inputValue("raster-import-name");
    const preservedOwnership = selectValue("raster-import-ownership");
    this.importBusy = true;
    this.importAbortController = new AbortController();

    const activeSubmit = document.getElementById("raster-import-submit") as HTMLButtonElement | null;
    const cancelOp = document.getElementById("raster-import-cancel") as HTMLButtonElement | null;
    const statusMsg = document.getElementById("raster-import-status") as HTMLDivElement | null;

    if (activeSubmit) activeSubmit.style.display = "none";
    if (cancelOp) cancelOp.style.display = "block";
    const setStatus = (msg: string) => { if (statusMsg) { statusMsg.textContent = msg; statusMsg.style.display = "block"; } };
    setStatus("Iniciant processament...");

    try {
      if (!preservedName) throw new Error("Cal indicar un nom descriptiu.");
      if (!this.importId) {
        if (preservedOwnership === "managed" && !this.importFiles.length) throw new Error("Cal seleccionar almenys un fitxer.");
        const created = await requestJson("/api/raster-imports", {
          method: "POST", headers: { "Content-Type": "application/json" },
          signal: this.importAbortController.signal,
          body: JSON.stringify({ ownership: preservedOwnership, name: preservedName, externalPath: inputValue("raster-import-external-path") || null, fileCount: Math.max(1, this.importFiles.length) }),
        });
        this.importId = String(created.importId);
        for (let ordinal = 0; ordinal < this.importFiles.length; ordinal++) {
          const file = this.importFiles[ordinal]!;
          setStatus(`Pujant fitxer ${ordinal + 1} de ${this.importFiles.length}...`);
          
          const track = document.getElementById("raster-import-progress-track");
          if (track) track.style.display = "block";

          await uploadFileWithProgress(
            `/api/raster-imports/${this.importId}/files/${ordinal}`,
            file,
            { "X-TerraLab-Relative-Path": file.webkitRelativePath || file.name },
            this.importAbortController.signal,
            (percent) => {
              setStatus(`Pujant fitxer ${ordinal + 1} de ${this.importFiles.length}... (${percent}%)`);
              const fill = document.getElementById("raster-import-progress-fill");
              if (fill) fill.style.width = `${percent}%`;
            }
          );
          
          if (track) track.style.display = "none";
        }
      }
      if (!this.importInspection) {
        setStatus("Processant anàlisi i dataset...");
        const mainOrdinal = this.importFiles.length > 0 ? findMainRasterOrdinal(this.importFiles) : 0;
        const sourceName = this.importFiles[mainOrdinal]?.name ?? inputValue("raster-import-external-path");
        const text = /\.(txt|csv|xyz)$/i.test(sourceName);
        const headerChoice = selectValue("raster-import-text-header");
        const textOptions = text ? {
          layout: selectValue("raster-import-text-layout") || null,
          hasHeader: headerChoice === "" ? null : headerChoice === "true",
          crs: inputValue("raster-import-crs") || null,
          transform: parseTransform(inputValue("raster-import-transform")),
        } : undefined;
        this.importInspection = await requestJson(`/api/raster-imports/${this.importId}/inspect`, {
          method: "POST", headers: { "Content-Type": "application/json" },
          signal: this.importAbortController.signal,
          body: JSON.stringify({ fileOrdinal: mainOrdinal, textOptions }),
        }) as RasterInspection;
        this.elevationImportForm = null;
        this.renderList();
        const renderedName = document.getElementById("raster-import-name") as HTMLInputElement | null;
        if (renderedName) renderedName.value = preservedName;
        return;
      }
      const selectedSubdataset = selectValue("raster-import-subdataset") || null;
      if (selectedSubdataset && selectedSubdataset !== this.importInspectedSubdataset) {
        setStatus("Processant dataset seleccionat...");
        this.importInspection = await requestJson(`/api/raster-imports/${this.importId}/inspect`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          signal: this.importAbortController.signal,
          body: JSON.stringify({ fileOrdinal: this.importFiles.length > 0 ? findMainRasterOrdinal(this.importFiles) : 0, subdataset: selectedSubdataset }),
        }) as RasterInspection;
        this.importInspectedSubdataset = selectedSubdataset;
        this.elevationImportForm = null;
        this.renderList();
        const renderedName = document.getElementById("raster-import-name") as HTMLInputElement | null;
        if (renderedName) renderedName.value = preservedName;
        return;
      }
      setStatus("Consolidant importació...");
      const unit = selectValue("raster-import-unit");
      const bandChoice = selectValue("raster-import-band");
      if (this.importInspection.bands.length > 1 && !bandChoice) {
        throw new Error("Cal seleccionar explícitament una banda.");
      }
      const overrides: Record<string, unknown> = { provenance: "import-confirmation" };
      const crs = inputValue("raster-import-crs");
      const transform = parseTransform(inputValue("raster-import-transform"));
      const bounds = parseBounds(inputValue("raster-import-bounds"));
      const nodata = inputValue("raster-import-nodata");
      if (crs) overrides.crs = crs;
      if (transform) overrides.transform = transform;
      if (bounds) overrides.bounds = bounds;
      if (nodata) overrides.nodata = Number(nodata);
      await requestJson(`/api/raster-imports/${this.importId}/commit`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        signal: this.importAbortController.signal,
        body: JSON.stringify({
          name: preservedName,
          bandIndex: Number(bandChoice || this.importInspection.bands[0]?.index),
          subdataset: this.importInspectedSubdataset,
          verticalUnit: unit,
          unitConfirmed: (document.getElementById("raster-import-unit-confirmed") as HTMLInputElement | null)?.checked === true,
          customUnitToMetre: unit === "custom" ? Number(inputValue("raster-import-custom-factor")) : null,
          overrides,
        }),
      });
      this.resetImportState();
      this.manager.requestCatalog();
      this.renderFooter();
      this.renderList();
    } catch (error) {
      if ((error as Error).name === "AbortError") {
        window.alert("Operació cancel·lada per l'usuari.");
      } else {
        window.alert(error instanceof Error ? error.message : String(error));
      }
    } finally {
      this.importBusy = false;
      this.importAbortController = null;
      if (activeSubmit) { activeSubmit.disabled = false; activeSubmit.style.display = "block"; }
      if (cancelOp) cancelOp.style.display = "none";
      if (statusMsg) statusMsg.style.display = "none";
    }
  }

  private async cancelImportSession(): Promise<void> {
    const importId = this.importId;
    this.resetImportState();
    if (importId) {
      try { await fetch(`/api/raster-imports/${importId}`, { method: "DELETE" }); } catch { /* recoverable staging remains */ }
    }
    this.renderFooter();
    this.renderList();
  }

  private resetImportState(): void {
    this.importId = null;
    this.importInspection = null;
    this.importInspectedSubdataset = null;
    this.importFiles = [];
    this.importStates = {};
    this.elevationImportForm = null;
  }

  private async releaseCategoricalImport(): Promise<void> {
    const view = this.categoricalImport;
    this.categoricalImport = null;
    if (view) await view.cancel();
  }
}

function tabButton(label: string, active: boolean, domain: boolean): HTMLButtonElement {
  const button = document.createElement("button");
  button.textContent = label;
  button.style.cssText = `flex:${domain ? "1" : "0 0 auto"};padding:${domain ? "12px 16px" : "10px 16px"};font-size:${domain ? "13px" : "12px"};background:${active ? "var(--color-surface-raised,#222)" : "transparent"};color:${active ? "var(--color-gold,#facc15)" : "var(--color-text-muted,#888)"};border:0;border-bottom:2px solid ${active ? "var(--color-gold,#facc15)" : "transparent"};cursor:pointer`;
  return button;
}

function message(text: string): HTMLDivElement {
  const value = document.createElement("div");
  value.textContent = text;
  value.style.cssText = "font-size:12px;color:var(--color-text-dim,#aaa)";
  return value;
}

function appendFact(parent: HTMLElement, text: string): void {
  if (!text) return;
  const line = document.createElement("div");
  line.textContent = text;
  line.style.marginBottom = "4px";
  parent.appendChild(line);
}

function formatBytes(bytes: number | null | undefined): string {
  if (!bytes) return "Mida desconeguda";
  const mib = bytes / 1048576;
  return mib > 1024 ? `${(mib / 1024).toFixed(2)} GB` : `${mib.toFixed(1)} MB`;
}

function buttonStyle(primary = false): string {
  return `padding:7px 14px;border-radius:4px;cursor:pointer;border:1px solid ${primary ? "var(--color-gold,#facc15)" : "var(--color-border,#333)"};background:${primary ? "var(--color-gold,#facc15)" : "transparent"};color:${primary ? "#111" : "var(--color-text-bright,#fff)"};font-size:12px`;
}

function actionButton(text: string, primary = false): HTMLButtonElement {
  const button = document.createElement("button");
  button.textContent = text;
  button.style.cssText = buttonStyle(primary);
  return button;
}

function labelStyle(): string {
  return "display:block;font-size:11px;color:var(--color-text-dim,#aaa);margin:8px 0 4px";
}

function inputStyle(): string {
  return "box-sizing:border-box;width:100%;padding:7px 8px;border-radius:4px;border:1px solid var(--color-border,#333);background:var(--color-surface,#1a1a1a);color:var(--color-text-bright,#fff);font-size:12px";
}

function labelledInput(labelText: string, type: string, placeholder: string, id: string): { root: HTMLDivElement; input: HTMLInputElement } {
  const root = document.createElement("div");
  const label = document.createElement("label");
  label.textContent = labelText;
  label.htmlFor = id;
  label.style.cssText = labelStyle();
  const input = document.createElement("input");
  input.type = type;
  input.placeholder = placeholder;
  input.id = id;
  input.style.cssText = inputStyle();
  root.append(label, input);
  return { root, input };
}

function labelledSelect(labelText: string, options: readonly (readonly [string, string])[], id: string): { root: HTMLDivElement; select: HTMLSelectElement } {
  const root = document.createElement("div");
  const label = document.createElement("label");
  label.textContent = labelText;
  label.htmlFor = id;
  label.style.cssText = labelStyle();
  const select = document.createElement("select");
  select.id = id;
  select.style.cssText = inputStyle();
  for (const [value, text] of options) {
    const option = document.createElement("option");
    option.value = value;
    option.textContent = text;
    select.appendChild(option);
  }
  root.append(label, select);
  return { root, select };
}

function inputValue(id: string): string {
  return (document.getElementById(id) as HTMLInputElement | null)?.value.trim() ?? "";
}

function selectValue(id: string): string {
  return (document.getElementById(id) as HTMLSelectElement | null)?.value ?? "";
}

function parseTransform(value: string): number[] | null {
  if (!value) return null;
  const values = value.split(",").map(Number);
  if (values.length !== 6 || values.some(item => !Number.isFinite(item))) throw new Error("La transformació ha de contenir sis nombres separats per comes.");
  return values;
}

function parseBounds(value: string): number[] | null {
  if (!value) return null;
  const values = value.split(",").map(Number);
  if (values.length !== 4 || values.some(item => !Number.isFinite(item)) || values[2]! <= values[0]! || values[3]! <= values[1]!) {
    throw new Error("Els bounds han de ser oest,sud,est,nord amb extents positius.");
  }
  return values;
}

async function requestJson(url: string, init: RequestInit): Promise<any> {
  const response = await fetch(url, init);
  if (!response.ok) throw new Error((await response.text()) || `HTTP ${response.status}`);
  return response.json();
}

function findMainRasterOrdinal(files: File[]): number {
  if (files.length <= 1) return 0;
  const rasterExts = [".tif", ".tiff", ".vrt", ".nc", ".hgt", ".asc", ".dt0", ".dt1", ".dt2", ".dem", ".img", ".jp2"];
  const exactMatches = files.findIndex(f => rasterExts.some(ext => f.name.toLowerCase().endsWith(ext)));
  if (exactMatches !== -1) return exactMatches;
  const textExts = [".txt", ".csv", ".xyz"];
  const textMatches = files.findIndex(f => textExts.some(ext => f.name.toLowerCase().endsWith(ext)));
  if (textMatches !== -1) return textMatches;
  return 0;
}

function uploadFileWithProgress(
  url: string,
  file: File,
  headers: Record<string, string>,
  signal: AbortSignal | undefined | null,
  onProgress: (percent: number) => void
): Promise<any> {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open("PUT", url);
    for (const [key, value] of Object.entries(headers)) xhr.setRequestHeader(key, value);

    if (signal) {
      signal.addEventListener("abort", () => {
        xhr.abort();
        reject(new DOMException("Aborted", "AbortError"));
      });
    }

    xhr.upload.onprogress = (e) => {
      if (e.lengthComputable) {
        onProgress(Math.floor((e.loaded / e.total) * 100));
      }
    };

    xhr.onload = () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        resolve(xhr.response ? JSON.parse(xhr.response) : null);
      } else {
        reject(new Error(xhr.responseText || `HTTP ${xhr.status}`));
      }
    };

    xhr.onerror = () => reject(new Error("Network error"));
    xhr.send(file);
  });
}
