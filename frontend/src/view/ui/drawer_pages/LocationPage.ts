import type { NavigationMode, NavigationCameraPose, MotionState, NavigationReadiness } from "../../../contracts/navigation";

export interface LocationPageCallbacks {
  onRelocate: (lat: number, lon: number, height: number) => void;
  onSetRealtime: (enabled: boolean) => void;
  onOffsetDay: (offsetDays: number) => void;
  onSetDate: (dateIso: string) => void;
  onToggleNavigationMode?: () => void;
  onResetToOrigin?: () => void;
  onOverlayToggle?: (key: string, visible: boolean) => void;
  onHudToggle?: (visible: boolean) => void;
}

// ─── SVG Icons ───────────────────────────────────────────────────────

const WALK_SVG = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
  <circle cx="12" cy="5" r="2"/>
  <path d="M10 22l2-7 3 3v4"/>
  <path d="M14 13l-3-3-3 5h4"/>
  <path d="M8 22l1-4"/>
</svg>`;

const FLIGHT_SVG = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
  <path d="M17.8 19.2L16 11l3.5-3.5C21 6 21.5 4 21 3c-1-.5-3 0-4.5 1.5L13 8 4.8 6.2c-.5-.1-.9.1-1.1.5l-.3.5c-.2.5-.1 1 .3 1.3L9 12l-2 3H4l-1 1 3 2 2 3 1-1v-3l3-2 3.5 5.3c.3.4.8.5 1.3.3l.5-.2c.4-.3.6-.7.5-1.2z"/>
</svg>`;

export class LocationPage {
  private element: HTMLDivElement;
  private inputLat: HTMLInputElement;
  private inputLon: HTMLInputElement;
  private inputHeight: HTMLInputElement;
  private btnRelocate: HTMLButtonElement;
  private statusLabel: HTMLDivElement;

  // Date & Time Controls
  private inputDate: HTMLInputElement;
  private btnPrevDay: HTMLButtonElement;
  private btnNextDay: HTMLButtonElement;
  private btnRealtime: HTMLButtonElement;

  // Navigation controls
  private btnNavMode: HTMLButtonElement;
  private btnReset: HTMLButtonElement;
  private navModeLabel: HTMLDivElement;
  private navPositionLabel: HTMLDivElement;
  private navSpeedLabel: HTMLDivElement;
  private navHeightLabel: HTMLDivElement;
  private navZoneLabel: HTMLDivElement;

  private isRealtimeActive = true;
  private currentNavMode: NavigationMode = "walk";
  private callbacks: LocationPageCallbacks;

  constructor(callbacks: LocationPageCallbacks) {
    this.callbacks = callbacks;
    this.element = document.createElement("div");
    this.element.style.cssText = `
      display: flex;
      flex-direction: column;
      gap: 12px;
    `;

    // ── 1. Ubicació de l'observador ─────────────────────────────────
    const locSection = document.createElement("div");
    locSection.style.cssText = "display: flex; flex-direction: column; gap: 8px;";

    const locTitle = document.createElement("div");
    locTitle.style.cssText = "font-weight: 600; color: var(--color-gold); font-size: 11px; margin-bottom: 2px;";
    locTitle.textContent = "Ubicació de l'observador";
    locSection.appendChild(locTitle);

    this.inputLat = this.createInputRow(locSection, "Latitud (°)", "-90 a 90");
    this.inputLon = this.createInputRow(locSection, "Longitud (°)", "-180 a 180");
    this.inputHeight = this.createInputRow(locSection, "Alçada addicional (m)", "0");

    this.btnRelocate = document.createElement("button");
    this.btnRelocate.textContent = "Reubicar";
    this.btnRelocate.style.cssText = `
      background: var(--button-bg);
      color: var(--button-text);
      border: 1px solid var(--button-border);
      border-radius: var(--border-radius-sm);
      padding: 6px 12px;
      cursor: pointer;
      font-weight: 600;
      margin-top: 4px;
      transition: all 0.2s ease;
    `;
    this.btnRelocate.onmouseover = () => this.btnRelocate.style.background = "var(--button-hover)";
    this.btnRelocate.onmouseout = () => this.btnRelocate.style.background = "var(--button-bg)";

    this.btnRelocate.onclick = () => {
      const lat = parseFloat(this.inputLat.value) || 0;
      const lon = parseFloat(this.inputLon.value) || 0;
      const height = parseFloat(this.inputHeight.value) || 0;
      this.btnRelocate.textContent = "Reubicant...";
      this.callbacks.onRelocate(lat, lon, height);
    };

    this.statusLabel = document.createElement("div");
    this.statusLabel.style.cssText = `
      font-size: 11px;
      color: var(--color-success);
      text-align: center;
      min-height: 14px;
      opacity: 0;
      transition: opacity 0.3s ease;
      font-weight: 500;
    `;

    locSection.appendChild(this.btnRelocate);
    locSection.appendChild(this.statusLabel);
    this.element.appendChild(locSection);

    // Separator
    this.element.appendChild(this.createSeparator());

    // ── 2. Data i Hora ───────────────────────────────────────────────
    const dateSection = document.createElement("div");
    dateSection.style.cssText = "display: flex; flex-direction: column; gap: 8px;";

    const dateTitle = document.createElement("div");
    dateTitle.style.cssText = "font-weight: 600; color: var(--color-gold); font-size: 11px;";
    dateTitle.textContent = "Data";
    dateSection.appendChild(dateTitle);

    const calRow = document.createElement("div");
    calRow.style.cssText = "display: flex; align-items: center; gap: 6px;";

    this.btnPrevDay = this.createSmallButton("<", "Dia anterior");
    this.btnPrevDay.onclick = () => this.callbacks.onOffsetDay(-1);

    this.inputDate = document.createElement("input");
    this.inputDate.type = "date";
    this.inputDate.style.cssText = `
      flex: 1;
      height: 26px;
      background: var(--color-chrome);
      border: 1px solid var(--color-border);
      color: var(--color-gold);
      border-radius: var(--border-radius-sm);
      padding: 2px 6px;
      font-family: inherit;
      font-size: 11px;
      font-weight: 600;
      text-align: center;
      cursor: pointer;
    `;

    const now = new Date();
    const initY = now.getUTCFullYear();
    const initM = String(now.getUTCMonth() + 1).padStart(2, "0");
    const initD = String(now.getUTCDate()).padStart(2, "0");
    this.inputDate.value = `${initY}-${initM}-${initD}`;

    this.inputDate.onchange = () => {
      if (this.inputDate.value) {
        const dateObj = new Date(`${this.inputDate.value}T12:00:00.000Z`);
        if (!isNaN(dateObj.getTime())) {
          this.callbacks.onSetDate(dateObj.toISOString());
        }
      }
    };

    this.btnNextDay = this.createSmallButton(">", "Dia següent");
    this.btnNextDay.onclick = () => this.callbacks.onOffsetDay(1);

    calRow.appendChild(this.btnPrevDay);
    calRow.appendChild(this.inputDate);
    calRow.appendChild(this.btnNextDay);
    dateSection.appendChild(calRow);

    this.btnRealtime = document.createElement("button");
    this.btnRealtime.textContent = "Temps real";
    this.btnRealtime.style.cssText = `
      width: 100%;
      height: 28px;
      background: var(--color-surface-raised);
      border: 1px solid var(--color-border);
      border-radius: var(--border-radius-sm);
      color: var(--color-text);
      cursor: pointer;
      font-weight: 600;
      font-size: 11px;
      transition: all 0.2s ease;
    `;
    this.btnRealtime.onclick = () => {
      this.callbacks.onSetRealtime(!this.isRealtimeActive);
    };

    dateSection.appendChild(this.btnRealtime);
    this.element.appendChild(dateSection);
    this.setRealtimeUI(true);

    // Separator
    this.element.appendChild(this.createSeparator());

    // ── 3. Navegació (Phase 3.5) ─────────────────────────────────────
    const navSection = document.createElement("div");
    navSection.style.cssText = "display: flex; flex-direction: column; gap: 8px;";

    const navTitle = document.createElement("div");
    navTitle.style.cssText = "font-weight: 600; color: var(--color-gold); font-size: 11px;";
    navTitle.textContent = "Navegació";
    navSection.appendChild(navTitle);

    // Mode toggle button row
    const modeRow = document.createElement("div");
    modeRow.style.cssText = "display: flex; align-items: center; gap: 8px;";

    this.btnNavMode = document.createElement("button");
    this.btnNavMode.id = "nav-mode-toggle";
    this.btnNavMode.style.cssText = `
      width: 36px;
      height: 36px;
      border-radius: var(--border-radius-md);
      background: var(--button-bg);
      border: 1px solid var(--button-border);
      color: var(--color-text);
      cursor: pointer;
      display: flex;
      align-items: center;
      justify-content: center;
      transition: all 0.2s ease;
      padding: 6px;
    `;
    this.btnNavMode.innerHTML = WALK_SVG;
    this.btnNavMode.setAttribute("aria-label", "Canviar a mode avió");
    this.btnNavMode.title = "Canviar a mode avió (F)";
    this.btnNavMode.onmouseover = () => this.btnNavMode.style.background = "var(--button-hover)";
    this.btnNavMode.onmouseout = () => {
      this.btnNavMode.style.background = this.currentNavMode === "walk"
        ? "var(--button-bg)"
        : "var(--button-checked-bg)";
    };
    this.btnNavMode.onclick = () => this.callbacks.onToggleNavigationMode?.();

    this.navModeLabel = document.createElement("div");
    this.navModeLabel.style.cssText = "font-size: 11px; color: var(--color-text); font-weight: 600;";
    this.navModeLabel.textContent = "Caminar";

    modeRow.appendChild(this.btnNavMode);
    modeRow.appendChild(this.navModeLabel);
    navSection.appendChild(modeRow);

    // Reset button
    this.btnReset = document.createElement("button");
    this.btnReset.textContent = "Tornar a l'origen";
    this.btnReset.style.cssText = `
      width: 100%;
      height: 26px;
      background: var(--color-surface-raised);
      border: 1px solid var(--color-border);
      border-radius: var(--border-radius-sm);
      color: var(--color-text);
      cursor: pointer;
      font-weight: 500;
      font-size: 10px;
      transition: all 0.2s ease;
    `;
    this.btnReset.onmouseover = () => this.btnReset.style.background = "var(--button-hover)";
    this.btnReset.onmouseout = () => this.btnReset.style.background = "var(--color-surface-raised)";
    this.btnReset.onclick = () => this.callbacks.onResetToOrigin?.();
    navSection.appendChild(this.btnReset);

    // Navigation indicators
    this.navPositionLabel = this.createInfoLabel(navSection, "Posició: E 0.0 | N 0.0");
    this.navHeightLabel = this.createInfoLabel(navSection, "Altura: 0.0 m");
    this.navSpeedLabel = this.createInfoLabel(navSection, "Velocitat: 0.0 m/s");
    this.navZoneLabel = this.createInfoLabel(navSection, "Zona: --");

    this.element.appendChild(navSection);

    // Separator
    this.element.appendChild(this.createSeparator());

    // ── 4. Visualització (Phase 4) ──────────────────────────────────
    const vizSection = document.createElement("div");
    vizSection.style.cssText = "display: flex; flex-direction: column; gap: 6px;";

    const vizTitle = document.createElement("div");
    vizTitle.style.cssText = "font-weight: 600; color: var(--color-gold); font-size: 11px;";
    vizTitle.textContent = "Visualització";
    vizSection.appendChild(vizTitle);

    const overlayToggles: Array<{ key: string; label: string; checked: boolean }> = [
      { key: "grid", label: "Grid azimut-altitud", checked: true },
      { key: "compass", label: "Brúixola (N/E/S/O)", checked: true },
      { key: "labels", label: "Etiquetes angulars", checked: true },
      { key: "equator", label: "Equador celeste", checked: true },
      { key: "bounds", label: "Límits de navegació (vermell)", checked: false },
      { key: "hud", label: "HUD", checked: true },
    ];

    for (const toggle of overlayToggles) {
      const row = document.createElement("label");
      row.style.cssText = "display: flex; align-items: center; gap: 6px; cursor: pointer; font-size: 11px; color: var(--color-text-dim);";

      const checkbox = document.createElement("input");
      checkbox.type = "checkbox";
      checkbox.checked = toggle.checked;
      checkbox.id = `overlay-toggle-${toggle.key}`;
      checkbox.style.cssText = "accent-color: var(--color-gold); cursor: pointer;";
      checkbox.onchange = () => {
        if (toggle.key === "hud") {
          this.callbacks.onHudToggle?.(checkbox.checked);
        } else {
          this.callbacks.onOverlayToggle?.(toggle.key, checkbox.checked);
        }
      };

      const label = document.createElement("span");
      label.textContent = toggle.label;

      row.appendChild(checkbox);
      row.appendChild(label);
      vizSection.appendChild(row);
    }

    this.element.appendChild(vizSection);
  }

  // ─── Public API ────────────────────────────────────────────────────

  public updateNavigationState(
    pose: NavigationCameraPose,
    motion: MotionState,
    readiness: NavigationReadiness,
  ): void {
    // Update mode display
    if (pose.navigationMode !== this.currentNavMode) {
      this.currentNavMode = pose.navigationMode;
      this.updateNavModeUI();
    }

    // Update indicators
    this.navPositionLabel.textContent = `Posició: E ${pose.positionEastM.toFixed(1)} | N ${pose.positionNorthM.toFixed(1)}`;
    this.navHeightLabel.textContent = `Altura: ${pose.positionUpM.toFixed(1)} m`;
    this.navSpeedLabel.textContent = `Velocitat: ${motion.speedMps.toFixed(1)} m/s${motion.sprinting ? " (sprint)" : ""}`;
    this.navZoneLabel.textContent = `Zona: ${readiness}`;
  }

  /** Called externally when mode changes (e.g. from F shortcut). */
  public syncNavigationMode(mode: NavigationMode): void {
    if (mode !== this.currentNavMode) {
      this.currentNavMode = mode;
      this.updateNavModeUI();
    }
  }

  public updateInputs(lat: number, lon: number): void {
    this.inputLat.value = lat.toString();
    this.inputLon.value = lon.toString();
  }

  public updateTimeState(currentTimeIso: string, isRealtime: boolean): void {
    this.isRealtimeActive = isRealtime;
    this.setRealtimeUI(isRealtime);

    const d = new Date(currentTimeIso);
    if (!isNaN(d.getTime())) {
      const year = d.getUTCFullYear();
      const month = String(d.getUTCMonth() + 1).padStart(2, "0");
      const day = String(d.getUTCDate()).padStart(2, "0");
      this.inputDate.value = `${year}-${month}-${day}`;
    }
  }

  public notifySuccess(): void {
    this.btnRelocate.textContent = "Reubicar";
    this.statusLabel.textContent = "✓ Ubicació actualitzada";
    this.statusLabel.style.opacity = "1";
    setTimeout(() => {
      this.statusLabel.style.opacity = "0";
    }, 2500);
  }

  public notifyError(): void {
    this.btnRelocate.textContent = "Reubicar";
  }

  public mount(container: HTMLElement): void {
    container.appendChild(this.element);
  }

  public dispose(): void {
    this.element.remove();
  }

  // ─── Private ───────────────────────────────────────────────────────

  private updateNavModeUI(): void {
    if (this.currentNavMode === "walk") {
      this.btnNavMode.innerHTML = WALK_SVG;
      this.btnNavMode.setAttribute("aria-label", "Canviar a mode avió");
      this.btnNavMode.title = "Canviar a mode avió (F)";
      this.btnNavMode.style.background = "var(--button-bg)";
      this.btnNavMode.style.color = "var(--color-text)";
      this.btnNavMode.style.borderColor = "var(--button-border)";
      this.navModeLabel.textContent = "Caminar";
    } else {
      this.btnNavMode.innerHTML = FLIGHT_SVG;
      this.btnNavMode.setAttribute("aria-label", "Canviar a mode caminar");
      this.btnNavMode.title = "Canviar a mode caminar (F)";
      this.btnNavMode.style.background = "var(--button-checked-bg)";
      this.btnNavMode.style.color = "var(--button-checked-text)";
      this.btnNavMode.style.borderColor = "var(--button-checked-border)";
      this.navModeLabel.textContent = "Avió";
    }
  }

  private setRealtimeUI(active: boolean): void {
    if (active) {
      this.btnRealtime.style.background = "var(--button-checked-bg)";
      this.btnRealtime.style.color = "var(--button-checked-text)";
      this.btnRealtime.style.borderColor = "var(--button-checked-border)";
    } else {
      this.btnRealtime.style.background = "var(--color-surface-raised)";
      this.btnRealtime.style.color = "var(--color-text)";
      this.btnRealtime.style.borderColor = "var(--color-border)";
    }
  }

  private createInputRow(parent: HTMLElement, labelText: string, placeholder: string): HTMLInputElement {
    const row = document.createElement("div");
    row.style.cssText = "display: flex; justify-content: space-between; align-items: center;";

    const label = document.createElement("label");
    label.textContent = labelText;
    label.style.color = "var(--color-text-dim)";
    label.style.fontSize = "11px";

    const input = document.createElement("input");
    input.type = "number";
    input.step = "any";
    input.placeholder = placeholder;
    input.style.cssText = `
      width: 100px;
      background: var(--color-chrome);
      border: 1px solid var(--color-border);
      color: var(--color-text);
      border-radius: var(--border-radius-sm);
      padding: 4px 6px;
      font-family: inherit;
      font-size: 11px;
    `;
    input.onfocus = () => input.style.borderColor = "var(--color-gold)";
    input.onblur = () => input.style.borderColor = "var(--color-border)";

    row.appendChild(label);
    row.appendChild(input);
    parent.appendChild(row);
    return input;
  }

  private createSmallButton(text: string, title: string): HTMLButtonElement {
    const btn = document.createElement("button");
    btn.textContent = text;
    btn.title = title;
    btn.style.cssText = `
      width: 26px; height: 26px;
      background: var(--color-surface-raised);
      border: 1px solid var(--color-border);
      border-radius: var(--border-radius-sm);
      color: var(--color-text);
      cursor: pointer;
      font-weight: 600;
    `;
    return btn;
  }

  private createInfoLabel(parent: HTMLElement, text: string): HTMLDivElement {
    const div = document.createElement("div");
    div.style.cssText = "font-size: 10px; color: var(--color-text-muted); font-family: var(--font-family-mono);";
    div.textContent = text;
    parent.appendChild(div);
    return div;
  }

  private createSeparator(): HTMLDivElement {
    const hr = document.createElement("div");
    hr.style.cssText = "height: 1px; background: var(--color-border); margin: 4px 0;";
    return hr;
  }
}
