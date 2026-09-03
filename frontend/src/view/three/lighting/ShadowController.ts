import * as THREE from "three";

export type ShadowQuality = "off" | "low" | "medium" | "high";

interface ShadowProfile {
  readonly mapSize: number;
  readonly localRadiusM: number;
  readonly bias: number;
  readonly normalBias: number;
}

const PROFILES: Readonly<Record<ShadowQuality, ShadowProfile>> = {
  off: { mapSize: 0, localRadiusM: 0, bias: 0, normalBias: 0 },
  low: { mapSize: 512, localRadiusM: 80, bias: -0.0005, normalBias: 0.035 },
  medium: { mapSize: 1024, localRadiusM: 160, bias: -0.0004, normalBias: 0.04 },
  high: { mapSize: 2048, localRadiusM: 240, bias: -0.0003, normalBias: 0.045 },
};

const DIRECTION_INVALIDATION_DEG = 0.15;
const SHADOW_FRAME_BUDGET_MS = 24;
const MAX_SHADOW_DEFER_MS = 750;
const LOG_PREFIX = "MGP: [ShadowController]";

export interface ShadowQualityTiming {
  readonly p50Ms: number;
  readonly p95Ms: number;
  readonly sampleCount: number;
}

export interface ShadowMetrics {
  readonly quality: ShadowQuality;
  readonly sunShadowUpdateCount: number;
  readonly moonShadowUpdateCount: number;
  readonly shadowMapEstimateBytes: number;
  readonly timings: Readonly<Record<ShadowQuality, ShadowQualityTiming>>;
}

interface ScheduledShadow {
  readonly light: THREE.DirectionalLight;
  readonly direction: THREE.Vector3;
  readonly renderedDirection: THREE.Vector3;
  active: boolean;
  photometricImportance: number;
  dirty: boolean;
  lastScheduledMs: number;
  updateCount: number;
}

/** Derived GPU shadow scheduler. Source photometry and directions remain untouched. */
export class ShadowController {
  private quality: ShadowQuality = "off";
  private readonly anchor = new THREE.Vector3();
  private readonly latestCamera = new THREE.Vector3();
  private readonly sun: ScheduledShadow;
  private readonly moon: ScheduledShadow;
  private anchorReady = false;
  private disposed = false;
  private lastFrameMs = 0;
  private readonly frameTimes: Record<ShadowQuality, number[]> = {
    off: [], low: [], medium: [], high: [],
  };

  constructor(
    private readonly renderer: THREE.WebGLRenderer,
    private readonly sunLight: THREE.DirectionalLight,
    private readonly sunTarget: THREE.Object3D,
    private readonly moonLight: THREE.DirectionalLight,
    private readonly moonTarget: THREE.Object3D,
  ) {
    this.sun = scheduledShadow(sunLight);
    this.moon = scheduledShadow(moonLight);
    this.renderer.shadowMap.autoUpdate = false;
    this.renderer.shadowMap.type = THREE.PCFSoftShadowMap;
    this.sunLight.shadow.autoUpdate = false;
    this.moonLight.shadow.autoUpdate = false;
    this.setQuality("medium");
  }

  setQuality(quality: ShadowQuality): void {
    if (this.disposed || quality === this.quality) return;
    const previous = this.quality;
    this.quality = quality;
    const profile = PROFILES[quality];
    this.renderer.shadowMap.enabled = quality !== "off";
    this.syncCastShadow();
    if (quality !== "off") {
      this.configureShadow(this.sunLight, profile);
      this.configureShadow(this.moonLight, profile);
      this.updateAnchor(this.latestCamera, true);
      this.markDirty(this.sun);
      this.markDirty(this.moon);
    }
    console.debug(`${LOG_PREFIX} [setQuality] [Qualitat canviada previous=${previous} current=${quality}]`);
  }

  getQuality(): ShadowQuality {
    return this.quality;
  }

  applySunDirection(
    directionToSourceThree: THREE.Vector3,
    active: boolean,
    photometricImportance: number,
  ): void {
    this.applyLightState(
      this.sun,
      directionToSourceThree,
      active,
      photometricImportance,
    );
  }

  applyMoonDirection(
    directionToSourceThree: THREE.Vector3,
    active: boolean,
    photometricImportance: number,
  ): void {
    this.applyLightState(
      this.moon,
      directionToSourceThree,
      active,
      photometricImportance,
    );
  }

  updateCamera(cameraPosition: THREE.Vector3, timestampMs: number): void {
    if (this.disposed) return;
    this.latestCamera.copy(cameraPosition);
    this.updateAnchor(cameraPosition, false);
    this.scheduleOneShadow(timestampMs);
  }

  invalidateGeometry(): void {
    this.markDirty(this.sun);
    this.markDirty(this.moon);
  }

  recordFrame(frameMs: number): void {
    if (!Number.isFinite(frameMs) || frameMs <= 0 || frameMs > 1_000) return;
    const samples = this.frameTimes[this.quality];
    this.lastFrameMs = frameMs;
    samples.push(frameMs);
    if (samples.length > 600) samples.shift();
  }

  metrics(): ShadowMetrics {
    const profile = PROFILES[this.quality];
    return {
      quality: this.quality,
      sunShadowUpdateCount: this.sun.updateCount,
      moonShadowUpdateCount: this.moon.updateCount,
      shadowMapEstimateBytes: profile.mapSize * profile.mapSize * 4 * 2,
      timings: {
        off: timing(this.frameTimes.off),
        low: timing(this.frameTimes.low),
        medium: timing(this.frameTimes.medium),
        high: timing(this.frameTimes.high),
      },
    };
  }

  dispose(): void {
    if (this.disposed) return;
    this.disposed = true;
    this.sunLight.castShadow = false;
    this.moonLight.castShadow = false;
    this.sunLight.shadow.dispose();
    this.moonLight.shadow.dispose();
    this.renderer.shadowMap.enabled = false;
    console.info("MGP: [ShadowController.ts] [dispose] [Recursos d'ombres alliberats]");
  }

  private applyLightState(
    state: ScheduledShadow,
    direction: THREE.Vector3,
    active: boolean,
    photometricImportance: number,
  ): void {
    if (this.disposed) return;
    const next = safeDirection(direction, state.direction);
    const activityChanged = active !== state.active;
    state.direction.copy(next);
    state.active = active;
    state.photometricImportance = Math.max(0, photometricImportance);
    if (activityChanged || angularErrorDeg(state) >= DIRECTION_INVALIDATION_DEG) {
      this.markDirty(state);
    }
    this.syncCastShadow();
    this.positionLights();
  }

  private configureShadow(light: THREE.DirectionalLight, profile: ShadowProfile): void {
    if (light.shadow.mapSize.x !== profile.mapSize) {
      light.shadow.map?.dispose();
      light.shadow.map = null;
    }
    light.shadow.mapSize.set(profile.mapSize, profile.mapSize);
    light.shadow.bias = profile.bias;
    light.shadow.normalBias = profile.normalBias;
    light.shadow.radius = 1;
    const camera = light.shadow.camera;
    camera.left = -profile.localRadiusM;
    camera.right = profile.localRadiusM;
    camera.top = profile.localRadiusM;
    camera.bottom = -profile.localRadiusM;
    camera.near = 1;
    camera.far = profile.localRadiusM * 6 + 300;
    camera.updateProjectionMatrix();
  }

  private updateAnchor(cameraPosition: THREE.Vector3, force: boolean): void {
    const profile = PROFILES[this.quality];
    if (profile.localRadiusM <= 0) return;
    const horizontalDistance = Math.hypot(
      cameraPosition.x - this.anchor.x,
      cameraPosition.z - this.anchor.z,
    );
    if (!force && this.anchorReady && horizontalDistance < profile.localRadiusM * 0.22) return;
    const texelWorldSize = profile.localRadiusM * 2 / profile.mapSize;
    this.anchor.set(
      Math.round(cameraPosition.x / texelWorldSize) * texelWorldSize,
      0,
      Math.round(cameraPosition.z / texelWorldSize) * texelWorldSize,
    );
    this.anchorReady = true;
    this.positionLights();
    this.markDirty(this.sun);
    this.markDirty(this.moon);
  }

  private positionLights(): void {
    const profile = PROFILES[this.quality];
    const distance = Math.max(500, profile.localRadiusM * 3);
    this.sunTarget.position.copy(this.anchor);
    this.sunLight.position.copy(this.anchor).addScaledVector(this.sun.direction, distance);
    this.moonTarget.position.copy(this.anchor);
    this.moonLight.position.copy(this.anchor).addScaledVector(this.moon.direction, distance);
    this.sunTarget.updateMatrixWorld();
    this.moonTarget.updateMatrixWorld();
  }

  private scheduleOneShadow(timestampMs: number): void {
    if (this.quality === "off") return;
    const candidates = [this.sun, this.moon].filter((state) => state.active && state.dirty);
    if (candidates.length === 0) return;
    const oldestAgeMs = Math.max(
      ...candidates.map((state) => Math.max(0, timestampMs - state.lastScheduledMs)),
    );
    if (this.lastFrameMs > SHADOW_FRAME_BUDGET_MS && oldestAgeMs < MAX_SHADOW_DEFER_MS) {
      return;
    }
    candidates.sort((left, right) => shadowPriority(right, timestampMs) - shadowPriority(left, timestampMs));
    const selected = candidates[0]!;
    selected.light.shadow.needsUpdate = true;
    this.renderer.shadowMap.needsUpdate = true;
    selected.renderedDirection.copy(selected.direction);
    selected.dirty = false;
    selected.lastScheduledMs = timestampMs;
    selected.updateCount++;
  }

  private markDirty(state: ScheduledShadow): void {
    if (!state.active) return;
    state.dirty = true;
  }

  private syncCastShadow(): void {
    const enabled = this.quality !== "off";
    this.sunLight.castShadow = enabled && this.sun.active;
    this.moonLight.castShadow = enabled && this.moon.active;
  }
}

function scheduledShadow(light: THREE.DirectionalLight): ScheduledShadow {
  return {
    light,
    direction: new THREE.Vector3(0, 1, 0),
    renderedDirection: new THREE.Vector3(0, 1, 0),
    active: false,
    photometricImportance: 0,
    dirty: false,
    lastScheduledMs: 0,
    updateCount: 0,
  };
}

function shadowPriority(state: ScheduledShadow, timestampMs: number): number {
  const ageMs = Math.max(0, timestampMs - state.lastScheduledMs);
  const starvationBoost = 1 + Math.min(ageMs / 250, 20);
  return (angularErrorDeg(state) + 0.01) * Math.max(state.photometricImportance, 0.001)
    * starvationBoost;
}

function angularErrorDeg(state: ScheduledShadow): number {
  return THREE.MathUtils.radToDeg(state.renderedDirection.angleTo(state.direction));
}

function safeDirection(value: THREE.Vector3, fallback: THREE.Vector3): THREE.Vector3 {
  return value.lengthSq() > 1e-12 && finiteVector(value)
    ? value.clone().normalize()
    : fallback.clone();
}

function finiteVector(value: THREE.Vector3): boolean {
  return Number.isFinite(value.x) && Number.isFinite(value.y) && Number.isFinite(value.z);
}

function timing(samples: readonly number[]): ShadowQualityTiming {
  return {
    p50Ms: percentile(samples, 0.50),
    p95Ms: percentile(samples, 0.95),
    sampleCount: samples.length,
  };
}

function percentile(samples: readonly number[], fraction: number): number {
  if (samples.length === 0) return 0;
  const sorted = [...samples].sort((a, b) => a - b);
  const index = Math.round((sorted.length - 1) * fraction);
  return sorted[index] ?? 0;
}
