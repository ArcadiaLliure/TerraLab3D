import * as THREE from "three";

import {
  projectTerrainCoordinate,
  type TerrainWorldAnchor,
} from "../../../application/TerrainCoordinateProjector";
import {
  TerrainGotoMenu,
  type TerrainGotoDestination,
} from "../../ui/TerrainGotoMenu";

export interface TerrainGotoControllerOptions {
  readonly canvas: HTMLElement;
  readonly menuParent: HTMLElement;
  readonly camera: THREE.PerspectiveCamera;
  readonly getTerrainMeshes: () => readonly THREE.Mesh[];
  readonly getTerrainWorldAnchor: () => TerrainWorldAnchor | null;
  readonly getTerrainLegendName?: (classId: number) => string | null;
  readonly onGoto: (destination: TerrainGotoDestination) => void;
}

/**
 * Turns a context click on rendered DEM geometry into an aircraft destination.
 * It is deliberately independent from celestial picking and only accepts an
 * actual triangle of the resident DEM meshes.
 */
export class TerrainGotoController {
  private readonly raycaster = new THREE.Raycaster();
  private readonly pointer = new THREE.Vector2();
  private readonly menu: TerrainGotoMenu;
  private readonly tooltip: HTMLDivElement;
  private readonly onContextMenuBound = this.onContextMenu.bind(this);
  private readonly onPointerDownBound = this.onPointerDown.bind(this);
  private readonly onPointerMoveBound = this.onPointerMove.bind(this);

  constructor(private readonly options: TerrainGotoControllerOptions) {
    this.menu = new TerrainGotoMenu(options.menuParent, options.onGoto);
    
    this.tooltip = document.createElement("div");
    this.tooltip.style.cssText = `
      position: absolute;
      pointer-events: none;
      display: none;
      background: var(--color-surface);
      border: 1px solid var(--color-border);
      color: var(--color-text-bright);
      padding: 4px 8px;
      border-radius: 4px;
      font-size: 11px;
      z-index: 1000;
      white-space: nowrap;
      box-shadow: 0 2px 4px rgba(0,0,0,0.5);
    `;
    options.menuParent.appendChild(this.tooltip);

    options.canvas.addEventListener("contextmenu", this.onContextMenuBound);
    options.canvas.addEventListener("pointerdown", this.onPointerDownBound);
    options.canvas.addEventListener("pointermove", this.onPointerMoveBound);
  }

  dispose(): void {
    this.options.canvas.removeEventListener("contextmenu", this.onContextMenuBound);
    this.options.canvas.removeEventListener("pointerdown", this.onPointerDownBound);
    this.options.canvas.removeEventListener("pointermove", this.onPointerMoveBound);
    this.tooltip.remove();
    this.menu.dispose();
  }

  private onContextMenu(event: MouseEvent): void {
    const destination = this.pickDestination(event.clientX, event.clientY);
    if (!destination) {
      this.menu.hide();
      return;
    }
    event.preventDefault();
    this.menu.show(event.clientX, event.clientY, destination);
  }

  private onPointerDown(event: PointerEvent): void {
    console.log("[DEBUG EVENT] TerrainGotoController.onPointerDown: event.target=", event.target);
    if (event.button === 0) this.menu.hide();
  }

  private onPointerMove(event: PointerEvent): void {
    if (!this.options.getTerrainLegendName) return;

    const bounds = this.options.canvas.getBoundingClientRect();
    if (bounds.width <= 0 || bounds.height <= 0) return;

    this.pointer.set(
      (event.clientX - bounds.left) / bounds.width * 2 - 1,
      -((event.clientY - bounds.top) / bounds.height) * 2 + 1,
    );
    this.raycaster.setFromCamera(this.pointer, this.options.camera);
    const meshes = this.options.getTerrainMeshes().filter((mesh) => mesh.visible && mesh.parent !== null);
    const hit = this.raycaster.intersectObjects(meshes, false)[0];

    if (hit && hit.face) {
      const index = hit.face.a;
      const classAttr = hit.object.geometry.getAttribute("terrainClassId");
      if (classAttr) {
        const classId = classAttr.getX(index);
        const name = this.options.getTerrainLegendName(classId);
        if (name) {
          this.tooltip.style.display = "block";
          this.tooltip.style.left = `${event.clientX + 15}px`;
          this.tooltip.style.top = `${event.clientY + 15}px`;
          this.tooltip.textContent = name;
          return;
        }
      }
    }
    
    this.tooltip.style.display = "none";
  }

  private pickDestination(clientX: number, clientY: number): TerrainGotoDestination | null {
    const anchor = this.options.getTerrainWorldAnchor();
    if (!anchor) return null;
    const bounds = this.options.canvas.getBoundingClientRect();
    if (bounds.width <= 0 || bounds.height <= 0) return null;
    this.pointer.set(
      (clientX - bounds.left) / bounds.width * 2 - 1,
      -((clientY - bounds.top) / bounds.height) * 2 + 1,
    );
    this.raycaster.setFromCamera(this.pointer, this.options.camera);
    const meshes = this.options.getTerrainMeshes().filter((mesh) => mesh.visible && mesh.parent !== null);
    const hit = this.raycaster.intersectObjects(meshes, false)[0];
    if (!hit || !Number.isFinite(hit.point.x) || !Number.isFinite(hit.point.y) || !Number.isFinite(hit.point.z)) {
      return null;
    }
    const eastM = hit.point.x;
    const northM = -hit.point.z;
    const coordinate = projectTerrainCoordinate(anchor, eastM, northM);
    if (!coordinate) return null;
    return {
      eastM,
      northM,
      terrainUpM: hit.point.y,
      ...coordinate,
    };
  }
}
