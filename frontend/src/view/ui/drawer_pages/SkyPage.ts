import type { SkyEnvironmentSnapshot } from "../../../contracts/sky_environment_contracts";
import type {
  MoonSurfaceResourceDescriptor,
  SolarSystemSnapshot,
} from "../../../contracts/solar_system_contracts";

export interface SkyPageOptions {
  onStarLayerToggled?: (visible: boolean) => void;
  onAtmosphereToggled?: (enabled: boolean) => void;
  onLightPollutionToggled?: (enabled: boolean) => void;
  onLightPollutionModeChanged?: (mode: "automatic" | "bortle" | "magnitude") => void;
  onBortleClassChanged?: (bortle: number) => void;
  onMagnitudeLimitChanged?: (mag: number) => void;
  onPureColorsToggled?: (pure: boolean) => void;
  onSolarSystemVisibilityChanged?: (
    part: "system" | "sun" | "moon" | "planets",
    visible: boolean,
  ) => void;
  onMoonSurfaceToggled?: (enabled: boolean) => void;
}

export class SkyPage {
  private element: HTMLDivElement;
  private options: SkyPageOptions;
  
  // Elements UI que s'actualitzen dinàmicament
  private starSourceLabel!: HTMLSpanElement;
  private starCountLabel!: HTMLSpanElement;
  private starsToggleBtn!: HTMLButtonElement;
  private starsVisible = true;
  
  private atmoToggleBtn!: HTMLButtonElement;
  private pureColorsToggleBtn!: HTMLButtonElement;
  
  private lpToggleBtn!: HTMLButtonElement;
  private lpModeSelect!: HTMLSelectElement;
  private lpBortleInput!: HTMLInputElement;
  private lpMagInput!: HTMLInputElement;
  private lpBortleValue!: HTMLSpanElement;
  private lpMagValue!: HTMLSpanElement;
  private lpSourceLabel!: HTMLDivElement;
  private bortleContainer!: HTMLDivElement;
  private magContainer!: HTMLDivElement;
  private solarStatusLabel!: HTMLDivElement;
  private moonSurfaceStatusLabel!: HTMLDivElement;

  constructor(options: SkyPageOptions = {}) {
    this.options = options;

    this.element = document.createElement("div");
    this.element.style.cssText = `
      display: flex;
      flex-direction: column;
      gap: 12px;
      color: var(--color-text-dim);
      font-size: var(--font-size-base);
    `;

    const desc = document.createElement("p");
    desc.textContent = "Paràmetres de visualització de la volta celeste, atmosfera i contaminació lumínica.";
    this.element.appendChild(desc);

    this.buildSolarSystemGroup();
    this.buildAtmoGroup();
    this.buildLightPollutionGroup();
    this.buildStarGroup();
  }

  private buildSolarSystemGroup(): void {
    const [group, titleRow] = this.createGroup("Sistema solar");
    titleRow.appendChild(this.createToggleButton("Visible", "Ocult", true, (visible) => {
      this.options.onSolarSystemVisibilityChanged?.("system", visible);
    }));
    const labels: ReadonlyArray<["sun" | "moon" | "planets", string]> = [
      ["sun", "Sol"],
      ["moon", "Lluna"],
      ["planets", "Planetes"],
    ];
    for (const [part, label] of labels) {
      const row = document.createElement("div");
      row.style.cssText = "display:flex;justify-content:space-between;align-items:center;font-size:10px;";
      const text = document.createElement("span");
      text.textContent = label;
      row.append(text, this.createToggleButton("Visible", "Ocult", true, (visible) => {
        this.options.onSolarSystemVisibilityChanged?.(part, visible);
      }));
      group.appendChild(row);
    }
    const surfaceRow = document.createElement("div");
    surfaceRow.style.cssText = "display:flex;justify-content:space-between;align-items:center;font-size:10px;padding-left:12px;";
    const surfaceText = document.createElement("span");
    surfaceText.textContent = "Superfície LRO/LOLA";
    surfaceRow.append(surfaceText, this.createToggleButton("Activa", "Inactiva", true, (enabled) => {
      this.options.onMoonSurfaceToggled?.(enabled);
    }));
    group.appendChild(surfaceRow);
    this.moonSurfaceStatusLabel = document.createElement("div");
    this.moonSurfaceStatusLabel.style.cssText = "font-size:9px;color:var(--color-text-muted);padding-left:12px;";
    this.moonSurfaceStatusLabel.textContent = "surface unavailable";
    group.appendChild(this.moonSurfaceStatusLabel);
    this.solarStatusLabel = document.createElement("div");
    this.solarStatusLabel.style.cssText = "font-size:9px;color:var(--color-text-muted);line-height:1.4;";
    this.solarStatusLabel.textContent = "Efemèride: carregant…";
    group.appendChild(this.solarStatusLabel);
    this.element.appendChild(group);
  }

  private createGroup(titleText: string): [HTMLDivElement, HTMLDivElement] {
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

    const titleRow = document.createElement("div");
    titleRow.style.cssText = "display: flex; justify-content: space-between; align-items: center;";
    
    const title = document.createElement("div");
    title.style.cssText = "font-weight: 600; color: var(--color-gold); font-size: 11px;";
    title.textContent = titleText;
    
    titleRow.appendChild(title);
    group.appendChild(titleRow);
    
    return [group, titleRow];
  }

  private createToggleButton(textOn: string, textOff: string, initialState: boolean, onClick: (state: boolean) => void): HTMLButtonElement {
    const btn = document.createElement("button");
    let state = initialState;
    const updateBtn = () => {
      btn.textContent = state ? textOn : textOff;
      btn.style.color = state ? "var(--color-gold)" : "var(--color-text-muted)";
    };
    btn.style.cssText = `
      padding: 2px 8px;
      font-size: 10px;
      border-radius: 4px;
      border: 1px solid var(--color-border);
      background: var(--color-surface);
      cursor: pointer;
    `;
    updateBtn();
    btn.onclick = () => {
      state = !state;
      updateBtn();
      onClick(state);
    };
    return btn;
  }

  private buildAtmoGroup() {
    const [group, titleRow] = this.createGroup("Atmosfera Visual");
    
    this.atmoToggleBtn = this.createToggleButton("Activada", "Desactivada", true, (state) => {
      this.options.onAtmosphereToggled?.(state);
    });
    titleRow.appendChild(this.atmoToggleBtn);

    const pureRow = document.createElement("div");
    pureRow.style.cssText = "display: flex; justify-content: space-between; align-items: center; font-size: 10px;";
    pureRow.innerHTML = "<span>Colors Purs (debug)</span>";
    
    this.pureColorsToggleBtn = this.createToggleButton("On", "Off", false, (state) => {
      this.options.onPureColorsToggled?.(state);
    });
    pureRow.appendChild(this.pureColorsToggleBtn);
    
    group.appendChild(pureRow);
    this.element.appendChild(group);
  }

  private buildLightPollutionGroup() {
    const [group, titleRow] = this.createGroup("Contaminació Lumínica");
    
    this.lpToggleBtn = this.createToggleButton("Activada", "Desactivada", true, (state) => {
      this.options.onLightPollutionToggled?.(state);
    });
    titleRow.appendChild(this.lpToggleBtn);

    // Mode Selector
    const modeRow = document.createElement("div");
    modeRow.style.cssText = "display: flex; justify-content: space-between; align-items: center; font-size: 10px;";
    modeRow.innerHTML = "<span>Mode:</span>";
    
    this.lpModeSelect = document.createElement("select");
    this.lpModeSelect.style.cssText = "background: var(--color-surface); color: var(--color-text-bright); border: 1px solid var(--color-border); border-radius: 4px; padding: 2px 4px; font-size: 10px;";
    
    const modes = [
      { value: "automatic", label: "Automàtic (estimat)" },
      { value: "bortle", label: "Classe Bortle" },
      { value: "magnitude", label: "Magnitud Límit" }
    ];
    modes.forEach(m => {
      const opt = document.createElement("option");
      opt.value = m.value;
      opt.textContent = m.label;
      this.lpModeSelect.appendChild(opt);
    });
    this.lpModeSelect.value = "bortle";
    this.lpModeSelect.onchange = () => {
      this.options.onLightPollutionModeChanged?.(this.lpModeSelect.value as any);
      this.updateConditionalVisibility();
    };
    modeRow.appendChild(this.lpModeSelect);
    group.appendChild(modeRow);

    // Bortle Slider
    this.bortleContainer = document.createElement("div");
    this.bortleContainer.style.cssText = "display: flex; flex-direction: column; gap: 4px; font-size: 10px;";
    
    const bortleLabelRow = document.createElement("div");
    bortleLabelRow.style.cssText = "display: flex; justify-content: space-between;";
    bortleLabelRow.innerHTML = "<span>Bortle:</span>";
    this.lpBortleValue = document.createElement("span");
    this.lpBortleValue.style.color = "var(--color-text-bright)";
    this.lpBortleValue.textContent = "4.0";
    bortleLabelRow.appendChild(this.lpBortleValue);
    
    this.lpBortleInput = document.createElement("input");
    this.lpBortleInput.type = "range";
    this.lpBortleInput.min = "1";
    this.lpBortleInput.max = "9";
    this.lpBortleInput.step = "0.1";
    this.lpBortleInput.value = "4.0";
    this.lpBortleInput.oninput = () => {
      const val = Number(this.lpBortleInput.value);
      this.lpBortleValue.textContent = val.toFixed(1);
      this.options.onBortleClassChanged?.(val);
    };
    
    this.bortleContainer.appendChild(bortleLabelRow);
    this.bortleContainer.appendChild(this.lpBortleInput);
    group.appendChild(this.bortleContainer);

    // Magnitude Slider
    this.magContainer = document.createElement("div");
    this.magContainer.style.cssText = "display: flex; flex-direction: column; gap: 4px; font-size: 10px; display: none;";
    
    const magLabelRow = document.createElement("div");
    magLabelRow.style.cssText = "display: flex; justify-content: space-between;";
    magLabelRow.innerHTML = "<span>Mag límit:</span>";
    this.lpMagValue = document.createElement("span");
    this.lpMagValue.style.color = "var(--color-text-bright)";
    this.lpMagValue.textContent = "6.0";
    magLabelRow.appendChild(this.lpMagValue);
    
    this.lpMagInput = document.createElement("input");
    this.lpMagInput.type = "range";
    this.lpMagInput.min = "3.0";
    this.lpMagInput.max = "8.0";
    this.lpMagInput.step = "0.1";
    this.lpMagInput.value = "6.0";
    this.lpMagInput.oninput = () => {
      const val = Number(this.lpMagInput.value);
      this.lpMagValue.textContent = val.toFixed(1);
      this.options.onMagnitudeLimitChanged?.(val);
    };
    
    this.magContainer.appendChild(magLabelRow);
    this.magContainer.appendChild(this.lpMagInput);
    group.appendChild(this.magContainer);
    
    // Status info for Automatic mode or equivalents
    this.lpSourceLabel = document.createElement("div");
    this.lpSourceLabel.style.cssText = "font-size: 9px; color: var(--color-text-muted); margin-top: 4px;";
    group.appendChild(this.lpSourceLabel);

    this.element.appendChild(group);
  }

  private buildStarGroup() {
    const [group, titleRow] = this.createGroup("Camp Estel·lar Gaia");

    this.starsToggleBtn = this.createToggleButton("Visible", "Ocult", true, (state) => {
      this.starsVisible = state;
      this.options.onStarLayerToggled?.(state);
    });
    titleRow.appendChild(this.starsToggleBtn);

    const sourceRow = document.createElement("div");
    sourceRow.style.cssText = "font-size: 10px; display: flex; justify-content: space-between;";
    sourceRow.innerHTML = "<span>Font de dades:</span>";
    this.starSourceLabel = document.createElement("span");
    this.starSourceLabel.style.cssText = "font-weight: 600; color: var(--color-text-bright);";
    this.starSourceLabel.textContent = "Carregant...";
    sourceRow.appendChild(this.starSourceLabel);
    group.appendChild(sourceRow);

    const countRow = document.createElement("div");
    countRow.style.cssText = "font-size: 10px; display: flex; justify-content: space-between;";
    countRow.innerHTML = "<span>Estrelles a VRAM:</span>";
    this.starCountLabel = document.createElement("span");
    this.starCountLabel.style.cssText = "font-weight: 600; color: var(--color-text-bright);";
    this.starCountLabel.textContent = "0";
    countRow.appendChild(this.starCountLabel);
    group.appendChild(countRow);

    this.element.appendChild(group);
  }

  private updateConditionalVisibility() {
    const mode = this.lpModeSelect.value;
    this.bortleContainer.style.display = (mode === "bortle") ? "flex" : "none";
    this.magContainer.style.display = (mode === "magnitude") ? "flex" : "none";
  }

  public updateSkyEnvironment(snapshot: SkyEnvironmentSnapshot): void {
    // Si l'usuari no ha interactuat, actualitzem els controls
    if (this.lpModeSelect.value !== snapshot.lightPollutionMode) {
      this.lpModeSelect.value = snapshot.lightPollutionMode;
      this.updateConditionalVisibility();
    }
    
    let info = "";
    if (snapshot.lightPollutionMode === "automatic") {
      info = `Font Automàtica: ${snapshot.lightPollutionSource}. Bortle actiu: ${snapshot.bortleClass?.toFixed(1) || 'N/A'}`;
    } else if (snapshot.lightPollutionMode === "magnitude") {
      info = `Bortle equivalent (aproximat): ${snapshot.bortleClass?.toFixed(1)}`;
    } else {
      info = `Magnitud zenital efectiva: ${snapshot.visibility.zenithMagnitudeLimit.toFixed(1)}`;
    }
    this.lpSourceLabel.textContent = info;
  }

  public updateSolarSystem(snapshot: SolarSystemSnapshot): void {
    const moon = snapshot.moon;
    const source = snapshot.source === "DE421" ? "DE421" : "fallback";
    const moonState = moon === null
      ? "Lluna unavailable"
      : `Lluna ${(moon.illuminationFraction * 100).toFixed(0)}% · ${
        moon.orientation?.quality === "precise"
          ? moon.orientation.frame
          : `orientació ${moon.orientation?.quality ?? "unavailable"}`
      }`;
    this.solarStatusLabel.textContent = [
      `Efemèride: ${source}`,
      `Sol ${snapshot.sun.altitudeDeg.toFixed(1)}°`,
      moonState,
      `${snapshot.planets.length} planetes`,
    ].join(" · ");
  }

  public updateMoonSurfaceResource(
    resource: MoonSurfaceResourceDescriptor,
    selectedLabel = resource.label,
  ): void {
    this.moonSurfaceStatusLabel.textContent = selectedLabel;
    this.moonSurfaceStatusLabel.style.color = resource.status === "ready"
      ? "#4ade80"
      : resource.status === "invalid" ? "#ff8a80" : "var(--color-text-muted)";
    this.moonSurfaceStatusLabel.title = resource.detail ?? resource.credits.join(" · ");
  }

  public updateStarCatalogStatus(status: {
    gaiaAvailability: string;
    effectiveSource: string;
    generalStarCount: number;
    fallbackStarCount: number;
    deepResidentCount: number;
  }): void {
    if (status.effectiveSource === "gaia") {
      this.starSourceLabel.textContent = "Gaia DR2/DR3";
      this.starSourceLabel.style.color = "#4ade80"; // verd
      this.starCountLabel.textContent = status.generalStarCount.toLocaleString();
    } else if (status.effectiveSource === "fallback") {
      this.starSourceLabel.textContent = "Catàleg Fallback (~9000)";
      this.starSourceLabel.style.color = "#facc15"; // groc
      this.starCountLabel.textContent = status.fallbackStarCount.toLocaleString();
    } else {
      this.starSourceLabel.textContent = status.gaiaAvailability;
      this.starCountLabel.textContent = "0";
    }
  }

  public mount(container: HTMLElement): void {
    container.appendChild(this.element);
  }

  public dispose(): void {
    this.element.remove();
  }
}
