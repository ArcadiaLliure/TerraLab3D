import type {
  HorizonProfileSettingsMessage,
  HorizonStatusMessage,
} from "../../../contracts/horizon_contracts";

type HorizonSettings = Omit<HorizonProfileSettingsMessage, "type">;

export interface EarthPageOptions {
  onHorizonSettings?: (settings: HorizonSettings) => void;
  onRegenerate?: (settings: HorizonSettings) => void;
  onCancel?: () => void;
  onSurfaceModeChanged?: (mode: string) => void;
}

const SETTINGS_DEBOUNCE_MS = 2_000;

interface ProgressBlock {
  element: HTMLDivElement;
  update: (params: {
    percent: number | null;
    statusText: string;
    detailsText: string;
    isError: boolean;
    isSuccess: boolean;
  }) => void;
}

/**
 * Controls and reports the observer-centred terrain profile.
 *
 * The backend owns automatic startup/location bakes. This page only adjusts
 * their settings and provides an explicit force-regeneration action.
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
  private readonly surfaceModeInput: HTMLSelectElement;
  private readonly cancelButton: HTMLButtonElement;
  
  private readonly horizonProgress: ProgressBlock;
  private readonly surfaceProgress: ProgressBlock;

  private settingsTimer: ReturnType<typeof setTimeout> | null = null;

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
      "Topografia real del terreny i perfil d’horitzó calculats automàticament per a l’observador.";
    this.element.appendChild(description);

    const observerGroup = this.createGroup("Terreny de l’observador");
    this.observerStatus = document.createElement("div");
    this.observerStatus.style.cssText = "font-size:10px;line-height:1.55;color:var(--color-text-muted);";
    this.observerStatus.textContent = "Esperant la ubicació i l’elevació DEM…";
    observerGroup.appendChild(this.observerStatus);
    this.element.appendChild(observerGroup);

    const horizonGroup = this.createGroup("Perfil topogràfic");

    const enabledRow = this.createRow();
    const enabledLabel = document.createElement("label");
    enabledLabel.htmlFor = "earth-horizon-enabled";
    enabledLabel.textContent = "Horitzó real";
    this.enabledInput = document.createElement("input");
    this.enabledInput.id = "earth-horizon-enabled";
    this.enabledInput.type = "checkbox";
    this.enabledInput.checked = true;
    this.enabledInput.addEventListener("change", () => this.emitSettingsImmediately());
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
      this.updateControlLabels();
      this.scheduleSettings();
    });
    horizonGroup.append(stepLabelRow, this.angularStepInput);

    const actionRow = document.createElement("div");
    actionRow.style.cssText = "display:flex;gap:6px;margin-top:2px;";
    const regenerateButton = this.createButton("Regenerar ara");
    regenerateButton.title = "Descarta la memòria cau i torna a calcular el perfil";
    regenerateButton.addEventListener("click", () => {
      this.clearSettingsTimer();
      this.options.onRegenerate?.(this.currentSettings());
    });
    this.cancelButton = this.createButton("Cancel·lar");
    this.cancelButton.disabled = true;
    this.cancelButton.addEventListener("click", () => this.options.onCancel?.());
    actionRow.append(regenerateButton, this.cancelButton);
    horizonGroup.appendChild(actionRow);

    this.horizonProgress = this.createProgressBlock();
    this.horizonProgress.update({
      percent: null,
      statusText: "El càlcul començarà automàticament quan el DEM estigui disponible.",
      detailsText: "",
      isError: false,
      isSuccess: false,
    });
    horizonGroup.appendChild(this.horizonProgress.element);

    this.element.appendChild(horizonGroup);

    const surfaceGroup = this.createGroup("Aspecte de la superfície");

    const modeRow = this.createRow();
    const modeLabel = document.createElement("label");
    modeLabel.htmlFor = "earth-surface-mode";
    modeLabel.textContent = "Estil visual";
    this.surfaceModeInput = document.createElement("select");
    this.surfaceModeInput.id = "earth-surface-mode";
    this.surfaceModeInput.style.cssText = this.inputStyle();
    this.surfaceModeInput.innerHTML = `
      <option value="terrain-fallback" selected>Paleta base del relleu</option>
      <option value="categorical">Cobertura categòrica</option>
    `;
    this.surfaceModeInput.addEventListener("change", () => {
      this.options.onSurfaceModeChanged?.(this.surfaceModeInput.value);
    });
    modeRow.append(modeLabel, this.surfaceModeInput);
    surfaceGroup.appendChild(modeRow);

    this.surfaceProgress = this.createProgressBlock();
    this.surfaceProgress.update({
      percent: null,
      statusText: "Malla base (sense cobertura categòrica).",
      detailsText: "",
      isError: false,
      isSuccess: false,
    });
    surfaceGroup.appendChild(this.surfaceProgress.element);

    this.element.appendChild(surfaceGroup);

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
    const progress = status.progress === null ? null : Math.max(0, Math.min(1, status.progress)) * 100;
    
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

    this.horizonProgress.update({
      percent: progress,
      statusText: phaseLabels[status.phase],
      detailsText: details.join(" · "),
      isError: status.phase === "error",
      isSuccess: status.phase === "completed",
    });

    const busy = ["queued", "opening_source", "sampling", "reducing", "publishing"].includes(status.phase);
    this.cancelButton.disabled = !busy;
  }

  /** Reports the configured appearance layer; it is separate from the DEM. */
  public updateTerrainSurface(status: {
    activeSource?: string;
    phase?: string;
    percent?: number;
    cleared?: boolean;
    completed?: boolean;
    validTiles?: number;
    emptyTiles?: number;
    failedTiles?: number;
    validPixels?: number;
  }): void {
    if (status.cleared === true) {
      this.surfaceProgress.update({
        percent: null,
        statusText: "Malla base (sense cobertura categòrica).",
        detailsText: "",
        isError: false,
        isSuccess: false,
      });
      return;
    }
    
    const isError = status.phase?.toLowerCase().includes("error") ?? false;
    const isSuccess = status.completed === true 
      && status.percent === 100 
      && (status.validTiles ?? 0) > 0 
      && (status.validPixels ?? 0) > 0 
      && (status.failedTiles ?? 0) === 0;

    const details: string[] = [];
    if (status.activeSource) details.push(`Font: ${status.activeSource}`);
    if (status.validTiles) details.push(`Tessel·les: ${status.validTiles}`);
    if (status.failedTiles) details.push(`Errors: ${status.failedTiles}`);
    if (status.emptyTiles) details.push(`Buides: ${status.emptyTiles}`);

    this.surfaceProgress.update({
      percent: status.percent ?? null,
      statusText: status.phase ? `Estat: ${status.phase}` : "Esperant dades...",
      detailsText: details.join(" · "),
      isError: isError,
      isSuccess: isSuccess,
    });
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

  private createProgressBlock(): ProgressBlock {
    const container = document.createElement("div");
    container.style.cssText = "display:flex;flex-direction:column;gap:4px;margin-top:6px;";
    
    const statusLabel = document.createElement("div");
    statusLabel.style.cssText = "font-size:10px;color:var(--color-text-bright);";
    
    const track = document.createElement("div");
    track.style.cssText = "height:3px;overflow:hidden;border-radius:2px;background:var(--color-surface);margin-top:2px;";
    
    const progressBar = document.createElement("div");
    progressBar.style.cssText = "width:0%;height:100%;background:var(--color-gold);transition:width 120ms linear;";
    track.appendChild(progressBar);

    const detailsLabel = document.createElement("div");
    detailsLabel.style.cssText = "font-size:9px;line-height:1.45;color:var(--color-text-muted);overflow-wrap:anywhere;";
    
    container.append(statusLabel, track, detailsLabel);

    return {
      element: container,
      update: (params) => {
        let text = params.statusText;
        if (params.percent !== null && params.percent < 100 && !params.isError && !params.isSuccess) {
          text += ` · ${params.percent.toFixed(0)}%`;
        }
        statusLabel.textContent = text;
        statusLabel.style.color = params.isError ? "#ff8a80" : (params.isSuccess ? "#4ade80" : "var(--color-text-bright)");
        detailsLabel.textContent = params.detailsText;
        
        progressBar.style.width = `${params.percent ?? 0}%`;
        if (params.isError || params.percent === null) {
          progressBar.style.background = "transparent";
        } else if (params.isSuccess) {
          progressBar.style.background = "#4ade80";
        } else {
          progressBar.style.background = "var(--color-gold)";
        }
      }
    };
  }
}
