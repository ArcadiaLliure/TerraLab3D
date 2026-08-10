import * as THREE from "three";
import { EXRLoader } from "three/examples/jsm/loaders/EXRLoader.js";

import type { SkyEnvironmentSnapshot } from "../../contracts/sky_environment_contracts";
import type { CelestialTransformState } from "./CelestialTransformState";
import {
  GALACTIC_FRAGMENT_SHADER,
  GALACTIC_VERTEX_SHADER,
} from "./shaders/galacticShader";

export interface GalacticTextureResource {
  readonly resourceId: "sky.milky_way" | "sky.planck_dust";
  readonly version: string;
  readonly url: string;
  readonly width: number;
  readonly height: number;
}

export interface GalacticTextureLoader {
  loadMilkyWay(url: string): Promise<THREE.Texture>;
  loadPlanckDust(url: string): Promise<THREE.Texture>;
}

export interface GalacticRendererMetrics {
  readonly geometryBuildCount: number;
  readonly materialBuildCount: number;
  readonly milkyWayTextureLoadCount: number;
  readonly planckTextureLoadCount: number;
  readonly staleTextureCount: number;
  readonly textureUploadBytes: number;
  readonly activeTextureCount: number;
}

export interface GalacticLayerVisibility {
  readonly localFrameReady: boolean;
  readonly milkyWayVisible: boolean;
  readonly planckDustVisible: boolean;
}

class ThreeGalacticTextureLoader implements GalacticTextureLoader {
  async loadMilkyWay(url: string): Promise<THREE.Texture> {
    return new EXRLoader().loadAsync(url);
  }

  async loadPlanckDust(url: string): Promise<THREE.Texture> {
    return new THREE.TextureLoader().loadAsync(url);
  }
}

interface ResidentTexture {
  readonly version: string;
  readonly texture: THREE.Texture;
  readonly estimatedBytes: number;
}

const SKY_RADIUS = 900_000;

export class GalacticSkyRenderer {
  private readonly geometry: THREE.SphereGeometry;
  private readonly material: THREE.ShaderMaterial;
  private readonly mesh: THREE.Mesh;
  private readonly emptyMilkyWayTexture = blackTexture();
  private readonly emptyDustTexture = blackTexture();
  private transformState: CelestialTransformState | null = null;
  private milkyWay: ResidentTexture | null = null;
  private planckDust: ResidentTexture | null = null;
  private milkyWayRequestedVisible = false;
  private planckDustRequestedVisible = false;
  private milkyWayRevision = 0;
  private planckRevision = 0;
  private disposed = false;
  private _milkyWayTextureLoadCount = 0;
  private _planckTextureLoadCount = 0;
  private _staleTextureCount = 0;

  constructor(
    parent: THREE.Object3D,
    private readonly maxTextureSize: number,
    private readonly loader: GalacticTextureLoader = new ThreeGalacticTextureLoader(),
  ) {
    this.geometry = new THREE.SphereGeometry(1, 128, 64);
    this.material = new THREE.ShaderMaterial({
      vertexShader: GALACTIC_VERTEX_SHADER,
      fragmentShader: GALACTIC_FRAGMENT_SHADER,
      uniforms: {
        u_equatorialToThree: { value: new THREE.Matrix3() },
        u_radius: { value: SKY_RADIUS },
        u_milkyWayTexture: { value: this.emptyMilkyWayTexture },
        u_planckDustTexture: { value: this.emptyDustTexture },
        u_milkyWayEnabled: { value: false },
        u_planckDustEnabled: { value: false },
        u_milkyWayOpacity: { value: 0.72 },
        u_dustDensityStrength: { value: 0.32 },
        u_dustExtinctionStrength: { value: 0.65 },
        u_skyVisibility: { value: 1.0 },
      },
      side: THREE.BackSide,
      transparent: true,
      depthWrite: false,
      depthTest: true,
      blending: THREE.AdditiveBlending,
    });
    this.mesh = new THREE.Mesh(this.geometry, this.material);
    this.mesh.name = "galacticSkydome";
    this.mesh.renderOrder = -900;
    this.mesh.frustumCulled = false;
    parent.add(this.mesh);
  }

  setTransformState(state: CelestialTransformState): void {
    this.transformState = state;
    this.syncTransform();
  }

  syncTransform(): void {
    if (!this.transformState?.isValid) {
      this.syncLayerVisibility();
      return;
    }
    uniform<THREE.Matrix3>(this.material, "u_equatorialToThree")
      .value.copy(this.transformState.equatorialToThree);
    this.syncLayerVisibility();
  }

  updateEnvironment(snapshot: SkyEnvironmentSnapshot): void {
    uniform<number>(this.material, "u_skyVisibility").value = galacticVisibilityFactor(snapshot);
  }

  setMilkyWayVisible(visible: boolean): void {
    this.milkyWayRequestedVisible = visible;
    this.syncLayerVisibility();
  }

  setPlanckDustVisible(visible: boolean): void {
    this.planckDustRequestedVisible = visible;
    this.syncLayerVisibility();
  }

  async installMilkyWay(resource: GalacticTextureResource): Promise<void> {
    if (this.milkyWay?.version === resource.version) return;
    this.validateTexture(resource);
    const revision = ++this.milkyWayRevision;
    const texture = await this.loader.loadMilkyWay(resource.url);
    configureScientificTexture(texture);
    if (this.disposed || revision !== this.milkyWayRevision) {
      texture.dispose();
      this._staleTextureCount++;
      return;
    }
    this.milkyWay?.texture.dispose();
    this.milkyWay = {
      version: resource.version,
      texture,
      estimatedBytes: resource.width * resource.height * 8,
    };
    uniform<THREE.Texture>(this.material, "u_milkyWayTexture").value = texture;
    this._milkyWayTextureLoadCount++;
    this.syncLayerVisibility();
  }

  async installPlanckDust(resource: GalacticTextureResource): Promise<void> {
    if (this.planckDust?.version === resource.version) return;
    this.validateTexture(resource);
    const revision = ++this.planckRevision;
    const texture = await this.loader.loadPlanckDust(resource.url);
    configureScientificTexture(texture);
    if (this.disposed || revision !== this.planckRevision) {
      texture.dispose();
      this._staleTextureCount++;
      return;
    }
    this.planckDust?.texture.dispose();
    this.planckDust = {
      version: resource.version,
      texture,
      estimatedBytes: resource.width * resource.height * 4,
    };
    uniform<THREE.Texture>(this.material, "u_planckDustTexture").value = texture;
    this._planckTextureLoadCount++;
    this.syncLayerVisibility();
  }

  metrics(): GalacticRendererMetrics {
    return {
      geometryBuildCount: 1,
      materialBuildCount: 1,
      milkyWayTextureLoadCount: this._milkyWayTextureLoadCount,
      planckTextureLoadCount: this._planckTextureLoadCount,
      staleTextureCount: this._staleTextureCount,
      textureUploadBytes: (this.milkyWay?.estimatedBytes ?? 0) + (this.planckDust?.estimatedBytes ?? 0),
      activeTextureCount: Number(this.milkyWay !== null) + Number(this.planckDust !== null),
    };
  }

  getTransformMatrix(): THREE.Matrix3 {
    return uniform<THREE.Matrix3>(this.material, "u_equatorialToThree").value.clone();
  }

  getLayerVisibility(): GalacticLayerVisibility {
    return {
      localFrameReady: this.transformState?.isValid ?? false,
      milkyWayVisible: uniform<boolean>(this.material, "u_milkyWayEnabled").value,
      planckDustVisible: uniform<boolean>(this.material, "u_planckDustEnabled").value,
    };
  }

  dispose(): void {
    if (this.disposed) return;
    this.disposed = true;
    this.milkyWayRevision++;
    this.planckRevision++;
    this.mesh.removeFromParent();
    this.milkyWay?.texture.dispose();
    this.planckDust?.texture.dispose();
    this.emptyMilkyWayTexture.dispose();
    this.emptyDustTexture.dispose();
    this.geometry.dispose();
    this.material.dispose();
    this.milkyWay = null;
    this.planckDust = null;
  }

  private validateTexture(resource: GalacticTextureResource): void {
    if (resource.width <= 0 || resource.height <= 0) {
      throw new Error(`Dimensions invàlides per a ${resource.resourceId}`);
    }
    if (resource.width > this.maxTextureSize || resource.height > this.maxTextureSize) {
      throw new Error(
        `${resource.width}×${resource.height} supera el límit GPU ${this.maxTextureSize}px`,
      );
    }
  }

  private syncLayerVisibility(): void {
    const localFrameReady = this.transformState?.isValid ?? false;
    uniform<boolean>(this.material, "u_milkyWayEnabled").value =
      localFrameReady && this.milkyWayRequestedVisible && this.milkyWay !== null;
    uniform<boolean>(this.material, "u_planckDustEnabled").value =
      localFrameReady && this.planckDustRequestedVisible && this.planckDust !== null;
  }
}

export function galacticVisibilityFactor(snapshot: SkyEnvironmentSnapshot): number {
  const darkness = clamp01(1 - snapshot.visibility.skyBrightnessNormalized);
  const bortle = snapshot.lightPollutionEnabled && snapshot.bortleClass !== null
    ? clamp01(1 - (snapshot.bortleClass - 1) / 8)
    : 1;
  return Math.pow(darkness, 1.6) * (0.18 + 0.82 * bortle);
}

function configureScientificTexture(texture: THREE.Texture): void {
  texture.wrapS = THREE.RepeatWrapping;
  texture.wrapT = THREE.ClampToEdgeWrapping;
  texture.magFilter = THREE.LinearFilter;
  texture.minFilter = THREE.LinearFilter;
  texture.generateMipmaps = false;
  texture.flipY = false;
  texture.colorSpace = THREE.NoColorSpace;
  texture.needsUpdate = true;
}

function blackTexture(): THREE.DataTexture {
  const texture = new THREE.DataTexture(new Uint8Array([0, 0, 0, 255]), 1, 1, THREE.RGBAFormat);
  texture.needsUpdate = true;
  texture.colorSpace = THREE.NoColorSpace;
  return texture;
}

function uniform<T>(material: THREE.ShaderMaterial, name: string): THREE.IUniform<T> {
  const found = material.uniforms[name];
  if (found === undefined) throw new Error(`Missing galactic shader uniform: ${name}`);
  return found as THREE.IUniform<T>;
}

function clamp01(value: number): number {
  return Math.max(0, Math.min(1, value));
}
