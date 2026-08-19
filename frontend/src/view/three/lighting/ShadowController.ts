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
const LOG_PREFIX = "MGP: [ShadowController]";

export interface ShadowQualityTiming {
  readonly p50Ms: number;
  readonly p95Ms: number;
  readonly sampleCount: number;
}

export interface ShadowMetrics {
  readonly quality: ShadowQuality;
  readonly sunShadowUpdateCount: number;
  readonly moonShadowUpdateCount: 0;
  readonly shadowMapEstimateBytes: number;
  readonly timings: Readonly<Record<ShadowQuality, ShadowQualityTiming>>;
}

/** Renderer-side local shadow policy. It never alters scientific directions. */
export class ShadowController {
  private quality: ShadowQuality = "off";
  private readonly anchor = new THREE.Vector3();
  private readonly latestCamera = new THREE.Vector3();
  private readonly sunDirection = new THREE.Vector3(0, 1, 0);
  private readonly moonDirection = new THREE.Vector3(0, 1, 0);
  private sunActive = false;
  private anchorReady = false;
  private disposed = false;
  private _sunShadowUpdateCount = 0;
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
    this.renderer.shadowMap.autoUpdate = false;
    this.renderer.shadowMap.type = THREE.PCFSoftShadowMap;
    this.setQuality("medium");
  }

  setQuality(quality: ShadowQuality): void {
    if (this.disposed || quality === this.quality) return;
    const previous = this.quality;
    this.quality = quality;
    const profile = PROFILES[quality];
    this.renderer.shadowMap.enabled = quality !== "off";
    this.sunLight.castShadow = quality !== "off" && this.sunActive;
    // Lunar shadows remain deliberately optional/off in Pas 8.7.
    this.moonLight.castShadow = false;
    if (quality !== "off") {
      this.configureSunShadow(profile);
      this.updateAnchor(this.latestCamera, true);
      this.invalidate("quality_changed");
    }
    console.debug(`${LOG_PREFIX} [setQuality] [Qualitat canviada previous=${previous} current=${quality}]`);
  }

  getQuality(): ShadowQuality {
    return this.quality;
  }

  applySunDirection(directionToSourceThree: THREE.Vector3, active: boolean): void {
    if (this.disposed) return;
    const next = safeDirection(directionToSourceThree, this.sunDirection);
    const changed = THREE.MathUtils.radToDeg(this.sunDirection.angleTo(next)) >= DIRECTION_INVALIDATION_DEG;
    const activityChanged = active !== this.sunActive;
    this.sunDirection.copy(next);
    this.sunActive = active;
    this.sunLight.castShadow = this.quality !== "off" && active;
    this.positionLights();
    if (changed || activityChanged) this.invalidate("sun_direction_changed");
  }

  applyMoonDirection(directionToSourceThree: THREE.Vector3): void {
    if (this.disposed) return;
    this.moonDirection.copy(safeDirection(directionToSourceThree, this.moonDirection));
    this.positionLights();
  }

  updateCamera(cameraPosition: THREE.Vector3): void {
    if (this.disposed) return;
    this.latestCamera.copy(cameraPosition);
    this.updateAnchor(cameraPosition, false);
  }

  invalidateGeometry(): void {
    this.invalidate("caster_receiver_geometry_changed");
  }

  recordFrame(frameMs: number): void {
    if (!Number.isFinite(frameMs) || frameMs <= 0 || frameMs > 1_000) return;
    const samples = this.frameTimes[this.quality];
    samples.push(frameMs);
    if (samples.length > 600) samples.shift();
  }

  metrics(): ShadowMetrics {
    const profile = PROFILES[this.quality];
    return {
      quality: this.quality,
      sunShadowUpdateCount: this._sunShadowUpdateCount,
      moonShadowUpdateCount: 0,
      shadowMapEstimateBytes: profile.mapSize * profile.mapSize * 4,
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

  private configureSunShadow(profile: ShadowProfile): void {
    if (this.sunLight.shadow.mapSize.x !== profile.mapSize) {
      this.sunLight.shadow.map?.dispose();
      this.sunLight.shadow.map = null;
    }
    this.sunLight.shadow.mapSize.set(profile.mapSize, profile.mapSize);
    this.sunLight.shadow.bias = profile.bias;
    this.sunLight.shadow.normalBias = profile.normalBias;
    this.sunLight.shadow.radius = 1;
    const camera = this.sunLight.shadow.camera;
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
    this.invalidate("camera_left_shadow_region");
  }

  private positionLights(): void {
    const profile = PROFILES[this.quality];
    const distance = Math.max(500, profile.localRadiusM * 3);
    this.sunTarget.position.copy(this.anchor);
    this.sunLight.position.copy(this.anchor).addScaledVector(this.sunDirection, distance);
    this.moonTarget.position.copy(this.anchor);
    this.moonLight.position.copy(this.anchor).addScaledVector(this.moonDirection, distance);
    this.sunTarget.updateMatrixWorld();
    this.moonTarget.updateMatrixWorld();
  }

  private invalidate(_reason: string): void {
    if (this.quality === "off" || !this.sunActive || !this.sunLight.castShadow) return;
    this.renderer.shadowMap.needsUpdate = true;
    this._sunShadowUpdateCount++;
  }
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
  return sorted[index]!;
}
