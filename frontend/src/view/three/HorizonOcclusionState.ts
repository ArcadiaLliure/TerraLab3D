import * as THREE from "three";

import type {
  HorizonProfileMetadata,
  HorizonQuality,
} from "../../contracts/horizon_contracts";
import { azimuthAltitudeFromThreeDirection } from "./celestialCoordinates";

export interface HorizonGpuUniformValues {
  readonly texture: THREE.DataTexture;
  readonly sampleCount: number;
  readonly textureWidth: number;
  readonly textureHeight: number;
  readonly enabled: number;
}

export interface HorizonOcclusionSnapshot {
  readonly metadata: HorizonProfileMetadata;
  readonly horizonElevationDeg: Float32Array;
  readonly occluderDistanceM: Float32Array;
  readonly occluderHeightM: Float32Array;
  readonly validMask: Uint8Array;
  readonly texture: THREE.DataTexture;
  readonly textureWidth: number;
  readonly textureHeight: number;
}

type HorizonListener = (snapshot: HorizonOcclusionSnapshot) => void;

export class HorizonOcclusionState {
  private snapshot: HorizonOcclusionSnapshot;
  private readonly listeners = new Set<HorizonListener>();
  private enabled = true;
  private disposed = false;
  private readonly lookupTimesMs: number[] = [];
  private textureBuildCount = 0;
  private uploadBytes = 0;

  constructor(private readonly maxTextureSize: number) {
    this.snapshot = this.buildFallback();
  }

  public get active(): HorizonOcclusionSnapshot {
    return this.snapshot;
  }

  public get quality(): HorizonQuality {
    return this.snapshot.metadata.quality;
  }

  public get hasDemBackedProfile(): boolean {
    return this.quality === "REAL" || this.quality === "PARTIAL_DEM";
  }

  public setEnabled(enabled: boolean): void {
    this.enabled = enabled;
    this.notify();
  }

  public subscribe(listener: HorizonListener): () => void {
    this.listeners.add(listener);
    listener(this.snapshot);
    return () => this.listeners.delete(listener);
  }

  public applyBinaryResource(metadata: HorizonProfileMetadata, payload: ArrayBuffer): boolean {
    if (this.disposed) return false;
    if (metadata.role !== "horizon_profile") return false;
    if (metadata.version <= this.snapshot.metadata.version) return false;
    if (metadata.sampleCount < 1 || metadata.byteLength !== payload.byteLength) {
      throw new Error("Invalid horizon resource dimensions");
    }
    const layout = metadata.bufferLayout;
    const count = metadata.sampleCount;
    const horizon = copyFloat32(payload, layout.horizonElevationDeg.offset, count);
    const distance = copyFloat32(payload, layout.occluderDistanceM.offset, count);
    const height = copyFloat32(payload, layout.occluderHeightM.offset, count);
    const valid = new Uint8Array(
      new Uint8Array(payload, layout.validMask.offset, count),
    );
    const prepared = this.prepareSnapshot(metadata, horizon, distance, height, valid);
    const previous = this.snapshot;
    this.snapshot = prepared;
    this.notify();
    previous.texture.dispose();
    return true;
  }

  public horizonElevationAtAzimuth(azimuthDeg: number): number {
    const started = performance.now();
    const snapshot = this.snapshot;
    if (!this.enabled || snapshot.metadata.sampleCount === 0) return 0;
    const normalized = ((azimuthDeg - snapshot.metadata.azimuthStartDeg) % 360 + 360) % 360;
    const position = normalized / snapshot.metadata.angularStepDeg;
    const leftFloor = Math.floor(position);
    const left = leftFloor % snapshot.metadata.sampleCount;
    const right = (left + 1) % snapshot.metadata.sampleCount;
    const fraction = position - leftFloor;
    const leftValue = snapshot.validMask[left] !== 0 ? snapshot.horizonElevationDeg[left]! : 0;
    const rightValue = snapshot.validMask[right] !== 0 ? snapshot.horizonElevationDeg[right]! : 0;
    const value = leftValue + (rightValue - leftValue) * fraction;
    this.lookupTimesMs.push(performance.now() - started);
    if (this.lookupTimesMs.length > 1024) this.lookupTimesMs.shift();
    return value;
  }

  public isOccludedAzimuthAltitude(azimuthDeg: number, altitudeDeg: number): boolean {
    return altitudeDeg < this.horizonElevationAtAzimuth(azimuthDeg);
  }

  public isOccludedDirection(direction: { x: number; y: number; z: number }): boolean {
    const horizontal = azimuthAltitudeFromThreeDirection(direction);
    return horizontal === null
      ? false
      : this.isOccludedAzimuthAltitude(horizontal.azimuthDeg, horizontal.altitudeDeg);
  }

  public isDiscFullyOccluded(
    azimuthDeg: number,
    centerAltitudeDeg: number,
    angularRadiusDeg: number,
  ): boolean {
    return centerAltitudeDeg + angularRadiusDeg < this.horizonElevationAtAzimuth(azimuthDeg);
  }

  public gpuUniformValues(): HorizonGpuUniformValues {
    return {
      texture: this.snapshot.texture,
      sampleCount: this.snapshot.metadata.sampleCount,
      textureWidth: this.snapshot.textureWidth,
      textureHeight: this.snapshot.textureHeight,
      enabled: this.enabled ? 1 : 0,
    };
  }

  public metrics(): {
    readonly horizonUploadBytes: number;
    readonly horizonTextureBuildCount: number;
    readonly activeTextureCount: number;
    readonly horizonLookupCpuP50: number;
    readonly horizonLookupCpuP95: number;
  } {
    const sorted = [...this.lookupTimesMs].sort((a, b) => a - b);
    return {
      horizonUploadBytes: this.uploadBytes,
      horizonTextureBuildCount: this.textureBuildCount,
      activeTextureCount: this.disposed ? 0 : 1,
      horizonLookupCpuP50: percentile(sorted, 0.50),
      horizonLookupCpuP95: percentile(sorted, 0.95),
    };
  }

  public dispose(): void {
    if (this.disposed) return;
    this.disposed = true;
    this.snapshot.texture.dispose();
    this.listeners.clear();
  }

  private buildFallback(): HorizonOcclusionSnapshot {
    const count = 720;
    const zeros = new Float32Array(count);
    return this.prepareSnapshot({
      role: "horizon_profile",
      resourceId: "earth.horizon.profile",
      version: 0,
      contentKey: "frontend-flat-fallback",
      sourceIds: [],
      sourceFingerprint: "unavailable",
      observerGeneration: 0,
      latitudeDeg: 0,
      longitudeDeg: 0,
      terrainElevationM: null,
      eyeElevationM: null,
      visibleRadiusM: 150_000,
      azimuthStartDeg: 0,
      angularStepDeg: 0.5,
      sampleCount: count,
      quality: "FLAT_FALLBACK",
      resolvedFraction: 0,
      kernelVersion: "frontend-flat-v1",
      byteLength: count * 13,
      bufferLayout: {
        horizonElevationDeg: { offset: 0, length: count * 4, dtype: "float32" },
        occluderDistanceM: { offset: count * 4, length: count * 4, dtype: "float32" },
        occluderHeightM: { offset: count * 8, length: count * 4, dtype: "float32" },
        validMask: { offset: count * 12, length: count, dtype: "uint8" },
      },
    }, zeros, zeros.slice(), zeros.slice(), new Uint8Array(count).fill(1));
  }

  private prepareSnapshot(
    metadata: HorizonProfileMetadata,
    horizon: Float32Array,
    distance: Float32Array,
    height: Float32Array,
    valid: Uint8Array,
  ): HorizonOcclusionSnapshot {
    const width = Math.max(1, Math.min(metadata.sampleCount, this.maxTextureSize));
    const textureHeight = Math.ceil(metadata.sampleCount / width);
    const packed = new Float32Array(width * textureHeight);
    for (let index = 0; index < metadata.sampleCount; index++) {
      packed[index] = valid[index] !== 0 ? horizon[index]! : 0;
    }
    const texture = new THREE.DataTexture(
      packed,
      width,
      textureHeight,
      THREE.RedFormat,
      THREE.FloatType,
    );
    texture.minFilter = THREE.NearestFilter;
    texture.magFilter = THREE.NearestFilter;
    texture.wrapS = THREE.ClampToEdgeWrapping;
    texture.wrapT = THREE.ClampToEdgeWrapping;
    texture.generateMipmaps = false;
    texture.needsUpdate = true;
    this.textureBuildCount++;
    this.uploadBytes += packed.byteLength;
    return {
      metadata,
      horizonElevationDeg: horizon,
      occluderDistanceM: distance,
      occluderHeightM: height,
      validMask: valid,
      texture,
      textureWidth: width,
      textureHeight,
    };
  }

  private notify(): void {
    for (const listener of this.listeners) listener(this.snapshot);
  }
}

function copyFloat32(buffer: ArrayBuffer, byteOffset: number, count: number): Float32Array {
  return new Float32Array(new Float32Array(buffer, byteOffset, count));
}

function percentile(samples: readonly number[], fraction: number): number {
  if (samples.length === 0) return 0;
  return samples[Math.round((samples.length - 1) * fraction)]!;
}
