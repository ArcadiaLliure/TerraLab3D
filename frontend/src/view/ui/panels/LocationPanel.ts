export class LocationPanel {
  private element: HTMLDivElement;
  private inputLat: HTMLInputElement;
  private inputLon: HTMLInputElement;
  private inputHeight: HTMLInputElement;
  private btnRelocate: HTMLButtonElement;
  private statusLabel: HTMLDivElement;
  private onRelocate: (lat: number, lon: number, height: number) => void;

  constructor(onRelocate: (lat: number, lon: number, height: number) => void) {
    this.onRelocate = onRelocate;
    this.element = document.createElement("div");
    this.element.style.cssText = `
      position: absolute;
      top: 10px;
      right: 10px;
      background: rgba(13, 17, 28, 0.8);
      border: 1px solid rgba(59, 69, 89, 0.5);
      border-radius: 8px;
      padding: 15px;
      color: #f3f5fa;
      font-family: 'Inter', sans-serif;
      backdrop-filter: blur(8px);
      display: flex;
      flex-direction: column;
      gap: 10px;
      width: 250px;
      box-shadow: 0 4px 6px rgba(0, 0, 0, 0.3);
      z-index: 10;
    `;

    const title = document.createElement("div");
    title.textContent = "Ubicació de l'observador";
    title.style.cssText = "font-weight: 600; font-size: 14px; margin-bottom: 5px; color: #d8b26a;";
    this.element.appendChild(title);

    this.inputLat = this.createInputGroup("Latitud (°)", "-90 a 90");
    this.inputLon = this.createInputGroup("Longitud (°)", "-180 a 180");
    this.inputHeight = this.createInputGroup("Alçada extra (m)", "0");

    this.btnRelocate = document.createElement("button");
    this.btnRelocate.textContent = "Reubicar";
    this.btnRelocate.style.cssText = `
      background: #252c3b;
      color: #f3f5fa;
      border: 1px solid #3b4559;
      border-radius: 4px;
      padding: 6px 12px;
      cursor: pointer;
      font-weight: 600;
      margin-top: 5px;
      transition: all 0.2s ease;
    `;
    this.btnRelocate.onmouseover = () => this.btnRelocate.style.background = "#3b4559";
    this.btnRelocate.onmouseout = () => this.btnRelocate.style.background = "#252c3b";
    
    this.statusLabel = document.createElement("div");
    this.statusLabel.style.cssText = `
      font-size: 11px;
      color: #55ff99;
      text-align: center;
      min-height: 15px;
      opacity: 0;
      transition: opacity 0.3s ease;
      font-weight: 500;
    `;

    this.btnRelocate.onclick = () => {
      const lat = parseFloat(this.inputLat.value) || 0;
      const lon = parseFloat(this.inputLon.value) || 0;
      const height = parseFloat(this.inputHeight.value) || 0;
      
      this.btnRelocate.textContent = "Reubicant...";
      this.btnRelocate.style.background = "#3b4559";
      this.onRelocate(lat, lon, height);
    };

    this.element.appendChild(this.btnRelocate);
    this.element.appendChild(this.statusLabel);
  }

  private createInputGroup(labelText: string, placeholder: string): HTMLInputElement {
    const row = document.createElement("div");
    row.style.cssText = "display: flex; justify-content: space-between; align-items: center; font-size: 12px;";
    
    const label = document.createElement("label");
    label.textContent = labelText;
    
    const input = document.createElement("input");
    input.type = "number";
    input.step = "any";
    input.placeholder = placeholder;
    input.style.cssText = `
      width: 80px;
      background: #050811;
      border: 1px solid #3b4559;
      color: #f3f5fa;
      border-radius: 4px;
      padding: 4px;
      font-family: inherit;
    `;
    
    row.appendChild(label);
    row.appendChild(input);
    this.element.appendChild(row);
    return input;
  }

  public updateInputs(lat: number, lon: number): void {
    this.inputLat.value = lat.toString();
    this.inputLon.value = lon.toString();
  }

  public notifySuccess(): void {
    this.btnRelocate.textContent = "Reubicar";
    this.btnRelocate.style.background = "#252c3b";
    this.statusLabel.textContent = "✓ Ubicació actualitzada";
    this.statusLabel.style.color = "#55ff99";
    this.statusLabel.style.opacity = "1";
    setTimeout(() => {
      this.statusLabel.style.opacity = "0";
    }, 2500);
  }

  public notifyError(): void {
    this.btnRelocate.textContent = "Reubicar";
    this.btnRelocate.style.background = "#252c3b";
  }

  public mount(container: HTMLElement): void {
    container.appendChild(this.element);
  }

  public dispose(): void {
    this.element.remove();
  }
}
