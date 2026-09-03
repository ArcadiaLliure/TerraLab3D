import * as THREE from "three";

import type {
  SatelliteCatalogManifest,
  SatelliteBodyId,
  SolarSystemBodyState,
  SolarSystemBodyId,
} from "../../contracts/solar_system_contracts";
import { threeFromEnu } from "./celestialCoordinates";
import type { PickableSolarSystemBody } from "./SolarSystemRenderer";
import type { CelestialOcclusionPolicy } from "./CelestialOcclusionPolicy";
import type { HorizonOcclusionState } from "./HorizonOcclusionState";
import { CELESTIAL_SCENE_RADIUS } from "./celestialScenePolicy";

const CELESTIAL_RADIUS = CELESTIAL_SCENE_RADIUS.solarSystem;

const VERTEX_SHADER = /* glsl */ `
  attribute vec3 color;
  attribute float aAngularDiameterRad;
  varying vec3 vColor;
  uniform float uPointSize;
  uniform float uPixelsPerRad;
  void main() {
    vColor = color;
    gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
    
    if (uPointSize < 0.0) {
      // Use apparent size
      float apparentSizePx = aAngularDiameterRad * uPixelsPerRad;
      if (apparentSizePx < 0.5) {
        gl_Position = vec4(2.0, 2.0, 2.0, 1.0); // Cull if sub-pixel
      } else {
        gl_PointSize = max(apparentSizePx, 1.0);
      }
    } else {
      gl_PointSize = uPointSize;
    }
  }
`;

const FRAGMENT_SHADER = /* glsl */ `
  varying vec3 vColor;
  void main() {
    vec2 centered = (gl_PointCoord - vec2(0.5)) * 2.0;
    float r2 = dot(centered, centered);
    if (r2 > 1.0) discard;
    
    float z = sqrt(1.0 - r2);
    vec3 normal = vec3(centered.x, -centered.y, z);
    vec3 lightDir = normalize(vec3(0.8, 0.6, 1.0));
    float diffuse = max(dot(normal, lightDir), 0.0);
    
    // Boost ambient for very small points so they don't disappear
    float ambient = 0.5;
    vec3 finalColor = vColor * (ambient + diffuse * (1.0 - ambient));
    gl_FragColor = vec4(finalColor, 1.0);
    #include <tonemapping_fragment>
    #include <colorspace_fragment>
  }
`;

const SYSTEM_COLORS: Readonly<Record<string, THREE.Color>> = {
  earth: new THREE.Color(0xd8d8d2),
  mars: new THREE.Color(0xff967a),
  jupiter: new THREE.Color(0xf1d1a4),
  saturn: new THREE.Color(0xe6cf95),
  uranus: new THREE.Color(0xa8e6ee),
  neptune: new THREE.Color(0x7da5ff),
  pluto: new THREE.Color(0xc7b5a4),
};

export type SatelliteLodMode = "auto" | "faithful" | "diagnostic";

export interface NaturalSatelliteMetrics {
  readonly catalogCount: number;
  readonly stateCount: number;
  readonly renderedCount: number;
  readonly entityBuildCount: number;
  readonly geometryBuildCount: number;
  readonly materialBuildCount: number;
  readonly bufferUpdateBytes: number;
  readonly lodMode: SatelliteLodMode;
}

/** One persistent GPU point batch plus stable interaction anchors. */
export class NaturalSatelliteRenderer {
  readonly root = new THREE.Group();
  private readonly sharedGeometry = new THREE.BufferGeometry();
  private readonly baseMaterial: THREE.ShaderMaterial;
  
  private readonly items = new Map<SatelliteBodyId, {
    anchor: THREE.Object3D;
    points: THREE.Points<THREE.BufferGeometry, THREE.ShaderMaterial>;
    uniforms: {
      uColor: THREE.IUniform<THREE.Color>;
      uAngularDiameterRad: THREE.IUniform<number>;
      uPointSize: THREE.IUniform<number>;
      uPixelsPerRad: THREE.IUniform<number>;
    };
  }>();

  private readonly sharedUniforms = {
    uPointSize: { value: -1.0 },
    uPixelsPerRad: { value: 1000.0 }
  };

  private catalogCount = 0;
  private stateCount = 0;
  private renderedCount = 0;
  private lodMode: SatelliteLodMode = "auto";
  private enabled = false;
  private disposed = false;

  constructor(
    parent: THREE.Object3D,
    private readonly horizonState: HorizonOcclusionState | null = null,
  ) {
    this.root.name = "naturalSatellitesRoot";
    this.sharedGeometry.setAttribute("position", new THREE.BufferAttribute(new Float32Array([0, 0, 0]), 3));
    
    // We override VERTEX_SHADER to use uniforms instead of attributes for color and diameter
    const vertexShader = `
      uniform vec3 uColor;
      uniform float uAngularDiameterRad;
      uniform float uPointSize;
      uniform float uPixelsPerRad;
      varying vec3 vColor;
      void main() {
        vColor = uColor;
        vec4 mvPosition = modelViewMatrix * vec4(position, 1.0);
        gl_Position = projectionMatrix * mvPosition;
        
        if (uPointSize < 0.0) {
          float apparentSizePx = uAngularDiameterRad * uPixelsPerRad;
          if (apparentSizePx < 0.5) {
            gl_Position = vec4(2.0, 2.0, 2.0, 1.0);
          } else {
            gl_PointSize = max(apparentSizePx, 1.0);
          }
        } else {
          gl_PointSize = uPointSize;
        }
      }
    `;

    this.baseMaterial = new THREE.ShaderMaterial({
      vertexShader: vertexShader,
      fragmentShader: FRAGMENT_SHADER,
      transparent: true,
      depthTest: true,
      depthWrite: false,
    });
    
    this.root.visible = false;
    parent.add(this.root);
  }

  configureCatalog(catalog: SatelliteCatalogManifest): void {
    if (this.disposed || catalog.status === "invalid" || catalog.status === "unavailable") return;
    if (catalog.counts.total === this.catalogCount && this.items.size > 0) return;
    
    for (const item of this.items.values()) {
      item.anchor.removeFromParent();
      item.points.material.dispose();
    }
    this.items.clear();
    
    this.catalogCount = catalog.counts.total;
    
    for (const definition of catalog.satellites) {
      if (definition.id === "naif-301") continue;
      
      const anchor = new THREE.Object3D();
      anchor.name = `satelliteAnchor:${definition.id}`;
      anchor.visible = false;
      
      const material = this.baseMaterial.clone();
      const uniforms = {
        uColor: { value: new THREE.Color(0xd8d8d2) },
        uAngularDiameterRad: { value: 0 },
        uPointSize: this.sharedUniforms.uPointSize,
        uPixelsPerRad: this.sharedUniforms.uPixelsPerRad
      };
      material.uniforms = uniforms;
      
      const points = new THREE.Points(this.sharedGeometry, material);
      points.frustumCulled = false;
      points.renderOrder = -97;
      
      anchor.add(points);
      this.items.set(definition.id, { anchor, points, uniforms });
      this.root.add(anchor);
    }
  }

  updateStates(
    states: readonly SolarSystemBodyState[],
    allStates: ReadonlyMap<SolarSystemBodyId, SolarSystemBodyState>,
    occlusion: Pick<CelestialOcclusionPolicy, "preparedPresentationRadius">,
  ): void {
    if (this.disposed) return;
    for (const item of this.items.values()) item.anchor.visible = false;
    
    let index = 0;
    for (const state of states) {
      if (!isSatelliteId(state.id)) continue;
      const item = this.items.get(state.id);
      if (item === undefined) continue;
      
      let radius = CELESTIAL_RADIUS;
      const parentState = state.parentBodyId ? allStates.get(state.parentBodyId as SolarSystemBodyId) : undefined;
      if (parentState) {
        const parentRadius = occlusion.preparedPresentationRadius(parentState);
        if (state.distanceKm > parentState.distanceKm) {
          radius = parentRadius + 50; // Darrere (ocultació)
        } else {
          radius = parentRadius - 50; // Davant (trànsit)
        }
      }

      const position = threeFromEnu(state.directionENU).normalize().multiplyScalar(radius);
      const visible = this.enabled && (
        this.horizonState === null
          ? (state.horizonVisible ?? state.altitudeDeg + state.angularRadiusDeg >= 0)
          : !this.horizonState.isDiscFullyOccluded(
            state.azimuthDeg,
            state.altitudeDeg,
            state.angularRadiusDeg,
          )
      );
      
      item.anchor.position.copy(position);
      item.anchor.visible = visible;
      item.anchor.userData.apparentState = state;
      
      if (visible) {
        const color = SYSTEM_COLORS[state.parentBodyId ?? ""] ?? new THREE.Color(0xd8d8d2);
        item.uniforms.uColor.value.copy(color);
        item.uniforms.uAngularDiameterRad.value = THREE.MathUtils.degToRad(state.angularDiameterDeg);
        index++;
      }
    }
    this.stateCount = states.length;
    this.renderedCount = index;
    this.root.visible = this.enabled && index > 0;
  }

  setEnabled(enabled: boolean): void {
    this.enabled = enabled;
    this.root.visible = enabled && this.renderedCount > 0;
    if (!enabled) for (const item of this.items.values()) item.anchor.visible = false;
  }

  setLodMode(mode: SatelliteLodMode): void {
    this.lodMode = mode;
    const pointSize = (mode === "faithful" || mode === "auto") ? -1.0 : mode === "diagnostic" ? 5 : 2.25;
    this.sharedUniforms.uPointSize.value = pointSize;
  }

  updateCamera(fovDeg: number, heightPx: number): void {
    const fovRad = THREE.MathUtils.degToRad(fovDeg);
    const pixelsPerRad = heightPx / (2 * Math.tan(fovRad / 2));
    this.sharedUniforms.uPixelsPerRad.value = pixelsPerRad;
  }

  getPickableBodies(): readonly PickableSolarSystemBody[] {
    if (!this.enabled) return [];
    const result: PickableSolarSystemBody[] = [];
    for (const [id, item] of this.items) {
      if (item.anchor.visible) {
        result.push({ id, state: item.anchor.userData.apparentState, object: item.anchor });
      }
    }
    return result;
  }

  getBodyObject(id: SolarSystemBodyId): THREE.Object3D | undefined {
    return this.items.get(id as SatelliteBodyId)?.anchor;
  }

  metrics(): NaturalSatelliteMetrics {
    return {
      catalogCount: this.catalogCount,
      stateCount: this.stateCount,
      renderedCount: this.renderedCount,
      entityBuildCount: this.items.size,
      geometryBuildCount: 1,
      materialBuildCount: 1 + this.items.size,
      bufferUpdateBytes: 0,
      lodMode: this.lodMode,
    };
  }

  dispose(): void {
    if (this.disposed) return;
    this.disposed = true;
    this.root.removeFromParent();
    this.sharedGeometry.dispose();
    this.baseMaterial.dispose();
    for (const item of this.items.values()) {
      item.points.material.dispose();
    }
    this.items.clear();
  }
}

function isSatelliteId(id: string): id is SatelliteBodyId {
  return id.startsWith("naif-") || id.startsWith("provisional-");
}
