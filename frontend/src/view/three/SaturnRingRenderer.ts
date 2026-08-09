import * as THREE from "three";

import type {
  BodyOrientationState,
  PlanetTextureAsset,
  SolarSystemBodyState,
} from "../../contracts/solar_system_contracts";
import { threeFromEnu, threeQuaternionFromBodyToEnu } from "./celestialCoordinates";
import type { MoonTextureLoad } from "./MoonSurfaceRenderer";

export const SATURN_RING_RADII_KM = {
  cInner: 74_658,
  cOuter: 91_975,
  bInner: 91_975,
  bOuter: 117_507,
  aInner: 122_340,
  aOuter: 136_780,
  fRing: 139_826,
} as const;

const SATURN_EQUATORIAL_RADIUS_KM = 60_268;
const SATURN_POLAR_RADIUS_KM = 54_364;

/**
 * True when Saturn's reference ellipsoid lies between the camera and a ring point.
 * The celestial renderer places the body at a fixed distant sphere, so its rays
 * are parallel at body scale. Working in unit-ellipsoid space avoids both the
 * depth-buffer loss and the catastrophic cancellation of a distant ray quadratic.
 */
export function ringPointOccludedByPlanet(
  cameraLocal: readonly [number, number, number],
  pointLocal: readonly [number, number, number],
  planetRadiiLocal: readonly [number, number, number],
): boolean {
  const camera = cameraLocal.map(
    (component, index) => component / planetRadiiLocal[index]!,
  );
  const cameraLength = Math.hypot(camera[0]!, camera[1]!, camera[2]!);
  if (cameraLength <= Number.EPSILON) return false;
  const view = camera.map((component) => component / cameraLength);
  const point = pointLocal.map(
    (component, index) => component / planetRadiiLocal[index]!,
  );
  const distanceAlongView = point.reduce(
    (sum, component, index) => sum + component * view[index]!,
    0,
  );
  if (distanceAlongView >= 0) return false;
  const projectedRadiusSquared = point.reduce(
    (sum, component, index) => {
      const projected = component - view[index]! * distanceAlongView;
      return sum + projected * projected;
    },
    0,
  );
  return projectedRadiusSquared < 1;
}

const VERTEX_SHADER = /* glsl */ `
  varying vec2 vUv;
  varying vec3 vNormalWorld;
  varying vec3 vRingLocalPosition;
  void main() {
    vUv = uv;
    vNormalWorld = normalize(mat3(modelMatrix) * normal);
    vRingLocalPosition = position;
    gl_Position = projectionMatrix * viewMatrix * modelMatrix * vec4(position, 1.0);
  }
`;

const FRAGMENT_SHADER = /* glsl */ `
  uniform sampler2D uMap;
  uniform bool uHasMap;
  uniform vec3 uLightDirectionThree;
  uniform vec3 uCameraDirectionPlanetLocal;
  uniform vec3 uPlanetInverseRadii;
  varying vec2 vUv;
  varying vec3 vNormalWorld;
  varying vec3 vRingLocalPosition;
  void main() {
    vec3 planetSpacePoint = vRingLocalPosition * uPlanetInverseRadii;
    float distanceAlongView = dot(planetSpacePoint, uCameraDirectionPlanetLocal);
    vec3 projectedPoint = planetSpacePoint
      - uCameraDirectionPlanetLocal * distanceAlongView;
    if (distanceAlongView < 0.0 && dot(projectedPoint, projectedPoint) < 1.0) discard;
    vec4 ring;
    if (uHasMap) {
      ring = texture2D(uMap, vec2(vUv.x, 0.5));
    } else {
      float cEnd = 0.2789;
      float bEnd = 0.6912;
      float aStart = 0.7691;
      if (vUv.x < cEnd) ring = vec4(0.58, 0.53, 0.47, 0.22);
      else if (vUv.x < bEnd) ring = vec4(0.82, 0.76, 0.66, 0.76);
      else if (vUv.x < aStart) ring = vec4(0.15, 0.14, 0.13, 0.035);
      else ring = vec4(0.70, 0.65, 0.57, 0.48);
    }
    float incidence = abs(dot(normalize(vNormalWorld), normalize(uLightDirectionThree)));
    float transmitted = 0.14 + 0.86 * incidence;
    gl_FragColor = vec4(ring.rgb * transmitted, ring.a);
    #include <tonemapping_fragment>
    #include <colorspace_fragment>
  }
`;

interface RingUniforms extends Record<string, THREE.IUniform<unknown>> {
  readonly uMap: THREE.IUniform<THREE.Texture>;
  readonly uHasMap: THREE.IUniform<boolean>;
  readonly uLightDirectionThree: THREE.IUniform<THREE.Vector3>;
  readonly uCameraDirectionPlanetLocal: THREE.IUniform<THREE.Vector3>;
  readonly uPlanetInverseRadii: THREE.IUniform<THREE.Vector3>;
}

export interface SaturnRingMetrics {
  readonly geometryBuildCount: 1;
  readonly materialBuildCount: 1;
  readonly textureLoadCount: number;
  readonly textureUploadBytes: number;
  readonly bridgeTextureBytes: 0;
  readonly pendingPlanetShadow: true;
  readonly pendingRingShadowOnPlanet: true;
}

/** Persistent physical ring plane; diagnostic B never enters its transform. */
export class SaturnRingRenderer {
  readonly root = new THREE.Group();
  readonly mesh: THREE.Mesh<THREE.BufferGeometry, THREE.ShaderMaterial>;
  private readonly geometry: THREE.BufferGeometry;
  private readonly material: THREE.ShaderMaterial;
  private readonly uniforms: RingUniforms;
  private readonly whiteTexture: THREE.DataTexture;
  private texture: THREE.Texture | null = null;
  private textureSha256: string | null = null;
  private loadRevision = 0;
  private disposed = false;
  private enabled = true;
  private _textureLoadCount = 0;
  private _textureUploadBytes = 0;

  constructor(parent: THREE.Object3D, private readonly loadTexture: MoonTextureLoad) {
    this.root.name = "saturnEquatorialOrientationRoot";
    this.geometry = createRingGeometry(
      SATURN_RING_RADII_KM.cInner / SATURN_EQUATORIAL_RADIUS_KM,
      SATURN_RING_RADII_KM.aOuter / SATURN_EQUATORIAL_RADIUS_KM,
      384,
    );
    this.whiteTexture = new THREE.DataTexture(new Uint8Array([255, 255, 255, 255]), 1, 1);
    this.whiteTexture.needsUpdate = true;
    this.uniforms = {
      uMap: { value: this.whiteTexture },
      uHasMap: { value: false },
      uLightDirectionThree: { value: new THREE.Vector3(0, 1, 0) },
      uCameraDirectionPlanetLocal: { value: new THREE.Vector3() },
      uPlanetInverseRadii: {
        value: inverseRadii([
          1,
          1,
          SATURN_POLAR_RADIUS_KM / SATURN_EQUATORIAL_RADIUS_KM,
        ]),
      },
    };
    this.material = new THREE.ShaderMaterial({
      vertexShader: VERTEX_SHADER,
      fragmentShader: FRAGMENT_SHADER,
      uniforms: this.uniforms,
      side: THREE.DoubleSide,
      transparent: true,
      // Planet/ring occlusion is analytic below. At the celestial-sphere
      // distance the shared depth buffer cannot distinguish their surfaces
      // and produces triangle-shaped holes in the foreground semiring.
      depthTest: false,
      depthWrite: false,
    });
    this.mesh = new THREE.Mesh(this.geometry, this.material);
    this.mesh.name = "saturnRingSystem";
    this.mesh.frustumCulled = false;
    this.mesh.renderOrder = -99;
    this.mesh.onBeforeRender = (_renderer, _scene, camera) => {
      const cameraDirection = this.uniforms.uCameraDirectionPlanetLocal.value;
      camera.getWorldPosition(cameraDirection);
      this.mesh.worldToLocal(cameraDirection);
      cameraDirection.multiply(this.uniforms.uPlanetInverseRadii.value).normalize();
    };
    this.root.add(this.mesh);
    parent.add(this.root);
  }

  configureTexture(asset: PlanetTextureAsset | null): void {
    if (asset === null || this.disposed) return;
    if (asset.sha256 === this.textureSha256 && this.texture !== null) return;
    const revision = ++this.loadRevision;
    this.releaseTexture();
    this.textureSha256 = asset.sha256;
    this._textureLoadCount++;
    this.loadTexture(asset.url, (texture) => {
      if (this.disposed || revision !== this.loadRevision) {
        texture.dispose();
        return;
      }
      texture.colorSpace = THREE.SRGBColorSpace;
      texture.wrapS = THREE.ClampToEdgeWrapping;
      texture.wrapT = THREE.ClampToEdgeWrapping;
      texture.minFilter = THREE.LinearMipmapLinearFilter;
      texture.magFilter = THREE.LinearFilter;
      texture.generateMipmaps = true;
      this.texture = texture;
      this.uniforms.uMap.value = texture;
      this.uniforms.uHasMap.value = true;
      this._textureUploadBytes = Math.round(asset.widthPx * asset.heightPx * 4 * 4 / 3);
    }, () => {
      if (revision === this.loadRevision) this.uniforms.uHasMap.value = false;
    });
  }

  updateState(state: SolarSystemBodyState, visible: boolean): void {
    const orientation = bodyOrientation(state);
    const equatorial = orientation?.equatorialToENUQuaternion;
    if (equatorial !== null && equatorial !== undefined) {
      this.root.quaternion.copy(threeQuaternionFromBodyToEnu(equatorial));
    } else {
      this.root.quaternion.identity();
    }
    const meanRadius = state.meanRadiusKm;
    this.root.scale.setScalar(
      meanRadius !== undefined && meanRadius !== null && meanRadius > 0
        ? SATURN_EQUATORIAL_RADIUS_KM / meanRadius
        : 1,
    );
    const radii = state.radiiKm;
    if (radii !== undefined && radii !== null && radii.every((radius) => radius > 0)) {
      this.uniforms.uPlanetInverseRadii.value.copy(inverseRadii([
        radii[0] / SATURN_EQUATORIAL_RADIUS_KM,
        radii[1] / SATURN_EQUATORIAL_RADIUS_KM,
        radii[2] / SATURN_EQUATORIAL_RADIUS_KM,
      ]));
    }
    const sun = state.bodyToSunDirectionENU;
    if (sun !== undefined && sun !== null) {
      this.uniforms.uLightDirectionThree.value.copy(threeFromEnu(sun)).normalize();
    }
    this.root.visible = this.enabled && visible && equatorial !== null && equatorial !== undefined;
    this.mesh.userData.apparentState = state;
  }

  setEnabled(enabled: boolean): void {
    this.enabled = enabled;
    if (!enabled) this.root.visible = false;
  }

  metrics(): SaturnRingMetrics {
    return {
      geometryBuildCount: 1,
      materialBuildCount: 1,
      textureLoadCount: this._textureLoadCount,
      textureUploadBytes: this._textureUploadBytes,
      bridgeTextureBytes: 0,
      pendingPlanetShadow: true,
      pendingRingShadowOnPlanet: true,
    };
  }

  dispose(): void {
    if (this.disposed) return;
    this.disposed = true;
    this.loadRevision++;
    this.mesh.onBeforeRender = () => undefined;
    this.root.removeFromParent();
    this.releaseTexture();
    this.geometry.dispose();
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

function inverseRadii(
  radii: readonly [number, number, number],
): THREE.Vector3 {
  return new THREE.Vector3(
    1 / radii[0],
    1 / radii[1],
    1 / radii[2],
  );
}

function bodyOrientation(state: SolarSystemBodyState): BodyOrientationState | null {
  const orientation = state.orientation;
  return orientation !== null && "equatorialToENUQuaternion" in orientation
    ? orientation
    : null;
}

function createRingGeometry(inner: number, outer: number, segments: number): THREE.BufferGeometry {
  const positions = new Float32Array((segments + 1) * 2 * 3);
  const normals = new Float32Array((segments + 1) * 2 * 3);
  const uvs = new Float32Array((segments + 1) * 2 * 2);
  const indices: number[] = [];
  for (let index = 0; index <= segments; index++) {
    const angle = index / segments * Math.PI * 2;
    const cosine = Math.cos(angle);
    const sine = Math.sin(angle);
    for (let edge = 0; edge < 2; edge++) {
      const vertex = index * 2 + edge;
      const radius = edge === 0 ? inner : outer;
      positions.set([cosine * radius, sine * radius, 0], vertex * 3);
      normals.set([0, 0, 1], vertex * 3);
      uvs.set([edge, index / segments], vertex * 2);
    }
    if (index < segments) {
      const base = index * 2;
      indices.push(base, base + 1, base + 2, base + 1, base + 3, base + 2);
    }
  }
  const geometry = new THREE.BufferGeometry();
  geometry.setAttribute("position", new THREE.BufferAttribute(positions, 3));
  geometry.setAttribute("normal", new THREE.BufferAttribute(normals, 3));
  geometry.setAttribute("uv", new THREE.BufferAttribute(uvs, 2));
  geometry.setIndex(indices);
  geometry.computeBoundingSphere();
  return geometry;
}
