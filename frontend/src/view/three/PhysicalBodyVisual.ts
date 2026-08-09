import * as THREE from "three";

import type {
  BodyOrientationState,
  PlanetTextureAsset,
  SolarSystemBodyState,
} from "../../contracts/solar_system_contracts";
import { threeFromEnu, threeQuaternionFromBodyToEnu } from "./celestialCoordinates";
import type { MoonTextureLoad } from "./MoonSurfaceRenderer";

const VERTEX_SHADER = /* glsl */ `
  varying vec2 vUv;
  varying vec3 vNormalWorld;
  void main() {
    vUv = uv;
    vNormalWorld = normalize(mat3(modelMatrix) * normal);
    gl_Position = projectionMatrix * viewMatrix * modelMatrix * vec4(position, 1.0);
  }
`;

const FRAGMENT_SHADER = /* glsl */ `
  uniform sampler2D uMap;
  uniform bool uHasMap;
  uniform vec3 uFallbackColor;
  uniform vec3 uLightDirectionThree;
  varying vec2 vUv;
  varying vec3 vNormalWorld;
  void main() {
    vec4 albedo = uHasMap ? texture2D(uMap, vUv) : vec4(uFallbackColor, 1.0);
    float directLight = max(dot(normalize(vNormalWorld), normalize(uLightDirectionThree)), 0.0);
    float light = max(directLight, 0.018);
    gl_FragColor = vec4(albedo.rgb * light, albedo.a);
    #include <tonemapping_fragment>
    #include <colorspace_fragment>
  }
`;

interface BodyUniforms extends Record<string, THREE.IUniform<unknown>> {
  readonly uMap: THREE.IUniform<THREE.Texture>;
  readonly uHasMap: THREE.IUniform<boolean>;
  readonly uFallbackColor: THREE.IUniform<THREE.Color>;
  readonly uLightDirectionThree: THREE.IUniform<THREE.Vector3>;
}

export interface PhysicalBodyVisualMetrics {
  readonly geometryBuildCount: 0;
  readonly materialBuildCount: 1;
  readonly textureLoadCount: number;
  readonly textureUploadBytes: number;
  readonly bridgeTextureBytes: 0;
  readonly textureReady: boolean;
}

/**
 * Persistent generic sphere/ellipsoid visual.
 *
 * Its parent positions and scales the apparent body. `bodyRoot` receives only
 * the scientific body-fixed quaternion, while `surfaceCalibration` contains
 * the immutable equirectangular dataset convention.
 */
export class PhysicalBodyVisual {
  readonly root = new THREE.Group();
  readonly bodyRoot = new THREE.Group();
  readonly surfaceCalibration = new THREE.Group();
  readonly mesh: THREE.Mesh<THREE.SphereGeometry, THREE.ShaderMaterial>;

  private readonly uniforms: BodyUniforms;
  private readonly material: THREE.ShaderMaterial;
  private readonly loadTexture: MoonTextureLoad;
  private readonly whiteTexture: THREE.DataTexture;
  private texture: THREE.Texture | null = null;
  private textureSha256: string | null = null;
  private loadRevision = 0;
  private disposed = false;
  private _textureLoadCount = 0;
  private _textureUploadBytes = 0;

  constructor(
    bodyId: string,
    geometry: THREE.SphereGeometry,
    fallbackColor: number,
    loadTexture: MoonTextureLoad,
  ) {
    this.root.name = `${bodyId}Root`;
    this.bodyRoot.name = `${bodyId}SurfaceSpinRoot`;
    this.surfaceCalibration.name = `${bodyId}SurfaceCalibration`;
    this.whiteTexture = new THREE.DataTexture(new Uint8Array([255, 255, 255, 255]), 1, 1);
    this.whiteTexture.needsUpdate = true;
    this.uniforms = {
      uMap: { value: this.whiteTexture },
      uHasMap: { value: false },
      uFallbackColor: { value: new THREE.Color(fallbackColor) },
      uLightDirectionThree: { value: new THREE.Vector3(0, 0, 1) },
    };
    this.material = new THREE.ShaderMaterial({
      vertexShader: VERTEX_SHADER,
      fragmentShader: FRAGMENT_SHADER,
      uniforms: this.uniforms,
      depthTest: true,
      depthWrite: true,
    });
    this.mesh = new THREE.Mesh(geometry, this.material);
    this.mesh.name = `${bodyId}Surface`;
    this.mesh.frustumCulled = false;
    this.mesh.renderOrder = -100;
    this.surfaceCalibration.quaternion.setFromAxisAngle(
      new THREE.Vector3(1, 0, 0),
      Math.PI / 2,
    );
    this.surfaceCalibration.add(this.mesh);
    this.bodyRoot.add(this.surfaceCalibration);
    this.root.add(this.bodyRoot);
    this.loadTexture = loadTexture;
  }

  configureTexture(asset: PlanetTextureAsset | null): void {
    if (this.disposed) return;
    if (asset === null) {
      this.releaseTexture();
      return;
    }
    if (asset.sha256 === this.textureSha256 && this.texture !== null) return;
    const revision = ++this.loadRevision;
    this.releaseTexture();
    this.textureSha256 = asset.sha256;
    this._textureLoadCount++;
    this.loadTexture(
      asset.url,
      (texture) => {
        if (this.disposed || revision !== this.loadRevision) {
          texture.dispose();
          return;
        }
        texture.colorSpace = asset.colorSpace === "sRGB"
          ? THREE.SRGBColorSpace
          : THREE.NoColorSpace;
        texture.wrapS = THREE.RepeatWrapping;
        texture.wrapT = THREE.ClampToEdgeWrapping;
        texture.flipY = asset.uvFlipY;
        texture.repeat.x = asset.uvFlipX ? -1 : 1;
        texture.offset.x = asset.uvFlipX ? 1 : 0;
        texture.center.set(0.5, 0.5);
        texture.rotation = THREE.MathUtils.degToRad(asset.uvRotationDeg);
        texture.minFilter = THREE.LinearMipmapLinearFilter;
        texture.magFilter = THREE.LinearFilter;
        texture.generateMipmaps = true;
        this.texture = texture;
        this.uniforms.uMap.value = texture;
        this.uniforms.uHasMap.value = true;
        this._textureUploadBytes = Math.round(asset.widthPx * asset.heightPx * 4 * 4 / 3);
      },
      () => {
        if (revision !== this.loadRevision) return;
        this.textureSha256 = null;
        this.uniforms.uHasMap.value = false;
      },
    );
  }

  updateState(
    state: SolarSystemBodyState,
    apparentRadius: number,
    lightDirectionThree: THREE.Vector3,
    visible: boolean,
  ): void {
    this.root.position.copy(threeFromEnu(state.directionENU).normalize()).multiplyScalar(900_000);
    this.root.scale.setScalar(apparentRadius);
    const orientation = bodyOrientation(state);
    if (orientation?.bodyToENUQuaternion !== null && orientation !== null) {
      this.bodyRoot.quaternion.copy(
        threeQuaternionFromBodyToEnu(orientation.bodyToENUQuaternion),
      );
    } else {
      this.bodyRoot.quaternion.identity();
    }
    const radii = state.radiiKm;
    const mean = state.meanRadiusKm;
    if (radii !== undefined && radii !== null && mean !== undefined && mean !== null && mean > 0) {
      // SphereGeometry's north axis is Y before the fixed body-axis calibration.
      this.mesh.scale.set(radii[0] / mean, radii[2] / mean, radii[1] / mean);
    } else {
      this.mesh.scale.set(1, 1, 1);
    }
    this.uniforms.uLightDirectionThree.value.copy(lightDirectionThree).normalize();
    this.root.visible = visible;
    this.mesh.visible = visible;
    this.mesh.userData.apparentState = state;
    this.root.userData.apparentState = state;
  }

  metrics(): PhysicalBodyVisualMetrics {
    return {
      geometryBuildCount: 0,
      materialBuildCount: 1,
      textureLoadCount: this._textureLoadCount,
      textureUploadBytes: this._textureUploadBytes,
      bridgeTextureBytes: 0,
      textureReady: this.texture !== null,
    };
  }

  dispose(): void {
    if (this.disposed) return;
    this.disposed = true;
    this.loadRevision++;
    this.root.removeFromParent();
    this.releaseTexture();
    this.material.dispose();
    this.whiteTexture.dispose();
  }

  private releaseTexture(): void {
    this.texture?.dispose();
    this.texture = null;
    this.textureSha256 = null;
    this.uniforms.uMap.value = this.whiteTexture;
    this.uniforms.uHasMap.value = false;
    this._textureUploadBytes = 0;
  }
}

function bodyOrientation(state: SolarSystemBodyState): BodyOrientationState | null {
  const orientation = state.orientation;
  return orientation !== null && "equatorialToENUQuaternion" in orientation
    ? orientation
    : null;
}
