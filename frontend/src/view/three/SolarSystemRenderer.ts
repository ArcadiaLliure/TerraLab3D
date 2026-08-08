import * as THREE from "three";

import type { SkyEnvironmentSnapshot } from "../../contracts/sky_environment_contracts";
import type {
  SolarSystemBodyId,
  SolarSystemBodyState,
  SolarSystemSnapshot,
} from "../../contracts/solar_system_contracts";
import { threeFromEnu } from "./celestialCoordinates";

const CELESTIAL_RADIUS = 900_000;
const INTERPOLATION_MS = 1000;
const LARGE_TIME_JUMP_SECONDS = 120;

export type PlanetBodyId = Exclude<SolarSystemBodyId, "sun" | "moon">;

export const PLANET_IDS: readonly PlanetBodyId[] = [
  "mercury", "venus", "mars", "jupiter", "saturn", "uranus", "neptune",
];

/** Shared visual identity for each planet disc and its projected tag. */
export const PLANET_PRESENTATIONS = {
  mercury: { label: "Mercury", color: 0xdcc8af, cssColor: "#dcc8af" },
  venus: { label: "Venus", color: 0xfff5d2, cssColor: "#fff5d2" },
  mars: { label: "Mars", color: 0xff7350, cssColor: "#ff7350" },
  jupiter: { label: "Jupiter", color: 0xf5d7af, cssColor: "#f5d7af" },
  saturn: { label: "Saturn", color: 0xebcd87, cssColor: "#ebcd87" },
  uranus: { label: "Uranus", color: 0xa5e1eb, cssColor: "#a5e1eb" },
  neptune: { label: "Neptune", color: 0x6e9bff, cssColor: "#6e9bff" },
} satisfies Record<PlanetBodyId, {
  readonly label: string;
  readonly color: number;
  readonly cssColor: string;
}>;

const BODY_IDS: readonly SolarSystemBodyId[] = ["sun", "moon", ...PLANET_IDS];

const BODY_COLORS: Readonly<Record<SolarSystemBodyId, number>> = {
  sun: 0xfff4c2,
  moon: 0xd8d8d2,
  mercury: PLANET_PRESENTATIONS.mercury.color,
  venus: PLANET_PRESENTATIONS.venus.color,
  mars: PLANET_PRESENTATIONS.mars.color,
  jupiter: PLANET_PRESENTATIONS.jupiter.color,
  saturn: PLANET_PRESENTATIONS.saturn.color,
  uranus: PLANET_PRESENTATIONS.uranus.color,
  neptune: PLANET_PRESENTATIONS.neptune.color,
};

const VERTEX_SHADER = /* glsl */ `
  varying vec3 vNormalWorld;
  varying float vCelestialY;
  void main() {
    vec4 worldPosition = modelMatrix * vec4(position, 1.0);
    vNormalWorld = normalize(mat3(modelMatrix) * normal);
    vCelestialY = worldPosition.y - cameraPosition.y;
    gl_Position = projectionMatrix * viewMatrix * worldPosition;
  }
`;

const FRAGMENT_SHADER = /* glsl */ `
  uniform vec3 uColor;
  uniform vec3 uLightDirectionThree;
  uniform float uNightSide;
  uniform float uRenderAlpha;
  uniform bool uEmissive;
  varying vec3 vNormalWorld;
  varying float vCelestialY;
  void main() {
    if (vCelestialY < 0.0) discard;
    float directLight = max(dot(normalize(vNormalWorld), normalize(uLightDirectionThree)), 0.0);
    float lightFactor = uEmissive ? 1.0 : max(directLight, uNightSide);
    float alpha = uEmissive ? uRenderAlpha : uRenderAlpha * clamp(directLight + uNightSide, 0.0, 1.0);
    gl_FragColor = vec4(uColor * lightFactor, alpha);
  }
`;

interface BodyUniforms extends Record<string, THREE.IUniform<unknown>> {
  readonly uColor: THREE.IUniform<THREE.Color>;
  readonly uLightDirectionThree: THREE.IUniform<THREE.Vector3>;
  readonly uNightSide: THREE.IUniform<number>;
  readonly uRenderAlpha: THREE.IUniform<number>;
  readonly uEmissive: THREE.IUniform<boolean>;
}

interface BodyEntity {
  readonly mesh: THREE.Mesh<THREE.SphereGeometry, THREE.ShaderMaterial>;
  readonly uniforms: BodyUniforms;
}

interface Interpolation {
  readonly startedMs: number;
  readonly from: ReadonlyMap<SolarSystemBodyId, SolarSystemBodyState>;
  readonly to: ReadonlyMap<SolarSystemBodyId, SolarSystemBodyState>;
}

export interface SolarSystemRenderMetrics {
  readonly entityBuildCount: number;
  readonly geometryBuildCount: number;
  readonly materialBuildCount: number;
  readonly snapshotApplyCount: number;
  readonly staleSnapshotCount: number;
  readonly lastBridgeBytes: number;
}

export class SolarSystemRenderer {
  readonly root = new THREE.Group();
  private readonly planetsRoot = new THREE.Group();
  private readonly geometry: THREE.SphereGeometry;
  private readonly entities = new Map<SolarSystemBodyId, BodyEntity>();
  private displayed = new Map<SolarSystemBodyId, SolarSystemBodyState>();
  private target = new Map<SolarSystemBodyId, SolarSystemBodyState>();
  private interpolation: Interpolation | null = null;
  private environment: SkyEnvironmentSnapshot | null = null;
  private latestGeneration = 0;
  private latestObserverGeneration = 0;
  private latestTimestampMs = 0;
  private masterVisible = true;
  private sunVisible = true;
  private moonVisible = true;
  private planetsVisible = true;
  private disposed = false;
  private _snapshotApplyCount = 0;
  private _staleSnapshotCount = 0;
  private _lastBridgeBytes = 0;

  readonly entityBuildCount: number;
  readonly geometryBuildCount = 1;
  readonly materialBuildCount: number;

  constructor(parent: THREE.Object3D) {
    this.root.name = "solarSystemRoot";
    this.planetsRoot.name = "planets";
    this.geometry = new THREE.SphereGeometry(1, 32, 20);
    for (const id of BODY_IDS) {
      const entity = this.createEntity(id);
      (id === "sun" || id === "moon" ? this.root : this.planetsRoot).add(entity.mesh);
      this.entities.set(id, entity);
    }
    this.root.add(this.planetsRoot);
    parent.add(this.root);
    this.entityBuildCount = this.entities.size;
    this.materialBuildCount = this.entities.size;
  }

  updateSnapshot(snapshot: SolarSystemSnapshot, bridgeBytes = 0, nowMs = performance.now()): boolean {
    if (snapshot.generation <= this.latestGeneration) {
      this._staleSnapshotCount++;
      return false;
    }
    const next = statesById(snapshot);
    const timestampMs = Date.parse(snapshot.timestampUtc);
    const snap = (
      this.displayed.size === 0
      || snapshot.observerGeneration !== this.latestObserverGeneration
      || Math.abs(timestampMs - this.latestTimestampMs) > LARGE_TIME_JUMP_SECONDS * 1000
    );
    this.latestGeneration = snapshot.generation;
    this.latestObserverGeneration = snapshot.observerGeneration;
    this.latestTimestampMs = timestampMs;
    this._lastBridgeBytes = bridgeBytes;
    this._snapshotApplyCount++;
    this.target = next;
    this.hideUnavailable(next);
    if (snap) {
      this.displayed = new Map(next);
      this.interpolation = null;
      this.applyDisplayed();
    } else {
      this.interpolation = { startedMs: nowMs, from: new Map(this.displayed), to: next };
    }
    return true;
  }

  update(timestampMs: number): void {
    if (this.disposed || this.interpolation === null) return;
    const fraction = clamp01((timestampMs - this.interpolation.startedMs) / INTERPOLATION_MS);
    const nextDisplayed = new Map<SolarSystemBodyId, SolarSystemBodyState>();
    for (const [id, target] of this.interpolation.to) {
      const start = this.interpolation.from.get(id) ?? target;
      nextDisplayed.set(id, interpolateBody(start, target, fraction));
    }
    this.displayed = nextDisplayed;
    this.applyDisplayed();
    if (fraction >= 1.0) this.interpolation = null;
  }

  updateEnvironment(snapshot: SkyEnvironmentSnapshot): void {
    this.environment = snapshot;
    this.applyDisplayed();
  }

  setVisibility(part: "system" | "sun" | "moon" | "planets", visible: boolean): void {
    if (part === "system") this.masterVisible = visible;
    if (part === "sun") this.sunVisible = visible;
    if (part === "moon") this.moonVisible = visible;
    if (part === "planets") this.planetsVisible = visible;
    this.applyDisplayed();
  }

  getBodyObject(id: SolarSystemBodyId): THREE.Mesh | undefined {
    return this.entities.get(id)?.mesh;
  }

  isPlanetLabelVisible(id: PlanetBodyId): boolean {
    const entity = this.entities.get(id);
    return entity !== undefined
      && entity.mesh.visible
      && entity.uniforms.uRenderAlpha.value > 0.01;
  }

  metrics(): SolarSystemRenderMetrics {
    return {
      entityBuildCount: this.entityBuildCount,
      geometryBuildCount: this.geometryBuildCount,
      materialBuildCount: this.materialBuildCount,
      snapshotApplyCount: this._snapshotApplyCount,
      staleSnapshotCount: this._staleSnapshotCount,
      lastBridgeBytes: this._lastBridgeBytes,
    };
  }

  dispose(): void {
    if (this.disposed) return;
    this.disposed = true;
    this.root.removeFromParent();
    this.geometry.dispose();
    for (const entity of this.entities.values()) entity.mesh.material.dispose();
    this.entities.clear();
  }

  private createEntity(id: SolarSystemBodyId): BodyEntity {
    const uniforms: BodyUniforms = {
      uColor: { value: new THREE.Color(BODY_COLORS[id]) },
      uLightDirectionThree: { value: new THREE.Vector3(0, 0, 1) },
      uNightSide: { value: id === "moon" ? 0.015 : 0.06 },
      uRenderAlpha: { value: 1 },
      uEmissive: { value: id === "sun" },
    };
    const material = new THREE.ShaderMaterial({
      vertexShader: VERTEX_SHADER,
      fragmentShader: FRAGMENT_SHADER,
      uniforms,
      transparent: true,
      depthTest: true,
      depthWrite: false,
    });
    const mesh = new THREE.Mesh(this.geometry, material);
    mesh.name = id;
    mesh.visible = false;
    mesh.frustumCulled = false;
    mesh.renderOrder = -100;
    return { mesh, uniforms };
  }

  private hideUnavailable(available: ReadonlyMap<SolarSystemBodyId, SolarSystemBodyState>): void {
    for (const [id, entity] of this.entities) {
      if (!available.has(id)) entity.mesh.visible = false;
    }
  }

  private applyDisplayed(): void {
    const sun = this.displayed.get("sun");
    if (sun === undefined) return;
    for (const [id, state] of this.displayed) {
      const entity = this.entities.get(id);
      if (entity === undefined) continue;
      const direction = threeFromEnu(state.directionENU).normalize();
      entity.mesh.position.copy(direction).multiplyScalar(CELESTIAL_RADIUS);
      entity.mesh.scale.setScalar(
        CELESTIAL_RADIUS * Math.sin(THREE.MathUtils.degToRad(state.angularRadiusDeg)),
      );
      entity.uniforms.uRenderAlpha.value = renderAlpha(state, this.environment);
      entity.uniforms.uLightDirectionThree.value.copy(
        phaseLightDirectionThree(state, sun),
      );
      entity.mesh.visible = this.isVisible(id) && state.altitudeDeg + state.angularRadiusDeg > 0;
      entity.mesh.userData.apparentState = state;
    }
  }

  private isVisible(id: SolarSystemBodyId): boolean {
    if (!this.masterVisible) return false;
    if (id === "sun") return this.sunVisible;
    if (id === "moon") return this.moonVisible;
    return this.planetsVisible;
  }
}

export function phaseLightDirectionThree(
  body: SolarSystemBodyState,
  sun: SolarSystemBodyState,
): THREE.Vector3 {
  const sunDirection = threeFromEnu(sun.directionENU).normalize();
  if (body.id === "sun") return sunDirection.negate();
  const viewDirection = threeFromEnu(body.directionENU).normalize();
  const observerFromBody = viewDirection.clone().negate();
  const projectedSun = sunDirection.clone()
    .addScaledVector(viewDirection, -sunDirection.dot(viewDirection));
  if (projectedSun.lengthSq() < 1e-12) projectedSun.set(1, 0, 0);
  projectedSun.normalize();
  const phase = THREE.MathUtils.degToRad(body.phaseAngleDeg);
  return observerFromBody.multiplyScalar(Math.cos(phase))
    .addScaledVector(projectedSun, Math.sin(phase))
    .normalize();
}

function statesById(snapshot: SolarSystemSnapshot): Map<SolarSystemBodyId, SolarSystemBodyState> {
  const states = new Map<SolarSystemBodyId, SolarSystemBodyState>();
  states.set("sun", snapshot.sun);
  if (snapshot.moon !== null) states.set("moon", snapshot.moon);
  for (const planet of snapshot.planets) states.set(planet.id, planet);
  return states;
}

function interpolateBody(
  start: SolarSystemBodyState,
  target: SolarSystemBodyState,
  fraction: number,
): SolarSystemBodyState {
  const direction = threeFromEnu(start.directionENU)
    .lerp(threeFromEnu(target.directionENU), fraction)
    .normalize();
  const directionENU: readonly [number, number, number] = [direction.x, direction.y, -direction.z];
  const lerp = (a: number, b: number): number => THREE.MathUtils.lerp(a, b, fraction);
  return {
    ...target,
    altitudeDeg: lerp(start.altitudeDeg, target.altitudeDeg),
    azimuthDeg: interpolateAngle(start.azimuthDeg, target.azimuthDeg, fraction),
    directionENU,
    distanceKm: lerp(start.distanceKm, target.distanceKm),
    angularRadiusDeg: lerp(start.angularRadiusDeg, target.angularRadiusDeg),
    angularDiameterDeg: lerp(start.angularDiameterDeg, target.angularDiameterDeg),
    illuminationFraction: lerp(start.illuminationFraction, target.illuminationFraction),
    phaseAngleDeg: lerp(start.phaseAngleDeg, target.phaseAngleDeg),
    apparentMagnitude: lerp(start.apparentMagnitude, target.apparentMagnitude),
  };
}

function interpolateAngle(start: number, target: number, fraction: number): number {
  const delta = ((target - start + 540) % 360) - 180;
  return (start + delta * fraction + 360) % 360;
}

function renderAlpha(body: SolarSystemBodyState, environment: SkyEnvironmentSnapshot | null): number {
  if (body.id === "sun" || body.id === "moon") return 1;
  const night = environment?.twilightFactor ?? 1;
  const limit = environment?.visibility.zenithMagnitudeLimit ?? 6;
  const magnitudeVisibility = clamp01((limit - body.apparentMagnitude + 0.75) / 1.5);
  return magnitudeVisibility * night;
}

function clamp01(value: number): number {
  return Math.max(0, Math.min(1, value));
}
