import type { MeasurementDocumentSnapshot, MeasurementKind } from "../../../contracts/measurement_contracts";

export interface ToolsPageCallbacks {
  readonly onOpenResourceManager: () => void;
  readonly onMeasurementTool: (kind: MeasurementKind | null) => void;
  readonly onUndo: () => void;
  readonly onRedo: () => void;
  readonly onDelete: () => void;
  readonly onClear: () => void;
}

const TOOL_LABELS: Readonly<Record<MeasurementKind, string>> = {
  ruler: "Regla", square: "Quadrat", rectangle: "Rectangle", circle: "Cercle",
};

export class ToolsPage {
  private readonly element: HTMLDivElement;
  private readonly toolButtons = new Map<MeasurementKind, HTMLButtonElement>();
  private readonly undoButton: HTMLButtonElement;
  private readonly redoButton: HTMLButtonElement;
  private readonly deleteButton: HTMLButtonElement;
  private readonly clearButton: HTMLButtonElement;
  private readonly status: HTMLDivElement;
  private readonly trackingCheckbox: HTMLInputElement;

  constructor(private readonly callbacks: ToolsPageCallbacks) {
    this.element = document.createElement("div");
    this.element.style.cssText = "display:flex;flex-direction:column;gap:12px;color:var(--color-text-dim);font-size:var(--font-size-base);";
    const desc = document.createElement("p");
    desc.textContent = "Eines d'anàlisi, mesura de distàncies, àrees i simulació d'òptica.";
    this.element.appendChild(desc);

    const group = document.createElement("div");
    group.style.cssText = "background:var(--color-surface-raised);border:1px solid var(--color-border);border-radius:var(--border-radius-md);padding:10px;display:flex;flex-direction:column;gap:8px;";
    const title = document.createElement("div");
    title.style.cssText = "font-weight:600;color:var(--color-gold);font-size:11px;";
    title.textContent = "Mesura angular";
    group.appendChild(title);
    const info = document.createElement("div");
    info.style.cssText = "font-size:10px;color:var(--color-text-muted);";
    info.textContent = "Crea, selecciona, mou i redimensiona formes sobre l'esfera celeste.";
    group.appendChild(info);

    const tools = document.createElement("div");
    tools.className = "measurement-tool-grid";
    for (const kind of Object.keys(TOOL_LABELS) as MeasurementKind[]) {
      const tool = this.makeButton(TOOL_LABELS[kind], () => callbacks.onMeasurementTool(kind));
      tool.dataset.measurementTool = kind;
      tool.setAttribute("aria-pressed", "false");
      tool.title = `${TOOL_LABELS[kind]} angular`;
      tools.appendChild(tool);
      this.toolButtons.set(kind, tool);
    }
    group.appendChild(tools);

    const trackingRow = document.createElement("div");
    trackingRow.style.cssText = "display:flex;align-items:center;gap:6px;font-size:11px;margin-top:4px;";
    this.trackingCheckbox = document.createElement("input");
    this.trackingCheckbox.type = "checkbox";
    this.trackingCheckbox.checked = true;
    this.trackingCheckbox.id = "measurement-tracking-checkbox";
    const trackingLabel = document.createElement("label");
    trackingLabel.htmlFor = "measurement-tracking-checkbox";
    trackingLabel.textContent = "Seguiment (ancorar al cel)";
    trackingRow.appendChild(this.trackingCheckbox);
    trackingRow.appendChild(trackingLabel);
    group.appendChild(trackingRow);

    const actions = document.createElement("div");
    actions.className = "measurement-action-row";
    this.undoButton = this.makeButton("Desfer (Ctrl+Z)", callbacks.onUndo);
    this.undoButton.dataset.measurementAction = "undo";
    this.redoButton = this.makeButton("Refer (Ctrl+Y)", callbacks.onRedo);
    this.redoButton.dataset.measurementAction = "redo";
    this.deleteButton = this.makeButton("Eliminar", callbacks.onDelete);
    this.deleteButton.dataset.measurementAction = "delete";
    this.clearButton = this.makeButton("Netejar", callbacks.onClear);
    this.clearButton.dataset.measurementAction = "clear";
    actions.append(this.undoButton, this.redoButton, this.deleteButton, this.clearButton);
    group.appendChild(actions);

    this.status = document.createElement("div");
    this.status.className = "measurement-status";
    this.status.setAttribute("role", "status");
    this.status.setAttribute("aria-live", "polite");
    this.status.textContent = "Cap mesura. Selecciona una eina i arrossega sobre el cel.";
    group.appendChild(this.status);

    const resourceButton = this.makeButton("Obrir Gestor de Recursos", callbacks.onOpenResourceManager);
    resourceButton.style.marginTop = "8px";
    group.appendChild(resourceButton);
    this.element.appendChild(group);
    this.undoButton.disabled = true;
    this.redoButton.disabled = true;
    this.deleteButton.disabled = true;
    this.clearButton.disabled = true;
  }

  mount(container: HTMLElement): void { container.appendChild(this.element); }

  presentActiveTool(kind: MeasurementKind | null): void {
    for (const [buttonKind, button] of this.toolButtons) {
      const active = buttonKind === kind;
      button.classList.toggle("active", active);
      button.setAttribute("aria-pressed", String(active));
    }
    if (kind) this.status.textContent = `${TOOL_LABELS[kind]} activa: arrossega sobre el cel; Esc cancel·la.`;
  }

  presentMeasurements(snapshot: MeasurementDocumentSnapshot): void {
    this.undoButton.disabled = !snapshot.canUndo;
    this.redoButton.disabled = !snapshot.canRedo;
    this.deleteButton.disabled = snapshot.selectedMeasurementId === null;
    this.clearButton.disabled = snapshot.measurements.length === 0;
    const selected = snapshot.selectedMeasurementId ? " · una mesura seleccionada" : "";
    this.status.textContent = snapshot.warning ?? `${snapshot.measurements.length} ${snapshot.measurements.length === 1 ? "mesura" : "mesures"}${selected}`;
  }

  presentMeasurementPending(): void { this.status.textContent = "Aplicant operació…"; }
  presentMeasurementError(message: string): void { this.status.textContent = `No s'ha aplicat: ${message}`; }
  dispose(): void { this.element.remove(); }

  private makeButton(label: string, action: () => void): HTMLButtonElement {
    const button = document.createElement("button");
    button.type = "button";
    button.textContent = label;
    button.onclick = action;
    return button;
  }

  isTrackingEnabled(): boolean {
    return this.trackingCheckbox.checked;
  }
}
