import * as THREE from "three";

import type { SolarSystemBodyState, SolarSystemSnapshot } from "../../contracts/solar_system_contracts";
import { threeFromEnu, threeQuaternionFromBodyToEnu } from "./celestialCoordinates";

const CELESTIAL_RADIUS = 900_000;

export interface OrbitBinaryMetadata {
  readonly resourceId: string;
  readonly version: string;
  readonly role: "solar_system_orbit";
  readonly bodyId: string;
  readonly parentBodyId: string;
  readonly sampleCount: number;
  readonly frame: "J2000 planetocentric" | string;
  readonly kernelGeneration: string;
  readonly orbitGeneration: number;
  readonly componentType: "float32";
  readonly componentsPerVertex: 3;
}

interface OrbitEntry {
  readonly metadata: OrbitBinaryMetadata;
  readonly line: THREE.Line<THREE.BufferGeometry, THREE.LineBasicMaterial>;
}

export interface SatelliteOrbitMetrics {
  readonly geometryBuildCount: number;
  readonly materialBuildCount: number;
  readonly disposedGeometryCount: number;
  readonly bridgeBytes: number;
  readonly activeOrbitCount: number;
}

/** Persistent J2000 planetocentric orbit buffers with physical 1:1 angular scale. */
export class SatelliteOrbitRenderer {
  readonly root = new THREE.Group();
  private readonly entries = new Map<string, OrbitEntry>();
  private latestSnapshot: SolarSystemSnapshot | null = null;
  private enabled = false;
  private geometryBuildCount = 0;
  private disposedGeometryCount = 0;
  private bridgeBytes = 0;
  private disposed = false;

  constructor(parent: THREE.Object3D) {
    this.root.name = "satelliteOrbitsRoot";
    this.root.visible = false;
    parent.add(this.root);
  }

  registerBinaryResource(metadata: OrbitBinaryMetadata, buffer: ArrayBuffer): boolean {
    if (
      this.disposed
      || metadata.role !== "solar_system_orbit"
      || metadata.componentType !== "float32"
      || buffer.byteLength !== metadata.sampleCount * 3 * Float32Array.BYTES_PER_ELEMENT
    ) return false;
    const old = this.entries.get(metadata.bodyId);
    if (old !== undefined && old.metadata.orbitGeneration >= metadata.orbitGeneration) return false;
    if (old !== undefined) {
      old.line.removeFromParent();
      old.line.geometry.dispose();
      old.line.material.dispose();
      this.disposedGeometryCount++;
    }
    const geometry = new THREE.BufferGeometry();
    geometry.setAttribute("position", new THREE.BufferAttribute(new Float32Array(buffer), 3));
    const material = new THREE.LineBasicMaterial({
      color: 0x7fa8d8,
      transparent: true,
      opacity: 0.42,
      depthTest: true,
      depthWrite: false,
    });
    const line = new THREE.Line(geometry, material);
    line.name = metadata.resourceId;
    line.frustumCulled = false;
    line.visible = false;
    this.entries.set(metadata.bodyId, { metadata, line });
    this.root.add(line);
    this.geometryBuildCount++;
    this.bridgeBytes += buffer.byteLength;
    if (this.latestSnapshot !== null) this.updateSnapshot(this.latestSnapshot);
    return true;
  }

  updateSnapshot(snapshot: SolarSystemSnapshot): void {
    this.latestSnapshot = snapshot;
    const quaternion = snapshot.icrfToENUQuaternion;
    if (quaternion === undefined || quaternion === null) {
      for (const entry of this.entries.values()) entry.line.visible = false;
      return;
    }
    const states = statesById(snapshot);
    for (const entry of this.entries.values()) {
      const parent = states.get(entry.metadata.parentBodyId);
      if (parent === undefined || parent.distanceKm <= 0) {
        entry.line.visible = false;
        continue;
      }
      entry.line.position.copy(threeFromEnu(parent.directionENU).normalize()).multiplyScalar(CELESTIAL_RADIUS);
      entry.line.quaternion.copy(threeQuaternionFromBodyToEnu(quaternion));
      entry.line.scale.setScalar(CELESTIAL_RADIUS / parent.distanceKm);
      entry.line.visible = this.enabled;
    }
    this.root.visible = this.enabled && this.entries.size > 0;
  }

  setEnabled(enabled: boolean): void {
    this.enabled = enabled;
    this.root.visible = enabled && this.entries.size > 0;
    for (const entry of this.entries.values()) entry.line.visible = enabled;
    if (enabled && this.latestSnapshot !== null) this.updateSnapshot(this.latestSnapshot);
  }

  metrics(): SatelliteOrbitMetrics {
    return {
      geometryBuildCount: this.geometryBuildCount,
      materialBuildCount: this.geometryBuildCount,
      disposedGeometryCount: this.disposedGeometryCount,
      bridgeBytes: this.bridgeBytes,
      activeOrbitCount: this.entries.size,
    };
  }

  dispose(): void {
    if (this.disposed) return;
    this.disposed = true;
    this.root.removeFromParent();
    for (const entry of this.entries.values()) {
      entry.line.geometry.dispose();
      entry.line.material.dispose();
      this.disposedGeometryCount++;
    }
    this.entries.clear();
  }
}

function statesById(snapshot: SolarSystemSnapshot): Map<string, SolarSystemBodyState> {
  const result = new Map<string, SolarSystemBodyState>();
  result.set(snapshot.sun.id, snapshot.sun);
  if (snapshot.moon !== null) result.set(snapshot.moon.id, snapshot.moon);
  for (const state of snapshot.planets) result.set(state.id, state);
  for (const state of snapshot.satellites ?? []) result.set(state.id, state);
  return result;
}
