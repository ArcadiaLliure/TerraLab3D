export interface LocationPageCallbacks {
  onRelocate: (lat: number, lon: number, height: number) => void;
  onSetRealtime: (enabled: boolean) => void;
  onOffsetDay: (offsetDays: number) => void;
  onSetDate: (dateIso: string) => void;
}

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
  
  private isRealtimeActive = true;
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

    // Separator line
    const hr = document.createElement("div");
    hr.style.cssText = "height: 1px; background: var(--color-border); margin: 4px 0;";
    this.element.appendChild(hr);

    // ── 2. Data i Hora / Calendari ────────────────────────────────────
    const dateSection = document.createElement("div");
    dateSection.style.cssText = "display: flex; flex-direction: column; gap: 8px;";

    const dateTitle = document.createElement("div");
    dateTitle.style.cssText = "font-weight: 600; color: var(--color-gold); font-size: 11px;";
    dateTitle.textContent = "Data";
    dateSection.appendChild(dateTitle);

    // Day navigation bar: [<] [ Date Picker ] [>]
    const calRow = document.createElement("div");
    calRow.style.cssText = "display: flex; align-items: center; gap: 6px;";

    this.btnPrevDay = document.createElement("button");
    this.btnPrevDay.textContent = "<";
    this.btnPrevDay.title = "Dia anterior";
    this.btnPrevDay.style.cssText = `
      width: 26px; height: 26px;
      background: var(--color-surface-raised);
      border: 1px solid var(--color-border);
      border-radius: var(--border-radius-sm);
      color: var(--color-text);
      cursor: pointer;
      font-weight: 600;
    `;
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
    const initM = String(now.getUTCMonth() + 1).padStart(2, '0');
    const initD = String(now.getUTCDate()).padStart(2, '0');
    this.inputDate.value = `${initY}-${initM}-${initD}`;

    this.inputDate.onchange = () => {
      if (this.inputDate.value) {
        const dateObj = new Date(`${this.inputDate.value}T12:00:00.000Z`);
        if (!isNaN(dateObj.getTime())) {
          this.callbacks.onSetDate(dateObj.toISOString());
        }
      }
    };

    this.btnNextDay = document.createElement("button");
    this.btnNextDay.textContent = ">";
    this.btnNextDay.title = "Dia següent";
    this.btnNextDay.style.cssText = `
      width: 26px; height: 26px;
      background: var(--color-surface-raised);
      border: 1px solid var(--color-border);
      border-radius: var(--border-radius-sm);
      color: var(--color-text);
      cursor: pointer;
      font-weight: 600;
    `;
    this.btnNextDay.onclick = () => this.callbacks.onOffsetDay(1);

    calRow.appendChild(this.btnPrevDay);
    calRow.appendChild(this.inputDate);
    calRow.appendChild(this.btnNextDay);
    dateSection.appendChild(calRow);

    // Botó "Temps real"
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
      const month = String(d.getUTCMonth() + 1).padStart(2, '0');
      const day = String(d.getUTCDate()).padStart(2, '0');
      this.inputDate.value = `${year}-${month}-${day}`;
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
}
