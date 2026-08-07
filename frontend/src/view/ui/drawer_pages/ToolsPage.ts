export class ToolsPage {
  private element: HTMLDivElement;

  constructor() {
    this.element = document.createElement("div");
    this.element.style.cssText = `
      display: flex;
      flex-direction: column;
      gap: 12px;
      color: var(--color-text-dim);
      font-size: var(--font-size-base);
    `;

    const desc = document.createElement("p");
    desc.textContent = "Eines d'anàlisi, mesura de distàncies, àrees i simulació d'òptica.";
    this.element.appendChild(desc);

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
    title.textContent = "Mesura i Utilitats";
    group.appendChild(title);

    const info = document.createElement("div");
    info.style.cssText = "font-size: 10px; color: var(--color-text-muted);";
    info.textContent = "Regla de mesura angular i eines de camp de visió (FOV).";
    group.appendChild(info);

    this.element.appendChild(group);
  }

  public mount(container: HTMLElement): void {
    container.appendChild(this.element);
  }

  public dispose(): void {
    this.element.remove();
  }
}
