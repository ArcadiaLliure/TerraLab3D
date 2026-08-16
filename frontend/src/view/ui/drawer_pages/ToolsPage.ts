export class ToolsPage {
  private element: HTMLDivElement;

  constructor(private onOpenResourceManager: () => void) {
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

    const btn = document.createElement("button");
    btn.textContent = "Obrir Gestor de Recursos";
    btn.style.cssText = `
        padding: 6px 12px;
        margin-top: 8px;
        background: var(--color-surface, #1a1a1a);
        color: var(--color-gold, #facc15);
        border: 1px solid var(--color-gold, #facc15);
        border-radius: 4px;
        cursor: pointer;
        font-size: 11px;
    `;
    btn.onclick = () => {
      console.log("MGP: Frontend (ToolsPage.ts:51: Obrir Gestor de Recursos -> Obrir modal del gestor de recursos)");
      this.onOpenResourceManager();
    };
    group.appendChild(btn);

    this.element.appendChild(group);
  }

  public mount(container: HTMLElement): void {
    container.appendChild(this.element);
  }

  public dispose(): void {
    this.element.remove();
  }
}
