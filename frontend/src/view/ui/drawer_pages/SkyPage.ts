export interface SkyPageOptions {
  onOverlayToggle?: (key: string, visible: boolean) => void;
}

export class SkyPage {
  private element: HTMLDivElement;
  private starSourceLabel: HTMLSpanElement;
  private starCountLabel: HTMLSpanElement;
  private starsToggleBtn: HTMLButtonElement;
  private starsVisible = true;
  private options: SkyPageOptions;

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
    desc.textContent = "Paràmetres de visualització de la volta celeste, estrelles, constel·lacions i atmosfera.";
    this.element.appendChild(desc);

    // ─── Grup: Volta Celeste ─────────────────────────────────────────
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
    title.style.cssText = "font-weight: 600; color: var(--color-gold); font-size: 11px;";
    title.textContent = "Volta Celeste";
    group.appendChild(title);

    const info = document.createElement("div");
    info.style.cssText = "font-size: 10px; color: var(--color-text-muted);";
    info.textContent = "Mode actiu: Graella equatorial i temps sideral local.";
    group.appendChild(info);

    this.element.appendChild(group);

    // ─── Grup: Camp Estel·lar Gaia / Fallback ────────────────────────
    const starGroup = document.createElement("div");
    starGroup.style.cssText = `
      background: var(--color-surface-raised);
      border: 1px solid var(--color-border);
      border-radius: var(--border-radius-md);
      padding: 10px;
      display: flex;
      flex-direction: column;
      gap: 8px;
    `;

    const starTitleRow = document.createElement("div");
    starTitleRow.style.cssText = "display: flex; justify-content: space-between; align-items: center;";

    const starTitle = document.createElement("div");
    starTitle.style.cssText = "font-weight: 600; color: var(--color-gold); font-size: 11px;";
    starTitle.textContent = "Camp Estel·lar Gaia";
    starTitleRow.appendChild(starTitle);

    this.starsToggleBtn = document.createElement("button");
    this.starsToggleBtn.textContent = "Visible";
    this.starsToggleBtn.style.cssText = `
      padding: 2px 8px;
      font-size: 10px;
      border-radius: 4px;
      border: 1px solid var(--color-border);
      background: var(--color-surface);
      color: var(--color-gold);
      cursor: pointer;
    `;
    this.starsToggleBtn.onclick = () => {
      this.starsVisible = !this.starsVisible;
      this.starsToggleBtn.textContent = this.starsVisible ? "Visible" : "Ocult";
      this.starsToggleBtn.style.color = this.starsVisible ? "var(--color-gold)" : "var(--color-text-muted)";
      this.options.onOverlayToggle?.("stars", this.starsVisible);
    };
    starTitleRow.appendChild(this.starsToggleBtn);
    starGroup.appendChild(starTitleRow);

    const sourceRow = document.createElement("div");
    sourceRow.style.cssText = "font-size: 10px; display: flex; justify-content: space-between;";
    sourceRow.innerHTML = "<span>Font de dades:</span>";
    this.starSourceLabel = document.createElement("span");
    this.starSourceLabel.style.cssText = "font-weight: 600; color: var(--color-text-bright);";
    this.starSourceLabel.textContent = "Carregant...";
    sourceRow.appendChild(this.starSourceLabel);
    starGroup.appendChild(sourceRow);

    const countRow = document.createElement("div");
    countRow.style.cssText = "font-size: 10px; display: flex; justify-content: space-between;";
    countRow.innerHTML = "<span>Estrelles a VRAM:</span>";
    this.starCountLabel = document.createElement("span");
    this.starCountLabel.style.cssText = "font-weight: 600; color: var(--color-text-bright);";
    this.starCountLabel.textContent = "0";
    countRow.appendChild(this.starCountLabel);
    starGroup.appendChild(countRow);

    this.element.appendChild(starGroup);
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
