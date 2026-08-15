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
  private readonly onContextMenuBound = this.onContextMenu.bind(this);
  private readonly onPointerDownBound = this.onPointerDown.bind(this);

  constructor(private readonly options: TerrainGotoControllerOptions) {
    this.menu = new TerrainGotoMenu(options.menuParent, options.onGoto);
    options.canvas.addEventListener("contextmenu", this.onContextMenuBound);
    options.canvas.addEventListener("pointerdown", this.onPointerDownBound);
  }

  dispose(): void {
    this.options.canvas.removeEventListener("contextmenu", this.onContextMenuBound);
    this.options.canvas.removeEventListener("pointerdown", this.onPointerDownBound);
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
    if (event.button === 0) this.menu.hide();
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
