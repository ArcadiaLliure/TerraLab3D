import * as THREE from "three";

import type { SkyEnvironmentSnapshot } from "../../contracts/sky_environment_contracts";
import type {
  MoonSurfaceAsset,
  MoonSurfaceResourceDescriptor,
  SolarSystemBodyState,
} from "../../contracts/solar_system_contracts";
import {
  threeFromEnu,
  threeQuaternionFromBodyToEnu,
} from "./celestialCoordinates";

const FALLBACK_COLOR = new THREE.Color(0xd8d8d2);
const MIP_FACTOR = 4 / 3;
/** Exact lunar night-side term restored from commit 439b9f6. */
export const LUNAR_NIGHT_SIDE_VISIBILITY = 0.015;
/** Cancels MeshLambertMaterial's 1/π BRDF to match the Pas 8 direct-light shader. */
export const LUNAR_LAMBERT_LIGHT_INTENSITY = Math.PI;

export type MoonTextureLoad = (
  url: string,
  onLoad: (texture: THREE.Texture) => void,
  onError: (error: unknown) => void,
) => void;

export interface MoonSurfaceRenderMetrics {
  readonly geometryBuildCount: number;
  readonly materialBuildCount: number;
  readonly albedoTextureLoadCount: number;
  readonly normalTextureLoadCount: number;
  readonly textureUploadBytes: number;
  readonly bridgeTextureBytes: 0;
  readonly selectedResource: string;
  readonly surfaceStatus: "ready" | "loading" | "unavailable" | "invalid";
  readonly surfaceApplied: boolean;
}

/**
 * Owns the persistent Moon geometry, material, textures and fixed UV calibration.
 *
 * The untextured disc is deliberately a separate material. It is the Step 8
 * fallback and remains available when a browser rejects a large texture, a
 * lunar-orientation kernel is unavailable, or the textured material fails.
 */
export class MoonSurfaceRenderer {
  readonly root = new THREE.Group();
  readonly bodyRoot = new THREE.Group();
  readonly surfaceCalibration = new THREE.Group();
  /** Non-rendering centre used by the persistent Moon label. */
  readonly labelAnchor = new THREE.Object3D();
  /** Stable visual anchor for labels and for the non-data fallback. */
  readonly mesh: THREE.Mesh<THREE.SphereGeometry, THREE.MeshLambertMaterial>;

  private readonly geometry: THREE.SphereGeometry;
  private readonly fallbackMaterial: THREE.MeshLambertMaterial;
  private readonly surfaceMaterial: THREE.MeshLambertMaterial;
  private readonly surfaceMesh: THREE.Mesh<THREE.SphereGeometry, THREE.MeshLambertMaterial>;
  private readonly phaseLightDirection = { value: new THREE.Vector3(0, 0, 1) };
  private readonly daylightVeil = { value: 0 };
  private readonly daylightNeutral = { value: FALLBACK_COLOR.clone() };
  /** The only scene light allowed to affect the lunar surface. */
  private readonly sunLight: THREE.DirectionalLight;
  private readonly sunTarget: THREE.Object3D;
  private readonly loadTexture: MoonTextureLoad;
  private albedo: THREE.Texture | null = null;
  private normalMap: THREE.Texture | null = null;
  private loadRevision = 0;
  private surfaceEnabled = true;
  private hasPreciseOrientation = false;
  private bodyVisible = false;
  private disposed = false;
  private _albedoTextureLoadCount = 0;
  private _normalTextureLoadCount = 0;
  private _textureUploadBytes = 0;
  private _selectedResource = "surface unavailable";
  private _surfaceStatus: MoonSurfaceRenderMetrics["surfaceStatus"] = "unavailable";

  readonly geometryBuildCount = 1;
  readonly materialBuildCount = 2;

  constructor(parent: THREE.Object3D, loadTexture: MoonTextureLoad = browserTextureLoader()) {
    this.loadTexture = loadTexture;
    this.root.name = "moonRoot";
    this.bodyRoot.name = "moonBodyRoot";
    this.surfaceCalibration.name = "moonSurfaceCalibration";

    this.geometry = new THREE.SphereGeometry(1, 96, 64);
    this.fallbackMaterial = new THREE.MeshLambertMaterial({
      color: FALLBACK_COLOR,
      depthTest: true,
      depthWrite: false,
    });
    this.surfaceMaterial = new THREE.MeshLambertMaterial({
      color: 0xffffff,
      depthTest: true,
      depthWrite: false,
      normalScale: new THREE.Vector2(0.45, 0.45),
    });
    restoreLunarAtmosphericVisibility(
      this.fallbackMaterial,
      this.phaseLightDirection,
      this.daylightVeil,
      this.daylightNeutral,
    );
    restoreLunarAtmosphericVisibility(
      this.surfaceMaterial,
      this.phaseLightDirection,
      this.daylightVeil,
      this.daylightNeutral,
    );
    this.mesh = new THREE.Mesh(this.geometry, this.fallbackMaterial);
    this.mesh.name = "moonFallbackMesh";
    this.mesh.visible = false;
    this.mesh.frustumCulled = false;
    this.mesh.renderOrder = -101;
    this.surfaceMesh = new THREE.Mesh(this.geometry, this.surfaceMaterial);
    this.surfaceMesh.name = "moonSurfaceMesh";
    this.surfaceMesh.visible = false;
    this.surfaceMesh.frustumCulled = false;
    this.surfaceMesh.renderOrder = -100;
    this.sunLight = new THREE.DirectionalLight(
      0xffffff,
      LUNAR_LAMBERT_LIGHT_INTENSITY,
    );
    this.sunTarget = new THREE.Object3D();
    this.sunLight.target = this.sunTarget;

    // Fixed dataset/UV calibration only: mesh Y is lunar north (+Z body),
    // and increasing U maps to east-positive lunar longitude (+Y body).
    this.surfaceCalibration.quaternion.setFromAxisAngle(
      new THREE.Vector3(1, 0, 0),
      Math.PI / 2,
    );
    this.surfaceCalibration.add(this.mesh, this.surfaceMesh);
    this.bodyRoot.add(this.surfaceCalibration);
    this.root.add(this.bodyRoot, this.sunLight, this.sunTarget, this.labelAnchor);

    parent.add(this.root);
  }

  configureResource(resource: MoonSurfaceResourceDescriptor, maxTextureSize: number): void {
    if (this.disposed) return;
    const revision = ++this.loadRevision;
    this.releaseTextures();
    this._selectedResource = resource.label;
    if (resource.status !== "ready") {
      this._surfaceStatus = resource.status;
      this.refreshVisuals();
      return;
    }

    const selectedAlbedo = selectAlbedo(resource, maxTextureSize);
    if (selectedAlbedo === null) {
      this._selectedResource = "surface unavailable";
      this._surfaceStatus = "unavailable";
      this.refreshVisuals();
      return;
    }
    this._selectedResource = selectedAlbedo.role === "albedo_8k"
      ? "LRO 2025 8K"
      : "LRO 2025 4K fallback";
    this._surfaceStatus = "loading";
    this._albedoTextureLoadCount++;
    this.loadTexture(
      selectedAlbedo.url,
      (texture) => {
        if (this.disposed || revision !== this.loadRevision) {
          texture.dispose();
          return;
        }
        texture.colorSpace = THREE.SRGBColorSpace;
        texture.wrapS = THREE.RepeatWrapping;
        texture.wrapT = THREE.ClampToEdgeWrapping;
        texture.minFilter = THREE.LinearMipmapLinearFilter;
        texture.magFilter = THREE.LinearFilter;
        texture.generateMipmaps = true;
        this.albedo = texture;
        this.surfaceMaterial.map = texture;
        this.surfaceMaterial.needsUpdate = true;
        this._textureUploadBytes += estimatedRgbaMipBytes(selectedAlbedo);
        this._surfaceStatus = "ready";
        this.refreshVisuals();
      },
      () => {
        if (revision !== this.loadRevision) return;
        this._surfaceStatus = "unavailable";
        this._selectedResource = "surface unavailable";
        this.refreshVisuals();
      },
    );
    if (resource.normalMap !== null && maxTextureSize >= resource.normalMap.widthPx) {
      this._normalTextureLoadCount++;
      const normalAsset = resource.normalMap;
      this.loadTexture(
        normalAsset.url,
        (texture) => {
          if (this.disposed || revision !== this.loadRevision) {
            texture.dispose();
            return;
          }
          texture.colorSpace = THREE.NoColorSpace;
          texture.wrapS = THREE.RepeatWrapping;
          texture.wrapT = THREE.ClampToEdgeWrapping;
          texture.minFilter = THREE.LinearMipmapLinearFilter;
          texture.magFilter = THREE.LinearFilter;
          texture.generateMipmaps = true;
          this.normalMap = texture;
          this.surfaceMaterial.normalMap = texture;
          this.surfaceMaterial.needsUpdate = true;
          this._textureUploadBytes += estimatedRgbaMipBytes(normalAsset);
        },
        () => {
          if (revision !== this.loadRevision) return;
          this.surfaceMaterial.normalMap = null;
          this.surfaceMaterial.needsUpdate = true;
        },
      );
    }
  }

  updateState(
    moon: SolarSystemBodyState,
    lightDirectionThree: THREE.Vector3,
    visible: boolean,
  ): void {
    const orientation = moon.orientation;
    const bodyToEnu = orientation?.quality === "precise"
      ? orientation.bodyToENUQuaternion
      : null;
    this.hasPreciseOrientation = bodyToEnu !== null && bodyToEnu !== undefined;
    if (bodyToEnu !== null && bodyToEnu !== undefined) {
      this.bodyRoot.quaternion.copy(
        threeQuaternionFromBodyToEnu(bodyToEnu),
      );
    } else {
      this.bodyRoot.quaternion.identity();
    }
    // Three's directional light points from its target towards its position.
    // In the Moon-local frame that is precisely the Moon -> Sun vector.
    this.sunLight.position.copy(lightDirectionThree).normalize();
    this.phaseLightDirection.value.copy(lightDirectionThree).normalize();
    this.sunTarget.position.set(0, 0, 0);
    this.bodyVisible = visible;
    this.mesh.userData.apparentState = moon;
    this.surfaceMesh.userData.apparentState = moon;
    this.labelAnchor.userData.apparentState = moon;
    this.refreshVisuals();
  }

  setSurfaceEnabled(enabled: boolean): void {
    this.surfaceEnabled = enabled;
    this.refreshVisuals();
  }

  updateEnvironment(snapshot: SkyEnvironmentSnapshot): void {
    this.daylightVeil.value = lunarDaylightVeil(snapshot);
  }

  metrics(): MoonSurfaceRenderMetrics {
    return {
      geometryBuildCount: this.geometryBuildCount,
      materialBuildCount: this.materialBuildCount,
      albedoTextureLoadCount: this._albedoTextureLoadCount,
      normalTextureLoadCount: this._normalTextureLoadCount,
      textureUploadBytes: this._textureUploadBytes,
      bridgeTextureBytes: 0,
      selectedResource: this._selectedResource,
      surfaceStatus: this._surfaceStatus,
      surfaceApplied: this.isSurfaceApplied(),
    };
  }

  /** Returns the visual mesh that currently represents the Moon for hit tests. */
  getPickObject(): THREE.Mesh | undefined {
    if (this.surfaceMesh.visible) return this.surfaceMesh;
    if (this.mesh.visible) return this.mesh;
    return undefined;
  }

  dispose(): void {
    if (this.disposed) return;
    this.disposed = true;
    this.loadRevision++;
    this.root.removeFromParent();
    this.releaseTextures();
    this.geometry.dispose();
    this.fallbackMaterial.dispose();
    this.surfaceMaterial.dispose();
  }

  private isSurfaceApplied(): boolean {
    return this.surfaceEnabled
      && this.hasPreciseOrientation
      && this._surfaceStatus === "ready"
      && this.albedo !== null;
  }

  private refreshVisuals(): void {
    const surfaceApplied = this.isSurfaceApplied();
    // The fallback is exclusive: once a correctly oriented LRO albedo is
    // ready, the only visible Moon surface is that albedo. The neutral Step 8
    // disc is reserved for loading/failure/out-of-range states.
    this.labelAnchor.visible = this.bodyVisible;
    this.mesh.visible = this.bodyVisible && !surfaceApplied;
    this.surfaceMesh.visible = this.bodyVisible && surfaceApplied;
  }

  private releaseTextures(): void {
    this.albedo?.dispose();
    this.normalMap?.dispose();
    this.albedo = null;
    this.normalMap = null;
    this.surfaceMaterial.map = null;
    this.surfaceMaterial.normalMap = null;
    this.surfaceMaterial.needsUpdate = true;
    this._textureUploadBytes = 0;
  }
}

/**
 * Restores the Pas 8 visibility model verbatim: the physical atmosphere stays
 * behind the Moon and becomes predominant through phase-dependent alpha.
 * Surface colour and relief remain the responsibility of MeshLambertMaterial.
 */
function restoreLunarAtmosphericVisibility(
  material: THREE.MeshLambertMaterial,
  lightDirection: THREE.IUniform<THREE.Vector3>,
  daylightVeil: THREE.IUniform<number>,
  daylightNeutral: THREE.IUniform<THREE.Color>,
): void {
  material.transparent = true;
  material.depthWrite = false;
  material.onBeforeCompile = (shader) => {
    shader.uniforms.uMoonLightDirectionThree = lightDirection;
    shader.uniforms.uMoonDaylightVeil = daylightVeil;
    shader.uniforms.uMoonDaylightNeutral = daylightNeutral;
    shader.vertexShader = shader.vertexShader
      .replace(
        "#include <common>",
        "#include <common>\nvarying vec3 vMoonNormalWorld;",
      )
      .replace(
        "#include <normal_vertex>",
        [
          "#include <normal_vertex>",
          "vMoonNormalWorld = normalize(mat3(modelMatrix) * normal);",
        ].join("\n"),
      );
    shader.fragmentShader = shader.fragmentShader
      .replace(
        "#include <common>",
        [
          "#include <common>",
          "uniform vec3 uMoonLightDirectionThree;",
          "uniform float uMoonDaylightVeil;",
          "uniform vec3 uMoonDaylightNeutral;",
          "varying vec3 vMoonNormalWorld;",
        ].join("\n"),
      )
      .replace(
        "#include <map_fragment>",
        [
          "#include <map_fragment>",
          "diffuseColor.rgb = mix(diffuseColor.rgb, uMoonDaylightNeutral, uMoonDaylightVeil);",
        ].join("\n"),
      )
      .replace(
        "#include <opaque_fragment>",
        [
          "float moonDirectLight = max(dot(normalize(vMoonNormalWorld), normalize(uMoonLightDirectionThree)), 0.0);",
          `diffuseColor.a *= clamp(moonDirectLight + ${LUNAR_NIGHT_SIDE_VISIBILITY}, 0.0, 1.0);`,
          "#include <opaque_fragment>",
        ].join("\n"),
      );
  };
  material.customProgramCacheKey = () => "moon-pas8-atmospheric-daylight-v1";
}

export function lunarAtmosphericOpacity(directLight: number): number {
  return Math.max(0, Math.min(1, directLight + LUNAR_NIGHT_SIDE_VISIBILITY));
}

export function lunarDaylightVeil(
  environment: Pick<
    SkyEnvironmentSnapshot,
    "atmosphereEnabled" | "twilightFactor" | "horizonHaze"
  >,
): number {
  if (!environment.atmosphereEnabled) return 0;
  const daylight = Math.max(0, Math.min(1, 1 - environment.twilightFactor));
  const haze = Math.max(0, Math.min(1, environment.horizonHaze));
  return daylight * haze;
}

function selectAlbedo(
  resource: MoonSurfaceResourceDescriptor,
  maxTextureSize: number,
): MoonSurfaceAsset | null {
  if (resource.albedo8k !== null && maxTextureSize >= resource.albedo8k.widthPx) {
    return resource.albedo8k;
  }
  if (resource.albedo4k !== null && maxTextureSize >= resource.albedo4k.widthPx) {
    return resource.albedo4k;
  }
  return null;
}

function estimatedRgbaMipBytes(asset: MoonSurfaceAsset): number {
  return Math.round(asset.widthPx * asset.heightPx * 4 * MIP_FACTOR);
}

function browserTextureLoader(): MoonTextureLoad {
  const loader = new THREE.TextureLoader();
  return (url, onLoad, onError) => {
    loader.load(url, onLoad, undefined, onError);
  };
}

export function moonLightDirectionThree(
  moon: SolarSystemBodyState,
  fallback: THREE.Vector3,
): THREE.Vector3 {
  const direction = moon.orientation !== null
    && moon.orientation !== undefined
    && "moonToSunDirectionENU" in moon.orientation
    ? moon.orientation.moonToSunDirectionENU
    : null;
  return direction === null || direction === undefined
    ? fallback
    : threeFromEnu(direction).normalize();
}

/** Fraction of the apparent lunar disc that the same Sun vector illuminates. */
export function moonIlluminationFractionFromGeometry(
  moon: SolarSystemBodyState,
): number | null {
  const direction = moon.orientation !== null
    && moon.orientation !== undefined
    && "moonToSunDirectionENU" in moon.orientation
    ? moon.orientation.moonToSunDirectionENU
    : null;
  if (direction === null || direction === undefined) return null;
  const moonToObserver = threeFromEnu(moon.directionENU).normalize().negate();
  const moonToSun = threeFromEnu(direction).normalize();
  return (1 + moonToObserver.dot(moonToSun)) / 2;
}
