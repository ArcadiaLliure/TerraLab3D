import * as THREE from "three";
import type { DemTerrainLayerRenderer } from "../layers/DemTerrainLayerRenderer";

export interface TerrainPickHit {
  readonly classId: number;
  readonly label: string;
  readonly worldPoint: THREE.Vector3;
}

export interface TerrainPickProviderConfig {
  camera: THREE.Camera;
  getViewportRect: () => DOMRect;
  terrainRenderer: DemTerrainLayerRenderer;
}

export class TerrainPickProvider {
  private readonly config: TerrainPickProviderConfig;
  private readonly raycaster = new THREE.Raycaster();
  private readonly pointer = new THREE.Vector2();

  constructor(config: TerrainPickProviderConfig) {
    this.config = config;
  }

  public hover(xCssPx: number, yCssPx: number): TerrainPickHit | null {
    const rect = this.config.getViewportRect();
    const xPos = xCssPx - rect.left;
    const yPos = yCssPx - rect.top;

    this.pointer.x = (xPos / rect.width) * 2 - 1;
    this.pointer.y = -(yPos / rect.height) * 2 + 1;
    this.raycaster.setFromCamera(this.pointer, this.config.camera);

    const intersects: THREE.Intersection[] = [];
    this.config.terrainRenderer.raycast(this.raycaster, intersects);

    if (intersects.length > 0) {
      // Sort by distance
      intersects.sort((a, b) => a.distance - b.distance);
      const hit = intersects[0];
      if (hit && hit.uv) {
        const category = this.config.terrainRenderer.landCoverManager.getCategoryAtUv(hit.uv.x, hit.uv.y);
        if (category) {
          return {
            classId: category.classId,
            label: category.label,
            worldPoint: hit.point.clone(),
          };
        }
      }
    }
    
    return null;
  }
}
