import * as THREE from "three";

import type {
  SatelliteCatalogManifest,
  SatelliteBodyId,
  SolarSystemBodyState,
} from "../../contracts/solar_system_contracts";
import { threeFromEnu } from "./celestialCoordinates";
import type { PickableSolarSystemBody } from "./SolarSystemRenderer";

const CELESTIAL_RADIUS = 900_000;

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
  readonly geometryBuildCount: 1;
  readonly materialBuildCount: 1;
  readonly bufferUpdateBytes: number;
  readonly lodMode: SatelliteLodMode;
}

/** One persistent GPU point batch plus stable interaction anchors. */
export class NaturalSatelliteRenderer {
  readonly root = new THREE.Group();
  readonly points: THREE.Points<THREE.BufferGeometry, THREE.ShaderMaterial>;
  private readonly geometry = new THREE.BufferGeometry();
  private readonly material: THREE.ShaderMaterial;
  private readonly anchors = new Map<SatelliteBodyId, THREE.Object3D>();
  private readonly states = new Map<SatelliteBodyId, SolarSystemBodyState>();
  private positions = new Float32Array(0);
  private colors = new Float32Array(0);
  private angularDiameters = new Float32Array(0);
  private catalogCount = 0;
  private stateCount = 0;
  private renderedCount = 0;
  private bufferUpdateBytes = 0;
  private lodMode: SatelliteLodMode = "auto";
  private enabled = false;
  private disposed = false;

  constructor(parent: THREE.Object3D) {
    this.root.name = "naturalSatellitesRoot";
    this.material = new THREE.ShaderMaterial({
      vertexShader: VERTEX_SHADER,
      fragmentShader: FRAGMENT_SHADER,
      uniforms: { 
        uPointSize: { value: -1.0 },
        uPixelsPerRad: { value: 1000.0 }
      },
      transparent: true,
      depthTest: true,
      depthWrite: false,
    });
    this.points = new THREE.Points(this.geometry, this.material);
    this.points.name = "naturalSatelliteLod0Batch";
    this.points.frustumCulled = false;
    this.points.renderOrder = -97;
    this.root.add(this.points);
    this.root.visible = false;
    parent.add(this.root);
  }

  configureCatalog(catalog: SatelliteCatalogManifest): void {
    if (this.disposed || catalog.status === "invalid" || catalog.status === "unavailable") return;
    if (catalog.counts.total === this.catalogCount && this.anchors.size > 0) return;
    for (const anchor of this.anchors.values()) anchor.removeFromParent();
    this.anchors.clear();
    this.catalogCount = catalog.counts.total;
    this.positions = new Float32Array(this.catalogCount * 3);
    this.colors = new Float32Array(this.catalogCount * 3);
    this.angularDiameters = new Float32Array(this.catalogCount);
    this.geometry.setAttribute("position", new THREE.BufferAttribute(this.positions, 3));
    this.geometry.setAttribute("color", new THREE.BufferAttribute(this.colors, 3));
    this.geometry.setAttribute("aAngularDiameterRad", new THREE.BufferAttribute(this.angularDiameters, 1));
    this.geometry.setDrawRange(0, 0);
    for (const definition of catalog.satellites) {
      if (definition.id === "naif-301") continue;
      const anchor = new THREE.Object3D();
      anchor.name = `satelliteAnchor:${definition.id}`;
      anchor.visible = false;
      this.anchors.set(definition.id, anchor);
      this.root.add(anchor);
    }
  }

  updateStates(states: readonly SolarSystemBodyState[]): void {
    if (this.disposed) return;
    for (const anchor of this.anchors.values()) anchor.visible = false;
    this.states.clear();
    let index = 0;
    for (const state of states) {
      if (!isSatelliteId(state.id)) continue;
      const anchor = this.anchors.get(state.id);
      if (anchor === undefined) continue;
      const position = threeFromEnu(state.directionENU).normalize().multiplyScalar(CELESTIAL_RADIUS);
      const visible = this.enabled && (state.horizonVisible ?? state.altitudeDeg >= 0);
      anchor.position.copy(position);
      anchor.visible = visible;
      anchor.userData.apparentState = state;
      this.states.set(state.id, state);
      if (!visible || index >= this.catalogCount) continue;
      position.toArray(this.positions, index * 3);
      const color = SYSTEM_COLORS[state.parentBodyId ?? ""] ?? new THREE.Color(0xd8d8d2);
      color.toArray(this.colors, index * 3);
      this.angularDiameters[index] = THREE.MathUtils.degToRad(state.angularDiameterDeg);
      index++;
    }
    this.stateCount = this.states.size;
    this.renderedCount = index;
    this.geometry.setDrawRange(0, index);
    const positionAttribute = this.geometry.getAttribute("position") as THREE.BufferAttribute | undefined;
    const colorAttribute = this.geometry.getAttribute("color") as THREE.BufferAttribute | undefined;
    const angularDiameterAttribute = this.geometry.getAttribute("aAngularDiameterRad") as THREE.BufferAttribute | undefined;
    if (positionAttribute !== undefined) positionAttribute.needsUpdate = true;
    if (colorAttribute !== undefined) colorAttribute.needsUpdate = true;
    if (angularDiameterAttribute !== undefined) angularDiameterAttribute.needsUpdate = true;
    this.bufferUpdateBytes += index * 3 * Float32Array.BYTES_PER_ELEMENT * 2 + index * Float32Array.BYTES_PER_ELEMENT;
    this.root.visible = this.enabled && index > 0;
  }

  setEnabled(enabled: boolean): void {
    this.enabled = enabled;
    this.root.visible = enabled && this.renderedCount > 0;
    if (!enabled) for (const anchor of this.anchors.values()) anchor.visible = false;
  }

  setLodMode(mode: SatelliteLodMode): void {
    this.lodMode = mode;
    const pointSize = (mode === "faithful" || mode === "auto") ? -1.0 : mode === "diagnostic" ? 5 : 2.25;
    this.material.uniforms["uPointSize"]!.value = pointSize;
  }

  updateCamera(fovDeg: number, heightPx: number): void {
    const fovRad = THREE.MathUtils.degToRad(fovDeg);
    const pixelsPerRad = heightPx / (2 * Math.tan(fovRad / 2));
    this.material.uniforms["uPixelsPerRad"]!.value = pixelsPerRad;
  }

  getPickableBodies(): readonly PickableSolarSystemBody[] {
    if (!this.enabled) return [];
    const result: PickableSolarSystemBody[] = [];
    for (const [id, state] of this.states) {
      const object = this.anchors.get(id);
      if (object?.visible) result.push({ id, state, object });
    }
    return result;
  }

  metrics(): NaturalSatelliteMetrics {
    return {
      catalogCount: this.catalogCount,
      stateCount: this.stateCount,
      renderedCount: this.renderedCount,
      entityBuildCount: this.anchors.size,
      geometryBuildCount: 1,
      materialBuildCount: 1,
      bufferUpdateBytes: this.bufferUpdateBytes,
      lodMode: this.lodMode,
    };
  }

  dispose(): void {
    if (this.disposed) return;
    this.disposed = true;
    this.root.removeFromParent();
    this.geometry.dispose();
    this.material.dispose();
    this.anchors.clear();
    this.states.clear();
  }
}

function isSatelliteId(id: string): id is SatelliteBodyId {
  return id.startsWith("naif-") || id.startsWith("provisional-");
}
