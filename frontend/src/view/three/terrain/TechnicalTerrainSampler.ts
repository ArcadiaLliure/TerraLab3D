/**
 * TechnicalTerrainSampler — concrete implementation of TerrainSampler
 * based on Three.js raycaster over the technical terrain mesh.
 *
 * This file is the ONLY place that knows about raycasters and meshes.
 * Consumers (GroundFollower, NavigationController, HUD) import only
 * the TerrainSampler interface from contracts/.
 */

import * as THREE from "three";
import type { GroundSample, TerrainSampler } from "../../contracts/TerrainSampler";

const RAD2DEG = 180 / Math.PI;
const UP = new THREE.Vector3(0, 1, 0);

export class TechnicalTerrainSampler implements TerrainSampler {
  private readonly raycaster = new THREE.Raycaster();
  private readonly rayOrigin = new THREE.Vector3();
  private readonly rayDir = new THREE.Vector3(0, -1, 0);
  private terrainMesh: THREE.Mesh | null = null;
  private ready = false;

  /**
   * Set the terrain mesh to raycast against.
   * Called by NavigationWorld after the terrain geometry is built.
   */
  setTerrainMesh(mesh: THREE.Mesh): void {
    this.terrainMesh = mesh;
    this.ready = true;
  }

  isReady(): boolean {
    return this.ready && this.terrainMesh !== null;
  }

  sampleGround(
    eastM: number,
    northM: number,
    referenceUpM?: number,
  ): GroundSample | null {
    if (!this.terrainMesh) return null;

    // Cast a ray downward from high above the queried position.
    // ENU → Three.js: East=+X, Up=+Y, North=-Z
    const probeHeight = referenceUpM !== undefined ? referenceUpM + 100 : 500;
    this.rayOrigin.set(eastM, probeHeight, -northM);
    this.rayDir.set(0, -1, 0);
    this.raycaster.set(this.rayOrigin, this.rayDir);
    this.raycaster.far = probeHeight + 100;

    const hits = this.raycaster.intersectObject(this.terrainMesh, false);
    if (hits.length === 0) return null;

    const hit = hits[0];
    const face = hit.face;
    if (!face) return null;

    // Get world-space normal
    const normalMatrix = new THREE.Matrix3().getNormalMatrix(
      this.terrainMesh.matrixWorld,
    );
    const worldNormal = face.normal.clone().applyMatrix3(normalMatrix).normalize();

    // Validate normal
    if (!isFinite(worldNormal.x) || !isFinite(worldNormal.y) || !isFinite(worldNormal.z)) {
      return null;
    }
    if (worldNormal.lengthSq() < 0.5) return null;

    // Height: Three.js Y → ENU Up
    const heightM = hit.point.y;
    if (!isFinite(heightM)) return null;

    // Slope from normal
    const cosAngle = worldNormal.dot(UP);
    const slopeDeg = Math.acos(Math.min(1, Math.max(-1, cosAngle))) * RAD2DEG;

    return {
      heightM,
      normal: {
        east: worldNormal.x,
        up: worldNormal.y,
        // Three.js -Z = North → ENU north component
        north: -worldNormal.z,
      },
      slopeDeg,
      valid: true,
      surfaceId: "technical_terrain",
    };
  }
}
