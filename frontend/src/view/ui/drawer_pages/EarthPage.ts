import type {
  HorizonProfileSettingsMessage,
  HorizonStatusMessage,
} from "../../../contracts/horizon_contracts";
import type {
  SurfaceCatalogMessage,
  SurfaceStatusMessage,
  SurfaceCatalogSourceEntry,
} from "../../../contracts/bridge_messages";

type HorizonSettings = Omit<HorizonProfileSettingsMessage, "type">;

export interface SurfaceLegendItem {
  readonly classId: number;
  readonly name: string;
  readonly rgba: readonly [number, number, number, number];
  readonly isNodata?: boolean;
}

export interface EarthPageOptions {
  onHorizonSettings?: (settings: HorizonSettings) => void;
  onRegenerate?: (settings: HorizonSettings) => void;
  onCancel?: () => void;
  onSurfaceMode?: (mode: "base" | "categorical_original") => void;
  onSurfaceSource?: (sourceId: string | null) => void;
  /** Fires immediately on combobox change to update shader without waiting for backend. */
  onLocalSurfaceModeSwitch?: (mode: "base" | "categorical_original") => void;
}

const SETTINGS_DEBOUNCE_MS = 2_000;

/**
 * Controls and reports the observer-centred terrain profile and land cover surface representation.
 */
export class EarthPage {
  private readonly element: HTMLDivElement;
  private readonly enabledInput: HTMLInputElement;
  private readonly rangeModeInput: HTMLSelectElement;
  private readonly radiusInput: HTMLInputElement;
  private readonly radiusValue: HTMLSpanElement;
  private readonly angularStepInput: HTMLInputElement;
  private readonly angularStepValue: HTMLSpanElement;
  private readonly observerStatus: HTMLDivElement;
  private readonly bakeStatus: HTMLDivElement;
  private readonly bakeDetail: HTMLDivElement;
  private readonly progressBar: HTMLDivElement;
  private readonly cancelButton: HTMLButtonElement;

  // Surface controls (Pas 17)
  private readonly surfaceModeSelect: HTMLSelectElement;
  private readonly surfaceSourceSelect: HTMLSelectElement;
  private readonly surfaceStatusDiv: HTMLDivElement;
  private readonly surfaceProgressBar: HTMLDivElement;
  private readonly surfaceLegendContainer: HTMLDivElement;

  private settingsTimer: ReturnType<typeof setTimeout> | null = null;
  private currentLegend: SurfaceLegendItem[] = [];

  constructor(private readonly options: EarthPageOptions = {}) {
    this.element = document.createElement("div");
    this.element.style.cssText = `
      display: flex;
      flex-direction: column;
      gap: 12px;
      color: var(--color-text-dim);
      font-size: var(--font-size-base);
    `;

    const description = document.createElement("p");
    description.textContent =
      "Topografia real del terreny, perfil d’horitzó i cobertura del sòl calculats per a l’observador.";
    this.element.appendChild(description);

    const observerGroup = this.createGroup("Terreny de l’observador");
    this.observerStatus = document.createElement("div");
    this.observerStatus.style.cssText = "font-size:10px;line-height:1.55;color:var(--color-text-muted);";
    this.observerStatus.textContent = "Esperant la ubicació i l’elevació DEM…";
    observerGroup.appendChild(this.observerStatus);
    this.element.appendChild(observerGroup);

    // ─── Surface Appearance Controls (Pas 17) ───────────────────────────
    const surfaceGroup = this.createGroup("Aspecte de la superfície");

    // Mode Selector
    const modeRow = this.createRow();
    const modeLabel = document.createElement("label");
    modeLabel.htmlFor = "earth-surface-mode";
    modeLabel.textContent = "Estil de representació";
    this.surfaceModeSelect = document.createElement("select");
    this.surfaceModeSelect.id = "earth-surface-mode";
    this.surfaceModeSelect.style.cssText = this.inputStyle();
    this.surfaceModeSelect.innerHTML = `
      <option value="base" selected>Terreny base (Relleu)</option>
      <option value="categorical_original">Cobertura del sòl · Original</option>
    `;
    this.surfaceModeSelect.addEventListener("change", () => {
      const mode = this.surfaceModeSelect.value as "base" | "categorical_original";
      console.log(`INTERN: Frontend (EarthPage.ts:95: Estil de representació -> Canvi de mode de superfície: ${mode})`);
      this.updateLegendVisibility(mode);
      this.options.onLocalSurfaceModeSwitch?.(mode);
      this.options.onSurfaceMode?.(mode);
    });
    modeRow.append(modeLabel, this.surfaceModeSelect);
    surfaceGroup.appendChild(modeRow);

    // Source Selector
    const sourceRow = this.createRow();
    const sourceLabel = document.createElement("label");
    sourceLabel.htmlFor = "earth-surface-source";
    sourceLabel.textContent = "Font de cobertura";
    this.surfaceSourceSelect = document.createElement("select");
    this.surfaceSourceSelect.id = "earth-surface-source";
    this.surfaceSourceSelect.style.cssText = this.inputStyle();
    this.surfaceSourceSelect.innerHTML = `<option value="">Automàtica (segons prioritat)</option>`;
    this.surfaceSourceSelect.addEventListener("change", () => {
      const val = this.surfaceSourceSelect.value;
      console.log(`INTERN: Frontend (EarthPage.ts:114: Font de cobertura -> Canvi de font de cobertura: ${val || "Automàtica"})`);
      this.options.onSurfaceSource?.(val === "" ? null : val);
    });
    sourceRow.append(sourceLabel, this.surfaceSourceSelect);
    surfaceGroup.appendChild(sourceRow);

    // Status Detail
    this.surfaceStatusDiv = document.createElement("div");
    this.surfaceStatusDiv.style.cssText =
      "font-size:10px;line-height:1.5;color:var(--color-text-muted);background:var(--color-surface);padding:6px 8px;border-radius:4px;border:1px solid var(--color-border);";
    this.surfaceStatusDiv.textContent = "Esperant dades de cobertura del sòl…";

    // Surface Progress Bar
    const surfaceProgressTrack = document.createElement("div");
    surfaceProgressTrack.style.cssText =
      "height:4px;background:var(--color-border);border-radius:2px;overflow:hidden;margin-top:2px;";
    this.surfaceProgressBar = document.createElement("div");
    this.surfaceProgressBar.style.cssText =
      "height:100%;width:0%;background:var(--color-accent);transition:width 0.25s ease-out;";
    surfaceProgressTrack.appendChild(this.surfaceProgressBar);

    surfaceGroup.append(this.surfaceStatusDiv, surfaceProgressTrack);

    // Legend
    this.surfaceLegendContainer = document.createElement("div");
    this.surfaceLegendContainer.style.cssText = `
      display: none;
      flex-direction: column;
      gap: 4px;
      max-height: 180px;
      overflow-y: auto;
      padding: 6px;
      background: var(--color-surface);
      border: 1px solid var(--color-border);
      border-radius: 4px;
      font-size: 9px;
    `;
    surfaceGroup.appendChild(this.surfaceLegendContainer);

    this.element.appendChild(surfaceGroup);

    // ─── Topographic Horizon Profile ─────────────────────────────────────
    const horizonGroup = this.createGroup("Perfil topogràfic");

    const enabledRow = this.createRow();
    const enabledLabel = document.createElement("label");
    enabledLabel.htmlFor = "earth-horizon-enabled";
    enabledLabel.textContent = "Horitzó real";
    this.enabledInput = document.createElement("input");
    this.enabledInput.id = "earth-horizon-enabled";
    this.enabledInput.type = "checkbox";
    this.enabledInput.checked = true;
    this.enabledInput.addEventListener("change", () => {
      console.log(`INTERN: Frontend (EarthPage.ts:161: Horitzó real -> Commutar visibilitat horitzó topogràfic: ${this.enabledInput.checked})`);
      this.emitSettingsImmediately();
    });
    enabledRow.append(enabledLabel, this.enabledInput);
    horizonGroup.appendChild(enabledRow);

    const rangeRow = this.createRow();
    const rangeLabel = document.createElement("label");
    rangeLabel.htmlFor = "earth-horizon-range";
    rangeLabel.textContent = "Abast topogràfic";
    this.rangeModeInput = document.createElement("select");
    this.rangeModeInput.id = "earth-horizon-range";
    this.rangeModeInput.style.cssText = this.inputStyle();
    this.rangeModeInput.innerHTML = `
      <option value="auto">Automàtic</option>
      <option value="manual" selected>Manual</option>
    `;
    this.rangeModeInput.addEventListener("change", () => {
      console.log(`INTERN: Frontend (EarthPage.ts:178: Abast topogràfic -> Mode d'abast seleccionat: ${this.rangeModeInput.value})`);
      this.radiusInput.disabled = this.rangeModeInput.value === "auto";
      this.scheduleSettings();
    });
    rangeRow.append(rangeLabel, this.rangeModeInput);
    horizonGroup.appendChild(rangeRow);

    const radiusLabelRow = this.createRow();
    const radiusLabel = document.createElement("label");
    radiusLabel.htmlFor = "earth-horizon-radius";
    radiusLabel.textContent = "Profunditat";
    this.radiusValue = document.createElement("span");
    this.radiusValue.style.color = "var(--color-text-bright)";
    radiusLabelRow.append(radiusLabel, this.radiusValue);
    this.radiusInput = document.createElement("input");
    this.radiusInput.id = "earth-horizon-radius";
    this.radiusInput.type = "range";
    this.radiusInput.min = "1";
    this.radiusInput.max = "530";
    this.radiusInput.step = "1";
    this.radiusInput.value = "150";
    this.radiusInput.title = "Profunditat topogràfica visible, en quilòmetres";
    this.radiusInput.addEventListener("input", () => {
      console.log(`INTERN: Frontend (EarthPage.ts:202: Profunditat -> Canvi de radi de visió: ${this.radiusInput.value} km)`);
      this.updateControlLabels();
      this.scheduleSettings();
    });
    horizonGroup.append(radiusLabelRow, this.radiusInput);

    const stepLabelRow = this.createRow();
    const stepLabel = document.createElement("label");
    stepLabel.htmlFor = "earth-horizon-step";
    stepLabel.textContent = "Precisió dels raigs";
    this.angularStepValue = document.createElement("span");
    this.angularStepValue.style.color = "var(--color-text-bright)";
    stepLabelRow.append(stepLabel, this.angularStepValue);
    this.angularStepInput = document.createElement("input");
    this.angularStepInput.id = "earth-horizon-step";
    this.angularStepInput.type = "range";
    this.angularStepInput.min = "5";
    this.angularStepInput.max = "5000";
    this.angularStepInput.step = "5";
    this.angularStepInput.value = "250";
    this.angularStepInput.title = "Separació angular dels raigs; un valor menor dona més detall";
    this.angularStepInput.addEventListener("input", () => {
      console.log(`INTERN: Frontend (EarthPage.ts:225: Precisió dels raigs -> Canvi de pas angular: ${this.formatDegrees(Number(this.angularStepInput.value) / 1000)})`);
      this.updateControlLabels();
      this.scheduleSettings();
    });
    horizonGroup.append(stepLabelRow, this.angularStepInput);

    const actionRow = document.createElement("div");
    actionRow.style.cssText = "display:flex;gap:6px;margin-top:2px;";
    const regenerateButton = this.createButton("Regenerar ara");
    regenerateButton.title = "Descarta la memòria cau i torna a calcular el perfil";
    regenerateButton.addEventListener("click", () => {
      console.log("INTERN: Frontend (EarthPage.ts:236: Regenerar ara -> Forçar recalculació del perfil d'horitzó)");
      this.clearSettingsTimer();
      this.options.onRegenerate?.(this.currentSettings());
    });
    this.cancelButton = this.createButton("Cancel·lar");
    this.cancelButton.disabled = true;
    this.cancelButton.addEventListener("click", () => {
      console.log("INTERN: Frontend (EarthPage.ts:243: Cancel·lar -> Cancel·lar càlcul de perfil d'horitzó)");
      this.options.onCancel?.();
    });

    actionRow.append(regenerateButton, this.cancelButton);
    horizonGroup.appendChild(actionRow);

    const progressTrack = document.createElement("div");
    progressTrack.style.cssText = `
      height: 3px;
      overflow: hidden;
      border-radius: 2px;
      background: var(--color-surface);
    `;
    this.progressBar = document.createElement("div");
    this.progressBar.style.cssText = `
      width: 0%;
      height: 100%;
      background: var(--color-gold);
      transition: width 120ms linear;
    `;
    progressTrack.appendChild(this.progressBar);
    horizonGroup.appendChild(progressTrack);

    this.bakeStatus = document.createElement("div");
    this.bakeStatus.style.cssText = "font-size:10px;color:var(--color-text-bright);";
    this.bakeStatus.textContent = "El càlcul començarà automàticament quan el DEM estigui disponible.";
    this.bakeDetail = document.createElement("div");
    this.bakeDetail.style.cssText = "font-size:9px;line-height:1.45;color:var(--color-text-muted);overflow-wrap:anywhere;";
    horizonGroup.append(this.bakeStatus, this.bakeDetail);
    this.element.appendChild(horizonGroup);

    this.updateControlLabels();
  }

  public mount(container: HTMLElement): void {
    container.appendChild(this.element);
  }

  public updateObserver(
    latitudeDeg: number,
    longitudeDeg: number,
    elevationM: number | null,
    heightOffsetM: number,
    effectiveHeightM: number | null,
    source: string,
  ): void {
    const elevation = elevationM === null ? "No disponible" : `${elevationM.toFixed(1)} m`;
    const effective = effectiveHeightM === null ? "No disponible" : `${effectiveHeightM.toFixed(1)} m`;
    this.observerStatus.textContent = [
      `${latitudeDeg.toFixed(5)}°, ${longitudeDeg.toFixed(5)}°`,
      `Elevació DEM: ${elevation}`,
      `Ull: +${heightOffsetM.toFixed(1)} m · alçada ocular: ${effective}`,
      `Font: ${source}`,
    ].join("\n");
    this.observerStatus.style.whiteSpace = "pre-line";
  }

  public updateHorizonStatus(status: HorizonStatusMessage): void {
    const progress = status.progress === null ? null : Math.max(0, Math.min(1, status.progress));
    this.progressBar.style.width = `${(progress ?? 0) * 100}%`;

    const phaseLabels: Record<HorizonStatusMessage["phase"], string> = {
      queued: "Càlcul programat",
      opening_source: "Obrint el terreny configurat",
      sampling: "Calculant la topografia",
      reducing: "Construint el perfil d’horitzó",
      publishing: "Actualitzant l’escena",
      completed: "Perfil topogràfic actualitzat",
      cancelled: "Càlcul cancel·lat",
      fallback: "Sense DEM: perfil pla provisional",
      error: "No s’ha pogut calcular el perfil",
    };
    const percent = progress === null || status.phase === "completed"
      ? ""
      : ` · ${(progress * 100).toFixed(0)}%`;
    this.bakeStatus.textContent = `${phaseLabels[status.phase]}${percent}`;
    this.bakeStatus.style.color = status.phase === "error"
      ? "#ff8a80"
      : status.phase === "completed" ? "#4ade80" : "var(--color-text-bright)";

    const details: string[] = [];
    if (status.quality) details.push(this.qualityLabel(status.quality));
    if (status.resolvedFraction !== undefined) {
      details.push(`cobertura DEM ${(status.resolvedFraction * 100).toFixed(1)}%`);
    }
    if (status.visibleRadiusM !== undefined) {
      details.push(`abast ${(status.visibleRadiusM / 1_000).toFixed(0)} km`);
    }
    if (status.angularStepDeg !== undefined) {
      details.push(`pas ${this.formatDegrees(status.angularStepDeg)}`);
    }
    if (status.sourceIds?.length) {
      details.push(`${status.sourceIds[0]}${status.sourceIds.length > 1 ? ` +${status.sourceIds.length - 1} fonts` : ""}`);
    }
    if (status.message) details.push(status.message);
    this.bakeDetail.textContent = details.join(" · ");

    const busy = ["queued", "opening_source", "sampling", "reducing", "publishing"].includes(status.phase);
    this.cancelButton.disabled = !busy;
  }

  public updateSurfaceCatalog(catalog: SurfaceCatalogMessage): void {
    const previous = this.surfaceSourceSelect.value;
    this.surfaceSourceSelect.innerHTML = `<option value="">Automàtica (segons prioritat)</option>`;
    for (const src of catalog.sources) {
      if (src.enabled) {
        const opt = document.createElement("option");
        opt.value = src.id;
        opt.textContent = `${src.name} (${src.resolutionM}m)`;
        if (catalog.selectedSourceId === src.id) opt.selected = true;
        this.surfaceSourceSelect.appendChild(opt);
      }
    }
    if (!catalog.selectedSourceId && previous) {
      this.surfaceSourceSelect.value = previous;
    }
    if (catalog.mode) {
      this.surfaceModeSelect.value = catalog.mode;
      this.updateLegendVisibility(catalog.mode as "base" | "categorical_original");
    }
  }

  public updateSurfaceStatus(status: SurfaceStatusMessage): void {
    if (status.mode) {
      this.surfaceModeSelect.value = status.mode;
      this.updateLegendVisibility(status.mode as "base" | "categorical_original");
    }
    const resolvedPct = (status.resolvedFraction * 100).toFixed(1);
    const fallbackPct = (status.fallbackFraction * 100).toFixed(1);
    const modeLabel = status.mode === "categorical_original" ? "Cobertura original" : "Terreny base";
    const lines = [
      `Mode: ${modeLabel}`,
      `Font efectiva: ${status.effectiveSource || "Cap font activa"}`,
      `Cobertura: ${resolvedPct}% (${status.sampleCount} vèrtexs)`,
    ];
    if (status.fallbackFraction > 0.001) {
      lines.push(`Fallback: ${fallbackPct}%`);
    }
    lines.push(`Memòria cau: ${status.cacheHits} encerts · ${(status.cacheBytes / 1024).toFixed(0)} KB`);
    this.surfaceStatusDiv.textContent = lines.join("\n");
    this.surfaceStatusDiv.style.whiteSpace = "pre-line";

    const pct = status.resolvedFraction * 100;
    this.surfaceProgressBar.style.width = `${Math.min(100, Math.max(0, pct))}%`;
  }

  public updateSurfaceProgress(fraction: number, message?: string): void {
    const pct = Math.min(100, Math.max(0, fraction * 100));
    this.surfaceProgressBar.style.width = `${pct}%`;
    if (message) {
      this.surfaceStatusDiv.textContent = message;
    }
  }


  public updateSurfaceLegend(legend: SurfaceLegendItem[]): void {
    this.currentLegend = legend;
    this.renderLegend();
  }

  public getLegendName(classId: number): string | null {
    const item = this.currentLegend.find(l => l.classId === classId);
    return item ? (item.name || `Classe ${classId}`) : null;
  }

  private updateLegendVisibility(mode: "base" | "categorical_original"): void {
    const show = mode === "categorical_original";
    
    // Llegenda i selector de font: només visibles en mode categòric
    this.surfaceLegendContainer.style.display = show ? "flex" : "none";
    if (this.surfaceSourceSelect.parentElement) {
      this.surfaceSourceSelect.parentElement.style.display = show ? "" : "none";
    }
    // La barra de progrés i l'status SEMPRE visibles (feedback de DEM o cobertura)
    
    if (show && this.currentLegend.length > 0) {
      this.renderLegend();
    }
  }

  private renderLegend(): void {
    this.surfaceLegendContainer.innerHTML = "";
    if (this.currentLegend.length === 0) {
      const empty = document.createElement("div");
      empty.textContent = "Sense classes actives";
      this.surfaceLegendContainer.appendChild(empty);
      return;
    }
    for (const item of this.currentLegend) {
      const row = document.createElement("div");
      row.style.cssText = "display:flex;align-items:center;gap:6px;";

      const swatch = document.createElement("span");
      const [r, g, b] = item.rgba;
      swatch.style.cssText = `
        display: inline-block;
        width: 10px;
        height: 10px;
        border-radius: 2px;
        background-color: rgb(${r}, ${g}, ${b});
        border: 1px solid rgba(255,255,255,0.2);
        flex-shrink: 0;
      `;

      const label = document.createElement("span");
      label.style.cssText = "color:var(--color-text-bright);overflow:hidden;text-overflow:ellipsis;white-space:nowrap;";
      label.textContent = item.name || `Classe ${item.classId}`;

      row.append(swatch, label);
      this.surfaceLegendContainer.appendChild(row);
    }
  }

  public dispose(): void {
    this.clearSettingsTimer();
    this.element.remove();
  }

  private currentSettings(): HorizonSettings {
    return {
      enabled: this.enabledInput.checked,
      rangeMode: this.rangeModeInput.value as "auto" | "manual",
      visibleRadiusKm: Number(this.radiusInput.value),
      angularStepDeg: Number(this.angularStepInput.value) / 1_000,
      atmosphericRefractionEnabled: true,
      effectiveEarthRadiusFactor: 7 / 6,
      maxSamplesPerRay: 4_096,
      memoryBudgetBytes: 128 * 1_024 * 1_024,
    };
  }

  private scheduleSettings(): void {
    this.clearSettingsTimer();
    this.settingsTimer = setTimeout(() => {
      this.settingsTimer = null;
      this.options.onHorizonSettings?.(this.currentSettings());
    }, SETTINGS_DEBOUNCE_MS);
  }

  private emitSettingsImmediately(): void {
    this.clearSettingsTimer();
    this.options.onHorizonSettings?.(this.currentSettings());
  }

  private clearSettingsTimer(): void {
    if (this.settingsTimer !== null) {
      clearTimeout(this.settingsTimer);
      this.settingsTimer = null;
    }
  }

  private updateControlLabels(): void {
    this.radiusValue.textContent = `${this.radiusInput.value} km`;
    this.angularStepValue.textContent = this.formatDegrees(Number(this.angularStepInput.value) / 1_000);
  }

  private formatDegrees(value: number): string {
    return `${value.toLocaleString("ca-ES", { maximumFractionDigits: 3 })}°`;
  }

  private qualityLabel(quality: NonNullable<HorizonStatusMessage["quality"]>): string {
    return ({
      REAL: "DEM real",
      PARTIAL_DEM: "DEM parcial",
      FLAT_FALLBACK: "perfil pla provisional",
      UNAVAILABLE: "no disponible",
      ERROR: "error",
    })[quality];
  }

  private createGroup(titleText: string): HTMLDivElement {
    const group = document.createElement("div");
    group.style.cssText = `
      background: var(--color-surface-raised);
      border: 1px solid var(--color-border);
      border-radius: var(--border-radius-md);
      padding: 10px;
      display: flex;
      flex-direction: column;
      gap: 8px;
    `;
    const title = document.createElement("div");
    title.style.cssText = "font-weight:600;color:var(--color-gold);font-size:11px;";
    title.textContent = titleText;
    group.appendChild(title);
    return group;
  }

  private createRow(): HTMLDivElement {
    const row = document.createElement("div");
    row.style.cssText = "display:flex;justify-content:space-between;align-items:center;gap:8px;font-size:10px;";
    return row;
  }

  private createButton(label: string): HTMLButtonElement {
    const button = document.createElement("button");
    button.type = "button";
    button.textContent = label;
    button.style.cssText = `
      padding: 4px 8px;
      color: var(--color-text-bright);
      background: var(--color-surface);
      border: 1px solid var(--color-border);
      border-radius: 4px;
      cursor: pointer;
      font-size: 10px;
    `;
    return button;
  }

  private inputStyle(): string {
    return "background:var(--color-surface);color:var(--color-text-bright);border:1px solid var(--color-border);border-radius:4px;padding:2px 4px;font-size:10px;";
  }
}
