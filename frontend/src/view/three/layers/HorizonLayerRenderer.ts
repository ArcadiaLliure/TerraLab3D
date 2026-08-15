import * as THREE from "three";

import type { HorizonOcclusionSnapshot } from "../HorizonOcclusionState";
import { HorizonOcclusionState } from "../HorizonOcclusionState";
import { CELESTIAL_SCENE_RADIUS } from "../celestialScenePolicy";
import { setThreeFromAzimuthAltitude } from "../celestialCoordinates";

export const HORIZON_MASK_RENDER_ORDER = -1_000;

export interface HorizonLayerMetrics {
  readonly geometryBuildCount: number;
  readonly geometryUploadBytes: number;
  readonly activeMeshCount: number;
}

/**
 * Persistent no-DEM fog at the geometric horizon.
 *
 * Missing DEM is an unknown landscape, never a black mountain wall. The fog
 * has its upper boundary fixed at 0° and is only a global fallback while the
 * DEM authority is unavailable. A partially covered real profile must not
 * turn temporary nodata gaps into a full-screen fog curtain. Real DEM
 * terrain remains the sole depth-writing world surface.
 */
export class HorizonLayerRenderer {
  readonly root = new THREE.Group();
  private mesh: THREE.Mesh<THREE.BufferGeometry, THREE.MeshBasicMaterial> | null = null;
  private readonly material = new THREE.MeshBasicMaterial({
    color: 0x8fa7c4,
    side: THREE.DoubleSide,
    depthTest: true,
    depthWrite: false,
    transparent: true,
    opacity: 0.55,
  });
  private readonly unsubscribe: () => void;
  private visible = true;
  private disposed = false;
  private geometryBuildCount = 0;
  private geometryUploadBytes = 0;
  private activeVersion = -1;
  private activeContentKey = "";
  private readonly directionScratch = new THREE.Vector3();

  constructor(parent: THREE.Object3D, private readonly state: HorizonOcclusionState) {
    this.root.name = "horizonOcclusionRoot";
    parent.add(this.root);
    this.unsubscribe = state.subscribe((snapshot) => this.swapGeometry(snapshot));
  }

  setVisible(visible: boolean): void {
    this.visible = visible;
    this.root.visible = visible;
  }

  metrics(): HorizonLayerMetrics {
    return {
      geometryBuildCount: this.geometryBuildCount,
      geometryUploadBytes: this.geometryUploadBytes,
      activeMeshCount: this.disposed || this.mesh === null ? 0 : 1,
    };
  }

  dispose(): void {
    if (this.disposed) return;
    this.disposed = true;
    this.unsubscribe();
    this.root.removeFromParent();
    this.mesh?.geometry.dispose();
    this.mesh = null;
    this.material.dispose();
  }

  private swapGeometry(snapshot: HorizonOcclusionSnapshot): void {
    if (this.disposed) return;
    const fogNeeded = !this.state.hasDemBackedProfile;
    if (
      this.mesh !== null
      && this.activeVersion === snapshot.metadata.version
      && this.activeContentKey === snapshot.metadata.contentKey
    ) {
      this.root.visible = this.visible
        && this.state.gpuUniformValues().enabled > 0
        && fogNeeded;
      return;
    }
    const count = snapshot.metadata.sampleCount;
    const positions = new Float32Array((count + 1) * 2 * 3);
    const indexValues: number[] = [];
    const radius = CELESTIAL_SCENE_RADIUS.horizonMask;

    for (let i = 0; i <= count; i++) {
      const sampleIndex = i % count;
      const azimuthDeg = snapshot.metadata.azimuthStartDeg
        + sampleIndex * snapshot.metadata.angularStepDeg;
      setThreeFromAzimuthAltitude(this.directionScratch, azimuthDeg, 0, radius)
        .toArray(positions, i * 6);
      setThreeFromAzimuthAltitude(this.directionScratch, azimuthDeg, -89.9, radius)
        .toArray(positions, i * 6 + 3);
      if (i === count) continue;
      const nextSample = (sampleIndex + 1) % count;
      if (this.state.hasDemBackedProfile) continue;
      const top = i * 2;
      const bottom = top + 1;
      indexValues.push(top, bottom, top + 2, top + 2, bottom, top + 3);
    }

    const geometry = new THREE.BufferGeometry();
    geometry.setAttribute("position", new THREE.BufferAttribute(positions, 3));
    const indices = new Uint32Array(indexValues);
    geometry.setIndex(new THREE.BufferAttribute(indices, 1));
    geometry.computeBoundingSphere();

    const replacement = new THREE.Mesh(geometry, this.material);
    replacement.name = "horizonNoDemFog";
    replacement.frustumCulled = false;
    replacement.renderOrder = HORIZON_MASK_RENDER_ORDER;
    const previous = this.mesh;
    this.mesh = replacement;
    this.root.add(replacement);
    previous?.removeFromParent();
    previous?.geometry.dispose();
    this.activeVersion = snapshot.metadata.version;
    this.activeContentKey = snapshot.metadata.contentKey;
    this.root.visible = this.visible
      && this.state.gpuUniformValues().enabled > 0
      && fogNeeded;
    this.geometryBuildCount++;
    this.geometryUploadBytes += positions.byteLength + indices.byteLength;
  }
}
