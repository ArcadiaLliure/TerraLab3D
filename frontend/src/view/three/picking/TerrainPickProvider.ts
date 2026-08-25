import * as THREE from "three";
import type { DemTerrainLayerRenderer } from "../layers/DemTerrainLayerRenderer";
import type { LandCoverObservation } from "../terrain/LandCoverTextureManager";

export interface TerrainPickHit {
  readonly observation: LandCoverObservation;
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
    
    // console.debug(`MGP: [TerrainPickProvider] intersects: ${intersects.length}`);

    if (intersects.length > 0) {
      // Sort by distance
      intersects.sort((a, b) => a.distance - b.distance);
      const hit = intersects[0];
      if (hit) {
        // The terrain geometry does not have UVs. We must use the world position.
        // In the terrain shader, geoX = worldPos.x and geoY = -worldPos.z
        const geoX = hit.point.x;
        const geoY = -hit.point.z;
        const observation = this.config.terrainRenderer.landCoverManager.getObservationAtWorld(geoX, geoY);
        
        if (observation) {
          return {
            observation,
            worldPoint: hit.point.clone(),
          };
        } else {
          // No land cover loaded or mapped at this point
          // console.debug(`MGP: [TerrainPickProvider] No category found for world: ${geoX}, ${geoY}`);
        }
      }
    }
    
    return null;
  }
}
