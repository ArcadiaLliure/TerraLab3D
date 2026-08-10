import * as THREE from "three";

import type { ApparentTrajectoryMetadata } from "../../contracts/astronomical_event_contracts";
import { threeFromEnu } from "./celestialCoordinates";

const TRAJECTORY_RADIUS = 870_000;

interface TrajectoryVisual {
  readonly line: THREE.Line<THREE.BufferGeometry, THREE.LineBasicMaterial>;
  version: string;
  observerGeneration: number;
}

export interface ApparentTrajectoryMetrics {
  readonly geometryBuildCount: number;
  readonly materialBuildCount: number;
  readonly resourceApplyCount: number;
  readonly staleResourceCount: number;
  readonly bridgeBytes: number;
}

/** Persistent renderer for observer-sky tracks; unrelated to SPK orbit lines. */
export class ApparentTrajectoryRenderer {
  readonly root = new THREE.Group();
  private readonly visuals = new Map<string, TrajectoryVisual>();
  private enabled = true;
  private disposed = false;
  private _geometryBuildCount = 0;
  private _materialBuildCount = 0;
  private _resourceApplyCount = 0;
  private _staleResourceCount = 0;
  private _bridgeBytes = 0;

  constructor(parent: THREE.Object3D) {
    this.root.name = "apparentTrajectories";
    parent.add(this.root);
  }

  registerBinaryResource(metadata: ApparentTrajectoryMetadata, payload: ArrayBuffer): boolean {
    if (this.disposed || metadata.role !== "apparent_trajectory") return false;
    const previous = this.visuals.get(metadata.bodyId);
    if (previous !== undefined && (
      metadata.observerGeneration < previous.observerGeneration
      || (metadata.observerGeneration === previous.observerGeneration && metadata.version === previous.version)
    )) {
      this._staleResourceCount++;
      return false;
    }
    const requiredBytes = metadata.validityByteOffset + metadata.sampleCount;
    if (payload.byteLength < requiredBytes) return false;
    const directions = new Float32Array(payload, metadata.directionByteOffset, metadata.sampleCount * 3);
    const validity = new Uint8Array(payload, metadata.validityByteOffset, metadata.sampleCount);
    const positions = new Float32Array(metadata.sampleCount * 3);
    for (let index = 0; index < metadata.sampleCount; index++) {
      const offset = index * 3;
      if (validity[index] === 0) {
        positions[offset] = Number.NaN;
        positions[offset + 1] = Number.NaN;
        positions[offset + 2] = Number.NaN;
        continue;
      }
      threeFromEnu([
        directions[offset] ?? 0,
        directions[offset + 1] ?? 0,
        directions[offset + 2] ?? 0,
      ]).normalize().multiplyScalar(TRAJECTORY_RADIUS).toArray(positions, offset);
    }
    const visual = previous ?? this.createVisual(metadata.bodyId);
    const geometry = visual.line.geometry;
    geometry.setAttribute("position", new THREE.BufferAttribute(positions, 3));
    geometry.computeBoundingSphere();
    visual.version = metadata.version;
    visual.observerGeneration = metadata.observerGeneration;
    visual.line.visible = this.enabled;
    visual.line.userData.trajectoryMetadata = metadata;
    this._resourceApplyCount++;
    this._bridgeBytes = payload.byteLength;
    return true;
  }

  setEnabled(enabled: boolean): void {
    this.enabled = enabled;
    this.root.visible = enabled;
  }

  metrics(): ApparentTrajectoryMetrics {
    return {
      geometryBuildCount: this._geometryBuildCount,
      materialBuildCount: this._materialBuildCount,
      resourceApplyCount: this._resourceApplyCount,
      staleResourceCount: this._staleResourceCount,
      bridgeBytes: this._bridgeBytes,
    };
  }

  dispose(): void {
    if (this.disposed) return;
    this.disposed = true;
    this.root.removeFromParent();
    for (const visual of this.visuals.values()) {
      visual.line.geometry.dispose();
      visual.line.material.dispose();
    }
    this.visuals.clear();
  }

  private createVisual(bodyId: string): TrajectoryVisual {
    const geometry = new THREE.BufferGeometry();
    const material = new THREE.LineBasicMaterial({
      color: trajectoryColor(bodyId),
      transparent: true,
      opacity: 0.72,
      depthWrite: false,
      depthTest: false,
    });
    const line = new THREE.Line(geometry, material);
    line.name = `apparentTrajectory:${bodyId}`;
    line.frustumCulled = false;
    line.renderOrder = -220;
    this.root.add(line);
    const visual = { line, version: "", observerGeneration: -1 };
    this.visuals.set(bodyId, visual);
    this._geometryBuildCount++;
    this._materialBuildCount++;
    return visual;
  }
}

function trajectoryColor(bodyId: string): number {
  if (bodyId === "sun") return 0xffc86b;
  if (bodyId === "moon") return 0xcad8ff;
  return 0x7fc7ff;
}
