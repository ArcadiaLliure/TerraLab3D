import type { MeasurementDocumentSnapshot, MeasurementKind } from "../../../contracts/measurement_contracts";
import type { ConstellationDocumentSnapshot } from "../../../contracts/constellation_contracts";

export interface ToolsPageCallbacks {
  readonly onOpenResourceManager: () => void;
  readonly onMeasurementTool: (kind: MeasurementKind | null) => void;
  readonly onUndo: () => void;
  readonly onRedo: () => void;
  readonly onDelete: () => void;
  readonly onClear: () => void;
  readonly onTrackingChanged: (enabled: boolean) => void;
  readonly onConstellationCreate: () => void;
  readonly onConstellationSelect: (constellationId: string | null) => void;
  readonly onConstellationRename: (name: string) => void;
  readonly onConstellationEditingChanged: (enabled: boolean) => void;
  readonly onConstellationShowAll: (visible: boolean) => void;
  readonly onConstellationNewStroke: () => void;
  readonly onConstellationFinish: () => void;
  readonly onConstellationUndo: () => void;
  readonly onConstellationRedo: () => void;
  readonly onConstellationDelete: () => void;
  readonly onConstellationClear: () => void;
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
  private snapshotTrackingEnabled: boolean | null = null;
  private readonly constellationEditing: HTMLInputElement;
  private readonly constellationShowAll: HTMLInputElement;
  private readonly constellationStatus: HTMLDivElement;
  private readonly constellationUndo: HTMLButtonElement;
  private readonly constellationRedo: HTMLButtonElement;
  private readonly constellationDelete: HTMLButtonElement;
  private readonly constellationSelect: HTMLSelectElement;
  private readonly constellationName: HTMLInputElement;

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
    trackingLabel.textContent = "Seguiment";
    this.trackingCheckbox.onchange = () => callbacks.onTrackingChanged(this.trackingCheckbox.checked);
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

    const constellationGroup = document.createElement("div");
    constellationGroup.style.cssText = group.style.cssText;
    const constellationTitle = document.createElement("div");
    constellationTitle.style.cssText = title.style.cssText;
    constellationTitle.textContent = "Constel·lacions";
    constellationGroup.appendChild(constellationTitle);
    const constellationInfo = document.createElement("div");
    constellationInfo.style.cssText = info.style.cssText;
    constellationInfo.textContent = "Consulta el traçat de referència o crea grups connectant estrelles visibles.";
    constellationGroup.appendChild(constellationInfo);
    const constellationIdentity = document.createElement("div");
    constellationIdentity.style.cssText = "display:grid;grid-template-columns:1fr auto;gap:6px;";
    this.constellationSelect = document.createElement("select");
    this.constellationSelect.onchange = () => callbacks.onConstellationSelect(this.constellationSelect.value || null);
    this.constellationName = document.createElement("input");
    this.constellationName.type = "text";
    this.constellationName.maxLength = 80;
    this.constellationName.placeholder = "Nom del grup";
    const rename = this.makeButton("Reanomena", () => callbacks.onConstellationRename(this.constellationName.value));
    constellationIdentity.append(this.constellationSelect, document.createElement("span"), this.constellationName, rename);
    constellationGroup.appendChild(constellationIdentity);
    const constellationActions = document.createElement("div");
    constellationActions.className = "measurement-action-row";
    constellationActions.append(
      this.makeButton("Nou grup", callbacks.onConstellationCreate),
      this.makeButton("Nou traç", callbacks.onConstellationNewStroke),
      this.makeButton("Finalitza", callbacks.onConstellationFinish),
    );
    constellationGroup.appendChild(constellationActions);
    const toggles = document.createElement("div");
    toggles.style.cssText = trackingRow.style.cssText;
    this.constellationEditing = document.createElement("input");
    this.constellationEditing.type = "checkbox";
    this.constellationEditing.id = "constellation-editing-checkbox";
    this.constellationEditing.onchange = () => callbacks.onConstellationEditingChanged(this.constellationEditing.checked);
    const editingLabel = document.createElement("label");
    editingLabel.htmlFor = this.constellationEditing.id;
    editingLabel.textContent = "Edita";
    this.constellationShowAll = document.createElement("input");
    this.constellationShowAll.type = "checkbox";
    this.constellationShowAll.id = "constellation-show-all-checkbox";
    this.constellationShowAll.onchange = () => callbacks.onConstellationShowAll(this.constellationShowAll.checked);
    const showAllLabel = document.createElement("label");
    showAllLabel.htmlFor = this.constellationShowAll.id;
    showAllLabel.textContent = "Mostra totes";
    toggles.append(this.constellationEditing, editingLabel, this.constellationShowAll, showAllLabel);
    constellationGroup.appendChild(toggles);
    const history = document.createElement("div");
    history.className = "measurement-action-row";
    this.constellationUndo = this.makeButton("Desfer", callbacks.onConstellationUndo);
    this.constellationRedo = this.makeButton("Refer", callbacks.onConstellationRedo);
    this.constellationDelete = this.makeButton("Elimina", callbacks.onConstellationDelete);
    history.append(this.constellationUndo, this.constellationRedo, this.constellationDelete, this.makeButton("Neteja", callbacks.onConstellationClear));
    constellationGroup.appendChild(history);
    this.constellationStatus = document.createElement("div");
    this.constellationStatus.className = "measurement-status";
    this.constellationStatus.setAttribute("role", "status");
    this.constellationStatus.textContent = "Carregant constel·lacions…";
    constellationGroup.appendChild(this.constellationStatus);
    this.element.appendChild(constellationGroup);
    this.constellationUndo.disabled = true;
    this.constellationRedo.disabled = true;
    this.constellationDelete.disabled = true;
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
    this.snapshotTrackingEnabled = snapshot.trackingEnabled;
    this.trackingCheckbox.checked = snapshot.trackingEnabled;
    this.trackingCheckbox.disabled = false;
    this.undoButton.disabled = !snapshot.canUndo;
    this.redoButton.disabled = !snapshot.canRedo;
    this.deleteButton.disabled = snapshot.selectedMeasurementId === null;
    this.clearButton.disabled = snapshot.measurements.length === 0;
    const selected = snapshot.selectedMeasurementId ? " · una mesura seleccionada" : "";
    this.status.textContent = snapshot.warning ?? `${snapshot.measurements.length} ${snapshot.measurements.length === 1 ? "mesura" : "mesures"}${selected}`;
  }

  presentMeasurementPending(): void {
    this.trackingCheckbox.disabled = true;
    this.status.textContent = "Aplicant operació…";
  }
  presentMeasurementError(message: string): void {
    if (this.snapshotTrackingEnabled !== null) this.trackingCheckbox.checked = this.snapshotTrackingEnabled;
    this.trackingCheckbox.disabled = false;
    this.status.textContent = `No s'ha aplicat: ${message}`;
  }

  presentConstellations(snapshot: ConstellationDocumentSnapshot): void {
    this.constellationEditing.checked = snapshot.editing;
    this.constellationEditing.disabled = false;
    this.constellationUndo.disabled = !snapshot.canUndo;
    this.constellationRedo.disabled = !snapshot.canRedo;
    this.constellationDelete.disabled = snapshot.selectedConstellationId === null;
    const currentOptions = [...this.constellationSelect.options].map(option => option.value).join("|");
    const nextOptions = snapshot.constellations.map(item => item.constellationId).join("|");
    if (currentOptions !== nextOptions) {
      this.constellationSelect.replaceChildren();
      const empty = document.createElement("option");
      empty.value = "";
      empty.textContent = "Selecciona un grup";
      this.constellationSelect.appendChild(empty);
      for (const item of snapshot.constellations) {
        const option = document.createElement("option");
        option.value = item.constellationId;
        option.textContent = item.name;
        this.constellationSelect.appendChild(option);
      }
    }
    this.constellationSelect.value = snapshot.selectedConstellationId ?? "";
    const selectedGroup = snapshot.constellations.find(item => item.constellationId === snapshot.selectedConstellationId);
    this.constellationName.value = selectedGroup?.name ?? "";
    const selected = snapshot.selectedConstellationId ? " · grup seleccionat" : "";
    this.constellationStatus.textContent = snapshot.warning ?? `${snapshot.constellations.length} grups d'usuari${selected}`;
  }

  presentConstellationPending(): void {
    this.constellationEditing.disabled = true;
    this.constellationStatus.textContent = "Aplicant operació…";
  }

  presentConstellationError(message: string): void {
    this.constellationEditing.disabled = false;
    this.constellationStatus.textContent = `No s'ha aplicat: ${message}`;
  }
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
