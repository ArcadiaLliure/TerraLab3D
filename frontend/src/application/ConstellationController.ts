import type { WebSocketBridge } from "../bridge/WebSocketBridge";
import type {
  ConstellationCatalogSnapshot,
  ConstellationCommandMessage,
  ConstellationDocumentSnapshot,
  ConstellationErrorMessage,
} from "../contracts/constellation_contracts";
import type { ToolsPage } from "../view/ui/drawer_pages/ToolsPage";
import type { CameraRigImpl } from "../view/three/CameraRigImpl";
import type { ConstellationLayerRendererImpl } from "../view/three/layers/ConstellationLayerRenderer";
import type { PointerGestureRouter } from "../view/three/picking/PointerGestureRouter";
import type { StarPickProvider } from "../view/three/picking/StarPickProvider";

interface Options {
  readonly canvas?: HTMLCanvasElement;
  readonly bridge: WebSocketBridge;
  readonly cameraRig?: CameraRigImpl;
  readonly gestureRouter: PointerGestureRouter;
  readonly starPicker: StarPickProvider;
  readonly renderer: ConstellationLayerRendererImpl;
  readonly toolsPage: ToolsPage;
}

/** Converteix gestos locals en intencions; mai envia coordenades RA/Dec. */
export class ConstellationController {
  private snapshot: ConstellationDocumentSnapshot | null = null;
  private pending = false;
  private readonly unregisterTap: () => void;

  constructor(private readonly options: Options) {
    this.unregisterTap = options.gestureRouter.onTap(this.onTap, "high");
  }

  presentCatalog(snapshot: ConstellationCatalogSnapshot): void {
    this.options.renderer.presentCatalog(snapshot);
  }

  present(snapshot: ConstellationDocumentSnapshot): void {
    if (this.snapshot && snapshot.documentRevision < this.snapshot.documentRevision) return;
    this.snapshot = snapshot;
    this.pending = false;
    this.options.renderer.presentDocument(snapshot);
    this.options.toolsPage.presentConstellations(snapshot);
  }

  presentError(error: ConstellationErrorMessage): void {
    this.pending = false;
    this.options.toolsPage.presentConstellationError(error.message);
  }

  create(): void {
    this.send({ action: "create_group", name: "Nova constel·lació" });
  }

  select(constellationId: string | null): void { this.send({ action: "select", constellationId }); }

  setEditing(editing: boolean): void { this.send({ action: "set_editing", editing }); }
  newStroke(): void { this.sendSelected({ action: "new_stroke" }); }
  finish(): void { this.send({ action: "finish_group" }); }
  undo(): void { this.send({ action: "undo" }); }
  redo(): void { this.send({ action: "redo" }); }
  clear(): void { this.send({ action: "clear" }); }

  deleteSelected(): void {
    this.sendSelected({ action: "delete_selection" });
  }

  renameSelected(name: string): void {
    this.sendSelected({ action: "rename_group", name });
  }

  setShowAll(visible: boolean): void {
    this.options.renderer.setShowAll(visible);
  }

  setSelectedOfficial(constellationId: string | null): void {
    this.options.renderer.setSelectedCatalog(constellationId);
  }

  dispose(): void {
    this.unregisterTap();
  }

  private readonly onTap = (clientX: number, clientY: number): boolean => {
    if (!this.snapshot?.editing) return false;
    if (this.pending) return true;
    const selected = this.snapshot.selectedConstellationId;
    if (!selected) {
      this.options.toolsPage.presentConstellationError("Crea o selecciona un grup abans d'afegir estrelles.");
      return true;
    }
    const hit = this.options.starPicker.pickNearest(clientX, clientY, 16);
    if (!hit) {
      this.options.toolsPage.presentConstellationError("No hi ha cap estrella visible a menys de 16 px.");
      return true;
    }
    this.send({
      action: "append_node",
      constellationId: selected,
      resourceId: hit.ref.resourceId,
      resourceVersion: hit.ref.resourceVersion,
      catalogIndex: hit.ref.catalogIndex,
    });
    return true;
  };

  private sendSelected(command: Omit<ConstellationCommandMessage, "type" | "requestId" | "documentRevision" | "constellationId">): void {
    const constellationId = this.snapshot?.selectedConstellationId;
    if (!constellationId) return;
    this.send({ ...command, constellationId });
  }

  private send(command: Omit<ConstellationCommandMessage, "type" | "requestId" | "documentRevision">): void {
    if (this.pending) return;
    this.pending = true;
    this.options.toolsPage.presentConstellationPending();
    this.options.bridge.sendConstellationCommand({
      requestId: globalThis.crypto?.randomUUID?.() ?? `constellation-${Date.now()}`,
      documentRevision: (this.snapshot?.documentRevision ?? 0) + 1,
      ...command,
    });
  }
}
