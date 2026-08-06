export class LocationHUD {
  private element: HTMLDivElement;

  constructor() {
    this.element = document.createElement("div");
    this.element.style.cssText = `
      position: absolute;
      bottom: 15px;
      left: 15px;
      background: rgba(13, 17, 28, 0.6);
      border: 1px solid rgba(59, 69, 89, 0.4);
      border-radius: 6px;
      padding: 8px 12px;
      color: #f3f5fa;
      font-family: 'Inter', sans-serif;
      font-size: 11px;
      backdrop-filter: blur(4px);
      display: flex;
      flex-direction: column;
      gap: 4px;
      pointer-events: none;
      z-index: 10;
    `;
    this.updateHUD(0, 0, 0, 0, "No disponible");
  }

  public updateHUD(
    lat: number,
    lon: number,
    elevation: number,
    effectiveHeight: number,
    source: string,
  ): void {
    const latStr = lat.toFixed(4);
    const lonStr = lon.toFixed(4);
    const effStr = effectiveHeight.toFixed(1);

    this.element.innerHTML = `
    <div style="font-weight: 600; color: #d8b26a; margin-bottom: 2px;">
      OBSERVADOR
    </div>
    <div>Lat: ${latStr}° | Lon: ${lonStr}°</div>
    <div>Alçada efectiva: ${effStr} m</div>
    <div style="color: #88bbff; font-size: 10px; margin-top: 2px;">
      Font elev: ${source}
    </div>
  `;
  }

  public mount(container: HTMLElement): void {
    container.appendChild(this.element);
  }

  public dispose(): void {
    this.element.remove();
  }
}
