import * as THREE from "three";

import type { SkyEnvironmentSnapshot } from "../../contracts/sky_environment_contracts";
import type {
  LunarEclipseState,
  SolarEclipseState,
  TerrainCorrectedLimbState,
} from "../../contracts/astronomical_event_contracts";
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
const MAX_TERRAIN_LIMB_SAMPLES = 1024;
/** Exact lunar night-side term restored from commit 439b9f6. */
export const LUNAR_NIGHT_SIDE_VISIBILITY = 0.015;
export const LUNAR_INDEPENDENT_LIGHTING_CACHE_KEY = "moon-pas8-atmospheric-independent-v4";

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
  private readonly eclipseShadowOffset = { value: new THREE.Vector2(10, 10) };
  private readonly eclipseShadowRadii = { value: new THREE.Vector2(0, 0) };
  private readonly eclipseMeanTransmission = { value: 1 };
  private readonly eclipseEnabled = { value: 0 };
  private readonly solarOccultationDirection = { value: new THREE.Vector3(0, 0, 1) };
  private readonly solarOccultationMoonDirection = { value: new THREE.Vector3(0, 0, 1) };
  private readonly solarOccultationAngularRadiusRad = { value: 0 };
  private readonly solarOccultationEnabled = { value: 0 };
  private readonly terrainLimbData = new Float32Array(MAX_TERRAIN_LIMB_SAMPLES).fill(1);
  private readonly terrainLimbTexture = {
    value: terrainLimbDataTexture(this.terrainLimbData),
  };
  private readonly terrainLimbSampleCount = { value: 1 };
  private readonly terrainLimbEnabled = { value: 0 };
  private readonly terrainLimbSunPositionAngleRad = { value: 0 };
  private readonly moonAngularRadiusRad = { value: 0 };
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
  private basePresentationScale = 1;
  private terrainEnvelopeScale = 1;
  private appliedTerrainLimb: TerrainCorrectedLimbState | null = null;

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
      this.eclipseShadowOffset,
      this.eclipseShadowRadii,
      this.eclipseMeanTransmission,
      this.eclipseEnabled,
      this.solarOccultationDirection,
      this.solarOccultationMoonDirection,
      this.solarOccultationAngularRadiusRad,
      this.solarOccultationEnabled,
      this.terrainLimbTexture,
      this.terrainLimbSampleCount,
      this.terrainLimbEnabled,
      this.terrainLimbSunPositionAngleRad,
      this.moonAngularRadiusRad,
    );
    restoreLunarAtmosphericVisibility(
      this.surfaceMaterial,
      this.phaseLightDirection,
      this.daylightVeil,
      this.daylightNeutral,
      this.eclipseShadowOffset,
      this.eclipseShadowRadii,
      this.eclipseMeanTransmission,
      this.eclipseEnabled,
      this.solarOccultationDirection,
      this.solarOccultationMoonDirection,
      this.solarOccultationAngularRadiusRad,
      this.solarOccultationEnabled,
      this.terrainLimbTexture,
      this.terrainLimbSampleCount,
      this.terrainLimbEnabled,
      this.terrainLimbSunPositionAngleRad,
      this.moonAngularRadiusRad,
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
    // Fixed dataset/UV calibration only: mesh Y is lunar north (+Z body),
    // and increasing U maps to east-positive lunar longitude (+Y body).
    this.surfaceCalibration.quaternion.setFromAxisAngle(
      new THREE.Vector3(1, 0, 0),
      Math.PI / 2,
    );
    this.surfaceCalibration.add(this.mesh, this.surfaceMesh);
    this.bodyRoot.add(this.surfaceCalibration);
    this.root.add(this.bodyRoot, this.labelAnchor);

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
    this.phaseLightDirection.value.copy(lightDirectionThree).normalize();
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

  updateEclipse(state: LunarEclipseState): void {
    const angle = THREE.MathUtils.degToRad(state.shadowOffsetPositionAngleDeg);
    this.eclipseShadowOffset.value.set(
      Math.sin(angle) * state.shadowOffsetMoonRadii,
      Math.cos(angle) * state.shadowOffsetMoonRadii,
    );
    this.eclipseShadowRadii.value.set(
      state.umbraRadiusMoonRadii,
      state.penumbraRadiusMoonRadii,
    );
    this.eclipseMeanTransmission.value = Math.max(0, Math.min(1, state.meanLunarLightTransmission));
    this.eclipseEnabled.value = state.classification === "none" ? 0 : 1;
  }

  /**
   * Makes only the lunar pixels projected over the solar disc opaque.
   * The rest of the night-side Moon keeps the established atmospheric fade.
   */
  updateSolarOccultation(
    state: SolarEclipseState,
    sunDirectionThree: THREE.Vector3,
    moonDirectionThree: THREE.Vector3,
    terrainLimb: TerrainCorrectedLimbState | null,
  ): void {
    this.solarOccultationDirection.value.copy(sunDirectionThree).normalize();
    this.solarOccultationMoonDirection.value.copy(moonDirectionThree).normalize();
    this.solarOccultationAngularRadiusRad.value = THREE.MathUtils.degToRad(
      state.sunAngularRadius,
    );
    this.moonAngularRadiusRad.value = THREE.MathUtils.degToRad(state.moonAngularRadius);
    this.terrainLimbSunPositionAngleRad.value = THREE.MathUtils.degToRad(
      (state.moonPositionAngleDeg + 180) % 360,
    );
    this.solarOccultationEnabled.value = state.locallyVisible
      && state.classification !== "none"
      ? 1
      : 0;
    this.updateTerrainLimb(
      this.solarOccultationEnabled.value > 0 ? terrainLimb : null,
    );
  }

  setPresentationScale(scale: number): void {
    this.basePresentationScale = scale;
    this.applyPresentationScale();
  }

  setRenderOrder(renderOrder: number): void {
    this.mesh.renderOrder = renderOrder;
    this.surfaceMesh.renderOrder = renderOrder;
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
    this.terrainLimbTexture.value.dispose();
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

  private updateTerrainLimb(limb: TerrainCorrectedLimbState | null): void {
    if (limb === this.appliedTerrainLimb) return;
    this.appliedTerrainLimb = limb;
    const source = limb?.radiusScaleSamples ?? [];
    const count = Math.min(source.length, MAX_TERRAIN_LIMB_SAMPLES);
    this.terrainLimbData.fill(1);
    for (let index = 0; index < count; index++) {
      this.terrainLimbData[index] = source[index] ?? 1;
    }
    this.terrainLimbSampleCount.value = Math.max(1, count);
    this.terrainLimbEnabled.value = count >= 3 ? 1 : 0;
    this.terrainEnvelopeScale = this.terrainLimbEnabled.value > 0
      ? Math.max(1, limb?.maximumRadiusScale ?? 1)
      : 1;
    this.terrainLimbTexture.value.needsUpdate = true;
    this.applyPresentationScale();
  }

  private applyPresentationScale(): void {
    this.root.scale.setScalar(this.basePresentationScale * this.terrainEnvelopeScale);
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
 * Surface colour and relief remain the responsibility of MeshLambertMaterial,
 * but its light accumulation is replaced completely. This preserves the normal
 * map while guaranteeing that scene-global Sun/Moon/sky lights cannot change
 * the lunar phase, terminator or atmospheric night-side transparency.
 */
function restoreLunarAtmosphericVisibility(
  material: THREE.MeshLambertMaterial,
  lightDirection: THREE.IUniform<THREE.Vector3>,
  daylightVeil: THREE.IUniform<number>,
  daylightNeutral: THREE.IUniform<THREE.Color>,
  eclipseShadowOffset: THREE.IUniform<THREE.Vector2>,
  eclipseShadowRadii: THREE.IUniform<THREE.Vector2>,
  eclipseMeanTransmission: THREE.IUniform<number>,
  eclipseEnabled: THREE.IUniform<number>,
  solarOccultationDirection: THREE.IUniform<THREE.Vector3>,
  solarOccultationMoonDirection: THREE.IUniform<THREE.Vector3>,
  solarOccultationAngularRadiusRad: THREE.IUniform<number>,
  solarOccultationEnabled: THREE.IUniform<number>,
  terrainLimbTexture: THREE.IUniform<THREE.DataTexture>,
  terrainLimbSampleCount: THREE.IUniform<number>,
  terrainLimbEnabled: THREE.IUniform<number>,
  terrainLimbSunPositionAngleRad: THREE.IUniform<number>,
  moonAngularRadiusRad: THREE.IUniform<number>,
): void {
  material.transparent = true;
  material.depthWrite = false;
  material.onBeforeCompile = (shader) => {
    shader.uniforms.uMoonLightDirectionThree = lightDirection;
    shader.uniforms.uMoonDaylightVeil = daylightVeil;
    shader.uniforms.uMoonDaylightNeutral = daylightNeutral;
    shader.uniforms.uMoonEclipseShadowOffset = eclipseShadowOffset;
    shader.uniforms.uMoonEclipseShadowRadii = eclipseShadowRadii;
    shader.uniforms.uMoonEclipseMeanTransmission = eclipseMeanTransmission;
    shader.uniforms.uMoonEclipseEnabled = eclipseEnabled;
    shader.uniforms.uMoonSolarOccultationDirectionThree = solarOccultationDirection;
    shader.uniforms.uMoonSolarOccultationMoonDirectionThree = solarOccultationMoonDirection;
    shader.uniforms.uMoonSolarOccultationAngularRadiusRad = solarOccultationAngularRadiusRad;
    shader.uniforms.uMoonSolarOccultationEnabled = solarOccultationEnabled;
    shader.uniforms.uMoonTerrainLimbTexture = terrainLimbTexture;
    shader.uniforms.uMoonTerrainLimbSampleCount = terrainLimbSampleCount;
    shader.uniforms.uMoonTerrainLimbEnabled = terrainLimbEnabled;
    shader.uniforms.uMoonTerrainLimbSunPositionAngleRad = terrainLimbSunPositionAngleRad;
    shader.uniforms.uMoonAngularRadiusRad = moonAngularRadiusRad;
    shader.vertexShader = shader.vertexShader
      .replace(
        "#include <common>",
        "#include <common>\nvarying vec3 vMoonNormalWorld;\nvarying vec3 vMoonWorldPosition;",
      )
      .replace(
        "#include <normal_vertex>",
        [
          "#include <normal_vertex>",
          "vMoonNormalWorld = normalize(mat3(modelMatrix) * normal);",
          "vMoonWorldPosition = (modelMatrix * vec4(position, 1.0)).xyz;",
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
          "uniform vec2 uMoonEclipseShadowOffset;",
          "uniform vec2 uMoonEclipseShadowRadii;",
          "uniform float uMoonEclipseMeanTransmission;",
          "uniform float uMoonEclipseEnabled;",
          "uniform vec3 uMoonSolarOccultationDirectionThree;",
          "uniform vec3 uMoonSolarOccultationMoonDirectionThree;",
          "uniform float uMoonSolarOccultationAngularRadiusRad;",
          "uniform float uMoonSolarOccultationEnabled;",
          "uniform sampler2D uMoonTerrainLimbTexture;",
          "uniform float uMoonTerrainLimbSampleCount;",
          "uniform float uMoonTerrainLimbEnabled;",
          "uniform float uMoonTerrainLimbSunPositionAngleRad;",
          "uniform float uMoonAngularRadiusRad;",
          `const float MOON_TERRAIN_LIMB_TEXTURE_WIDTH = ${MAX_TERRAIN_LIMB_SAMPLES}.0;`,
          "float sampleMoonTerrainLimb(float positionAngleRad) {",
          "  float normalizedAngle = mod(positionAngleRad + PI2, PI2) / PI2;",
          "  float samplePosition = normalizedAngle * uMoonTerrainLimbSampleCount;",
          "  float lowerIndex = mod(floor(samplePosition), uMoonTerrainLimbSampleCount);",
          "  float upperIndex = mod(lowerIndex + 1.0, uMoonTerrainLimbSampleCount);",
          "  float fraction = fract(samplePosition);",
          "  float lower = texture2D(uMoonTerrainLimbTexture, vec2((lowerIndex + 0.5) / MOON_TERRAIN_LIMB_TEXTURE_WIDTH, 0.5)).r;",
          "  float upper = texture2D(uMoonTerrainLimbTexture, vec2((upperIndex + 0.5) / MOON_TERRAIN_LIMB_TEXTURE_WIDTH, 0.5)).r;",
          "  return mix(lower, upper, fraction);",
          "}",
          "varying vec3 vMoonNormalWorld;",
          "varying vec3 vMoonWorldPosition;",
        ].join("\n"),
      )
      .replace(
        "#include <map_fragment>",
        [
          "#include <map_fragment>",
          "diffuseColor.rgb = mix(diffuseColor.rgb, uMoonDaylightNeutral, uMoonDaylightVeil);",
          "vec3 moonNormalView = normalize(mat3(viewMatrix) * vMoonNormalWorld);",
          "vec2 moonDiscCoordinate = moonNormalView.xy;",
          "float moonShadowDistance = length(moonDiscCoordinate - uMoonEclipseShadowOffset);",
          "float moonUmbra = (1.0 - smoothstep(uMoonEclipseShadowRadii.x - 0.035, uMoonEclipseShadowRadii.x + 0.035, moonShadowDistance)) * uMoonEclipseEnabled;",
          "float moonPenumbra = (1.0 - smoothstep(uMoonEclipseShadowRadii.y - 0.08, uMoonEclipseShadowRadii.y + 0.08, moonShadowDistance)) * uMoonEclipseEnabled;",
          "float moonPenumbralOnly = max(0.0, moonPenumbra - moonUmbra);",
          "diffuseColor.rgb *= mix(1.0, 0.62, moonPenumbralOnly);",
          "vec3 moonUmbraRed = diffuseColor.rgb * vec3(0.72, 0.16, 0.08) * max(0.045, uMoonEclipseMeanTransmission);",
          "diffuseColor.rgb = mix(diffuseColor.rgb, moonUmbraRed, moonUmbra);",
        ].join("\n"),
      )
      .replace(
        "#include <lights_lambert_fragment>",
        [
          "// Independent Moon -> Sun lighting: never consume scene lights.",
          "vec3 moonLightDirectionView = normalize(mat3(viewMatrix) * uMoonLightDirectionThree);",
          "float moonSurfaceDirect = max(dot(normal, moonLightDirectionView), 0.0);",
          "reflectedLight.directDiffuse = diffuseColor.rgb * moonSurfaceDirect;",
          "reflectedLight.indirectDiffuse = vec3(0.0);",
        ].join("\n"),
      )
      .replace("#include <lights_fragment_begin>", "")
      .replace("#include <lights_fragment_maps>", "")
      .replace("#include <lights_fragment_end>", "")
      .replace(
        "#include <opaque_fragment>",
        [
          "float moonDirectLight = max(dot(normalize(vMoonNormalWorld), normalize(uMoonLightDirectionThree)), 0.0);",
          `float moonAtmosphericOpacity = clamp(moonDirectLight + ${LUNAR_NIGHT_SIDE_VISIBILITY}, 0.0, 1.0);`,
          "vec3 moonFragmentDirection = normalize(vMoonWorldPosition - cameraPosition);",
          "vec3 solarOccultationDirection = normalize(uMoonSolarOccultationDirectionThree);",
          "vec3 moonOccultationDirection = normalize(uMoonSolarOccultationMoonDirectionThree);",
          "float moonFragmentToSun = atan(length(cross(moonFragmentDirection, solarOccultationDirection)), clamp(dot(moonFragmentDirection, solarOccultationDirection), -1.0, 1.0));",
          "float solarDiscEdgeWidth = max(fwidth(moonFragmentToSun), 1.0e-7);",
          "float smoothSolarDisc = 1.0 - smoothstep(uMoonSolarOccultationAngularRadiusRad - solarDiscEdgeWidth, uMoonSolarOccultationAngularRadiusRad + solarDiscEdgeWidth, moonFragmentToSun);",
          "float moonFragmentFromCenter = atan(length(cross(moonFragmentDirection, moonOccultationDirection)), clamp(dot(moonFragmentDirection, moonOccultationDirection), -1.0, 1.0));",
          "vec3 moonToSunTangentCandidate = solarOccultationDirection - moonOccultationDirection * dot(solarOccultationDirection, moonOccultationDirection);",
          "vec3 moonTangentReference = abs(moonOccultationDirection.y) < 0.9 ? vec3(0.0, 1.0, 0.0) : vec3(1.0, 0.0, 0.0);",
          "vec3 moonFallbackTangent = normalize(moonTangentReference - moonOccultationDirection * dot(moonTangentReference, moonOccultationDirection));",
          "vec3 moonToSunTangent = length(moonToSunTangentCandidate) > 1.0e-7 ? normalize(moonToSunTangentCandidate) : moonFallbackTangent;",
          "vec3 increasingPositionAngle = normalize(cross(moonToSunTangent, moonOccultationDirection));",
          "vec3 fragmentTangent = moonFragmentDirection - moonOccultationDirection * dot(moonFragmentDirection, moonOccultationDirection);",
          "float relativePositionAngle = atan(dot(fragmentTangent, increasingPositionAngle), dot(fragmentTangent, moonToSunTangent));",
          "float limbPositionAngle = relativePositionAngle + uMoonTerrainLimbSunPositionAngleRad;",
          "float terrainLimbRadiusScale = sampleMoonTerrainLimb(limbPositionAngle);",
          "float normalizedMoonRadius = moonFragmentFromCenter / max(uMoonAngularRadiusRad, 1.0e-7);",
          "float terrainEdgeWidth = max(fwidth(normalizedMoonRadius), 2.0e-5);",
          "float terrainDisc = mix(1.0, 1.0 - smoothstep(terrainLimbRadiusScale - terrainEdgeWidth, terrainLimbRadiusScale + terrainEdgeWidth, normalizedMoonRadius), uMoonTerrainLimbEnabled);",
          "float moonOverSolarDisc = smoothSolarDisc * uMoonSolarOccultationEnabled * terrainDisc;",
          "diffuseColor.a *= terrainDisc * mix(moonAtmosphericOpacity, 1.0, moonOverSolarDisc);",
          "#include <opaque_fragment>",
        ].join("\n"),
      );
  };
  material.customProgramCacheKey = () => LUNAR_INDEPENDENT_LIGHTING_CACHE_KEY;
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

function terrainLimbDataTexture(data: Float32Array): THREE.DataTexture {
  const texture = new THREE.DataTexture(
    data,
    MAX_TERRAIN_LIMB_SAMPLES,
    1,
    THREE.RedFormat,
    THREE.FloatType,
  );
  texture.name = "lroLolaTerrainCorrectedLimb";
  texture.wrapS = THREE.RepeatWrapping;
  texture.wrapT = THREE.ClampToEdgeWrapping;
  texture.minFilter = THREE.NearestFilter;
  texture.magFilter = THREE.NearestFilter;
  texture.generateMipmaps = false;
  texture.needsUpdate = true;
  return texture;
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
