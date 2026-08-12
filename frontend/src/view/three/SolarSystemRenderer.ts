import * as THREE from "three";

import type { SkyEnvironmentSnapshot } from "../../contracts/sky_environment_contracts";
import type {
  ApparentTrajectoryMetadata,
  AstronomicalEventSnapshot,
  SolarEclipseState,
} from "../../contracts/astronomical_event_contracts";
import type {
  BodyOrientationState,
  LunarOrientationState,
  MoonSurfaceResourceDescriptor,
  PlanetTextureManifest,
  SatelliteCatalogManifest,
  SolarSystemBodyId,
  SolarSystemBodyState,
  SolarSystemSnapshot,
} from "../../contracts/solar_system_contracts";
import { threeFromEnu } from "./celestialCoordinates";
import { ApparentTrajectoryRenderer, type ApparentTrajectoryMetrics } from "./ApparentTrajectoryRenderer";
import { CelestialOcclusionPolicy } from "./CelestialOcclusionPolicy";
import {
  MoonSurfaceRenderer,
  moonLightDirectionThree,
  type MoonSurfaceRenderMetrics,
  type MoonTextureLoad,
} from "./MoonSurfaceRenderer";
import {
  NaturalSatelliteRenderer,
  type NaturalSatelliteMetrics,
  type SatelliteLodMode,
} from "./NaturalSatelliteRenderer";
import {
  PhysicalBodyVisual,
  type PhysicalBodyVisualMetrics,
} from "./PhysicalBodyVisual";
import {
  SatelliteOrbitRenderer,
  type OrbitBinaryMetadata,
  type SatelliteOrbitMetrics,
} from "./SatelliteOrbitRenderer";
import {
  SaturnRingRenderer,
  type SaturnRingMetrics,
} from "./SaturnRingRenderer";
import { SolarTotalityRenderer } from "./SolarTotalityRenderer";

const CELESTIAL_RADIUS = 900_000;
const INTERPOLATION_MS = 1000;
const LARGE_TIME_JUMP_SECONDS = 120;

export type PlanetBodyId =
  | "mercury"
  | "venus"
  | "mars"
  | "jupiter"
  | "saturn"
  | "uranus"
  | "neptune"
  | "pluto";

export const PLANET_IDS: readonly PlanetBodyId[] = [
  "mercury", "venus", "mars", "jupiter", "saturn", "uranus", "neptune", "pluto",
];

/** Visual identity only; texture mapping now comes from the validated manifest. */
export const PLANET_PRESENTATIONS = {
  mercury: { label: "Mercury", color: 0xdcc8af, cssColor: "#dcc8af", textureUrl: "/planet-assets/mercury.jpg" },
  venus: { label: "Venus", color: 0xfff5d2, cssColor: "#fff5d2", textureUrl: "/planet-assets/venus.jpg" },
  mars: { label: "Mars", color: 0xff7350, cssColor: "#ff7350", textureUrl: "/planet-assets/mars.jpg" },
  jupiter: { label: "Jupiter", color: 0xf5d7af, cssColor: "#f5d7af", textureUrl: "/planet-assets/jupiter.jpg" },
  saturn: { label: "Saturn", color: 0xebcd87, cssColor: "#ebcd87", textureUrl: "/planet-assets/saturn.jpg" },
  uranus: { label: "Uranus", color: 0xa5e1eb, cssColor: "#a5e1eb", textureUrl: "/planet-assets/uranus.jpg" },
  neptune: { label: "Neptune", color: 0x6e9bff, cssColor: "#6e9bff", textureUrl: "/planet-assets/neptune.jpg" },
  pluto: { label: "Pluto", color: 0xc8b29d, cssColor: "#c8b29d", textureUrl: null },
} satisfies Record<PlanetBodyId, {
  readonly label: string;
  readonly color: number;
  readonly cssColor: string;
  readonly textureUrl: string | null;
}>;

export const PLANET_EXTRA_TEXTURE_URLS = {
  venusSurface: "/planet-assets/venus_surface.jpg",
  saturnRings: "/planet-assets/saturn_rings.png",
};

const SUN_VERTEX_SHADER = /* glsl */ `
  varying float vCelestialY;
  void main() {
    vec4 worldPosition = modelMatrix * vec4(position, 1.0);
    vCelestialY = worldPosition.y - cameraPosition.y;
    vec4 mvPosition = modelViewMatrix * vec4(position, 1.0);
    gl_Position = projectionMatrix * mvPosition;
  }
`;

const SUN_FRAGMENT_SHADER = /* glsl */ `
  uniform vec3 uColor;
  uniform float uRenderAlpha;
  varying float vCelestialY;
  void main() {
    if (vCelestialY < 0.0) discard;
    gl_FragColor = vec4(uColor, uRenderAlpha);
    #include <tonemapping_fragment>
    #include <colorspace_fragment>
  }
`;

interface SunUniforms extends Record<string, THREE.IUniform<unknown>> {
  readonly uColor: THREE.IUniform<THREE.Color>;
  readonly uRenderAlpha: THREE.IUniform<number>;
}

interface SunEntity {
  readonly mesh: THREE.Mesh<THREE.SphereGeometry, THREE.ShaderMaterial>;
  readonly uniforms: SunUniforms;
}

export interface PickableSolarSystemBody {
  readonly id: SolarSystemBodyId;
  readonly state: SolarSystemBodyState;
  readonly object: THREE.Object3D;
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
  readonly planetTextureLoadCount: number;
  readonly planetTextureUploadBytes: number;
  readonly moon: MoonSurfaceRenderMetrics;
  readonly rings: SaturnRingMetrics;
  readonly satellites: NaturalSatelliteMetrics;
  readonly orbits: SatelliteOrbitMetrics;
  readonly trajectories: ApparentTrajectoryMetrics;
  readonly totality: {
    readonly geometryBuildCount: number;
    readonly materialBuildCount: number;
  };
}

export class SolarSystemRenderer {
  readonly root = new THREE.Group();
  private readonly planetsRoot = new THREE.Group();
  private readonly sharedBodyGeometry: THREE.SphereGeometry;
  private readonly sun: SunEntity;
  private readonly moonSurface: MoonSurfaceRenderer;
  private readonly planetVisuals = new Map<PlanetBodyId, PhysicalBodyVisual>();
  private readonly rings: SaturnRingRenderer;
  private readonly satellites: NaturalSatelliteRenderer;
  private readonly orbits: SatelliteOrbitRenderer;
  private readonly trajectories: ApparentTrajectoryRenderer;
  private readonly totality: SolarTotalityRenderer;
  private readonly occlusion = new CelestialOcclusionPolicy(CELESTIAL_RADIUS);
  private displayed = new Map<SolarSystemBodyId, SolarSystemBodyState>();
  private target = new Map<SolarSystemBodyId, SolarSystemBodyState>();
  private interpolation: Interpolation | null = null;
  private environment: SkyEnvironmentSnapshot | null = null;
  private latestGeneration = 0;
  private latestObserverGeneration = 0;
  private latestTimestampMs = 0;
  private latestEventGeneration = 0;
  private latestSolarEclipse: SolarEclipseState | null = null;
  private latestTerrainLimb: AstronomicalEventSnapshot["totalityAppearance"]["terrainCorrectedLimb"] = null;
  private eventBodySnapEnabled = false;
  private masterVisible = true;
  private sunVisible = true;
  private moonVisible = true;
  private planetsVisible = true;
  private satellitesVisible = false;
  private disposed = false;
  private _snapshotApplyCount = 0;
  private _staleSnapshotCount = 0;
  private _lastBridgeBytes = 0;

  readonly entityBuildCount: number;
  readonly geometryBuildCount: number;
  readonly materialBuildCount: number;

  constructor(parent: THREE.Object3D, textureLoad: MoonTextureLoad = browserTextureLoader()) {
    this.root.name = "solarSystemRoot";
    this.planetsRoot.name = "planets";
    this.sharedBodyGeometry = new THREE.SphereGeometry(1, 64, 40);
    this.sun = this.createSun();
    this.root.add(this.sun.mesh, this.planetsRoot);
    this.moonSurface = new MoonSurfaceRenderer(this.root, textureLoad);
    for (const id of PLANET_IDS) {
      const visual = new PhysicalBodyVisual(
        id,
        this.sharedBodyGeometry,
        PLANET_PRESENTATIONS[id].color,
        textureLoad,
      );
      this.planetVisuals.set(id, visual);
      this.planetsRoot.add(visual.root);
    }
    const saturn = this.planetVisuals.get("saturn");
    if (saturn === undefined) throw new Error("Saturn visual was not constructed");
    this.rings = new SaturnRingRenderer(saturn.root, textureLoad);
    this.satellites = new NaturalSatelliteRenderer(this.root);
    this.orbits = new SatelliteOrbitRenderer(this.root);
    this.trajectories = new ApparentTrajectoryRenderer(this.root);
    this.totality = new SolarTotalityRenderer(this.root);
    parent.add(this.root);

    this.entityBuildCount = 2 + this.planetVisuals.size;
    this.geometryBuildCount = 1
      + this.moonSurface.geometryBuildCount
      + this.rings.metrics().geometryBuildCount
      + this.satellites.metrics().geometryBuildCount;
    this.materialBuildCount = 1
      + this.moonSurface.materialBuildCount
      + this.planetVisuals.size
      + this.rings.metrics().materialBuildCount
      + this.satellites.metrics().materialBuildCount;
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
    this.orbits.updateSnapshot(snapshot);
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
      nextDisplayed.set(
        id,
        this.eventBodySnapEnabled && isEclipseGeometryBody(id)
          ? target
          : interpolateBody(start, target, fraction),
      );
    }
    this.displayed = nextDisplayed;
    this.applyDisplayed();
    if (fraction >= 1.0) this.interpolation = null;
  }

  updateEnvironment(snapshot: SkyEnvironmentSnapshot): void {
    this.environment = snapshot;
    this.moonSurface.updateEnvironment(snapshot);
    this.applyDisplayed();
  }

  configurePlanetTextures(manifest: PlanetTextureManifest, maxTextureSize = Infinity): void {
    const byBody = new Map<PlanetBodyId, typeof manifest.textures[number][]>();
    for (const asset of manifest.textures) {
      if (!isPlanetBodyId(asset.bodyId) || asset.widthPx > maxTextureSize) continue;
      const values = byBody.get(asset.bodyId) ?? [];
      values.push(asset);
      byBody.set(asset.bodyId, values);
    }
    for (const id of PLANET_IDS) {
      const options = byBody.get(id) ?? [];
      const preferred = options.find((asset) => (
        id === "venus" ? asset.role === "atmosphere_reference" : asset.role !== "rings"
      )) ?? null;
      this.planetVisuals.get(id)?.configureTexture(preferred);
    }
    const ringTexture = byBody.get("saturn")?.find((asset) => asset.role === "rings") ?? null;
    this.rings.configureTexture(ringTexture);
  }

  configureSatelliteCatalog(catalog: SatelliteCatalogManifest): void {
    this.satellites.configureCatalog(catalog);
  }

  registerOrbitResource(metadata: OrbitBinaryMetadata, buffer: ArrayBuffer): boolean {
    return this.orbits.registerBinaryResource(metadata, buffer);
  }

  registerApparentTrajectoryResource(
    metadata: ApparentTrajectoryMetadata,
    buffer: ArrayBuffer,
  ): boolean {
    return this.trajectories.registerBinaryResource(metadata, buffer);
  }

  updateEventSnapshot(snapshot: AstronomicalEventSnapshot): boolean {
    if (
      snapshot.generation <= this.latestEventGeneration
      || snapshot.sourceSolarSystemGeneration !== this.latestGeneration
      || snapshot.observerGeneration !== this.latestObserverGeneration
    ) return false;
    this.latestEventGeneration = snapshot.generation;
    this.latestSolarEclipse = snapshot.solar;
    this.latestTerrainLimb = snapshot.totalityAppearance.terrainCorrectedLimb;
    this.eventBodySnapEnabled = snapshot.solar.classification !== "none"
      || snapshot.lunar.classification !== "none";
    if (this.eventBodySnapEnabled) {
      for (const id of ["sun", "moon"] as const) {
        const target = this.target.get(id);
        if (target !== undefined) this.displayed.set(id, target);
      }
    }
    this.totality.updateEvent(snapshot);
    this.moonSurface.updateEclipse(snapshot.lunar);
    this.applyDisplayed();
    return true;
  }

  setVisibility(
    part: "system" | "sun" | "moon" | "planets" | "rings" | "satellites" | "orbits" | "trajectories",
    visible: boolean,
  ): void {
    if (part === "system") this.masterVisible = visible;
    if (part === "sun") this.sunVisible = visible;
    if (part === "moon") this.moonVisible = visible;
    if (part === "planets") this.planetsVisible = visible;
    if (part === "rings") this.rings.setEnabled(visible);
    if (part === "satellites") {
      this.satellitesVisible = visible;
      this.satellites.setEnabled(visible);
    }
    if (part === "orbits") this.orbits.setEnabled(visible);
    if (part === "trajectories") this.trajectories.setEnabled(visible);
    this.applyDisplayed();
  }

  setSatelliteLodMode(mode: SatelliteLodMode): void {
    this.satellites.setLodMode(mode);
  }

  updateCamera(fovDeg: number, heightPx: number): void {
    this.satellites.updateCamera(fovDeg, heightPx);
  }

  setMoonSurfaceEnabled(enabled: boolean): void {
    this.moonSurface.setSurfaceEnabled(enabled);
  }

  configureMoonSurface(
    resource: MoonSurfaceResourceDescriptor,
    maxTextureSize: number,
  ): MoonSurfaceRenderMetrics {
    this.moonSurface.configureResource(resource, maxTextureSize);
    return this.moonSurface.metrics();
  }

  getBodyObject(id: SolarSystemBodyId): THREE.Object3D | undefined {
    if (id === "moon") return this.moonSurface.mesh;
    if (id === "sun") return this.sun.mesh;
    if (isPlanetBodyId(id)) return this.planetVisuals.get(id)?.mesh;
    return this.satellites.getPickableBodies().find((item) => item.id === id)?.object;
  }

  getLabelAnchor(id: SolarSystemBodyId): THREE.Object3D | undefined {
    if (id === "moon") return this.moonSurface.labelAnchor;
    if (id === "sun") return this.sun.mesh;
    if (isPlanetBodyId(id)) return this.planetVisuals.get(id)?.root;
    return this.satellites.getPickableBodies().find((item) => item.id === id)?.object;
  }

  getPickableBodies(): readonly PickableSolarSystemBody[] {
    const bodies: PickableSolarSystemBody[] = [];
    for (const [id, state] of this.displayed) {
      if (id === "moon") {
        const object = this.moonSurface.getPickObject();
        if (object !== undefined) bodies.push({ id, state, object });
      } else if (id === "sun" && this.sun.mesh.visible) {
        bodies.push({ id, state, object: this.sun.mesh });
      } else if (isPlanetBodyId(id)) {
        const visual = this.planetVisuals.get(id);
        if (visual?.root.visible) bodies.push({ id, state, object: visual.root });
      }
    }
    bodies.push(...this.satellites.getPickableBodies());
    return bodies;
  }

  getDisplayedBodyDirection(id: SolarSystemBodyId): THREE.Vector3 | null {
    // Obtenim l'objecte visual actualment interpolat
    const obj = this.getLabelAnchor(id);
    if (!obj) return null;
    
    // El celestialRoot no té rotació (està alineat amb l'ENU de ThreeJS), només translació.
    const state = this.displayed.get(id);
    if (!state) return null;
    return threeFromEnu(state.directionENU).normalize();
  }

  isPlanetLabelVisible(id: PlanetBodyId, state: SolarSystemBodyState | undefined): boolean {
    if (!state || !this.planetsVisible || !this.masterVisible) return false;
    return (state.horizonVisible ?? state.altitudeDeg + state.angularRadiusDeg > 0);
  }

  isBodyVisuallyObservable(state: SolarSystemBodyState): boolean {
    if (!this.environment) return true;
    if (this.environment.twilightPhase === "night") return true;
    if (state.apparentMagnitude === null) return true;
    return state.apparentMagnitude <= this.environment.visibility.zenithMagnitudeLimit;
  }

  metrics(): SolarSystemRenderMetrics {
    let textureLoads = 0;
    let textureBytes = 0;
    for (const visual of this.planetVisuals.values()) {
      const metrics = visual.metrics();
      textureLoads += metrics.textureLoadCount;
      textureBytes += metrics.textureUploadBytes;
    }
    return {
      entityBuildCount: this.entityBuildCount + this.satellites.metrics().entityBuildCount,
      geometryBuildCount: this.geometryBuildCount + this.orbits.metrics().geometryBuildCount,
      materialBuildCount: this.materialBuildCount + this.orbits.metrics().materialBuildCount,
      snapshotApplyCount: this._snapshotApplyCount,
      staleSnapshotCount: this._staleSnapshotCount,
      lastBridgeBytes: this._lastBridgeBytes,
      planetTextureLoadCount: textureLoads,
      planetTextureUploadBytes: textureBytes,
      moon: this.moonSurface.metrics(),
      rings: this.rings.metrics(),
      satellites: this.satellites.metrics(),
      orbits: this.orbits.metrics(),
      trajectories: this.trajectories.metrics(),
      totality: {
        geometryBuildCount: this.totality.geometryBuildCount,
        materialBuildCount: this.totality.materialBuildCount,
      },
    };
  }

  dispose(): void {
    if (this.disposed) return;
    this.disposed = true;
    this.root.removeFromParent();
    this.sharedBodyGeometry.dispose();
    this.sun.mesh.material.dispose();
    this.moonSurface.dispose();
    this.rings.dispose();
    this.satellites.dispose();
    this.orbits.dispose();
    this.trajectories.dispose();
    this.totality.dispose();
    for (const visual of this.planetVisuals.values()) visual.dispose();
    this.planetVisuals.clear();
  }

  private createSun(): SunEntity {
    const uniforms: SunUniforms = {
      uColor: { value: new THREE.Color(0xfff4c2) },
      uRenderAlpha: { value: 1 },
    };
    const material = new THREE.ShaderMaterial({
      vertexShader: SUN_VERTEX_SHADER,
      fragmentShader: SUN_FRAGMENT_SHADER,
      uniforms,
      transparent: true,
      depthTest: true,
      depthWrite: false,
    });
    const mesh = new THREE.Mesh(this.sharedBodyGeometry, material);
    mesh.name = "sun";
    mesh.visible = false;
    mesh.frustumCulled = false;
    mesh.renderOrder = -101;
    return { mesh, uniforms };
  }

  private hideUnavailable(available: ReadonlyMap<SolarSystemBodyId, SolarSystemBodyState>): void {
    if (!available.has("sun")) this.sun.mesh.visible = false;
    if (!available.has("moon")) this.moonSurface.mesh.visible = false;
    for (const [id, visual] of this.planetVisuals) {
      if (!available.has(id)) {
        visual.root.visible = false;
        visual.mesh.visible = false;
      }
    }
  }

  private applyDisplayed(): void {
    const sun = this.displayed.get("sun");
    if (sun === undefined) return;
    const satelliteStates: SolarSystemBodyState[] = [];
    for (const [id, state] of this.displayed) {
      if (state.type === "natural_satellite") {
        satelliteStates.push(state);
        continue;
      }
      if (id === "moon") {
        const direction = threeFromEnu(state.directionENU).normalize();
        const radius = this.occlusion.presentationRadius(state, this.displayed.values());
        this.moonSurface.root.position.copy(direction).multiplyScalar(radius);
        this.moonSurface.setPresentationScale(
          this.occlusion.apparentRadius(radius, state.angularRadiusDeg),
        );
        this.moonSurface.setRenderOrder(this.occlusion.renderOrder(state, this.displayed.values()));
        const fallbackLight = phaseLightDirectionThree(state, sun);
        this.moonSurface.updateState(
          state,
          moonLightDirectionThree(state, fallbackLight),
          this.isVisible(id) && (state.horizonVisible ?? state.altitudeDeg + state.angularRadiusDeg > 0),
        );
        this.totality.updateMoon(state);
        continue;
      }
      if (id === "sun") {
        const direction = threeFromEnu(state.directionENU).normalize();
        const radius = this.occlusion.presentationRadius(state, this.displayed.values());
        this.sun.mesh.position.copy(direction).multiplyScalar(radius);
        this.sun.mesh.scale.setScalar(this.occlusion.apparentRadius(radius, state.angularRadiusDeg));
        this.sun.mesh.renderOrder = this.occlusion.renderOrder(state, this.displayed.values());
        this.totality.updateSun(state, radius);
        this.sun.uniforms.uRenderAlpha.value = 1;
        this.sun.mesh.visible = this.isVisible(id)
          && (state.horizonVisible ?? state.altitudeDeg + state.angularRadiusDeg > 0);
        this.sun.mesh.userData.apparentState = state;
        continue;
      }
      if (!isPlanetBodyId(id)) continue;
      const visual = this.planetVisuals.get(id);
      if (visual === undefined) continue;
      const visibility = this.isVisible(id)
        && (state.horizonVisible ?? state.altitudeDeg + state.angularRadiusDeg > 0);
      visual.updateState(
        state,
        this.occlusion.apparentRadius(
          this.occlusion.presentationRadius(state, this.displayed.values()),
          state.angularRadiusDeg,
        ),
        phaseLightDirectionThree(state, sun),
        visibility,
        this.occlusion.presentationRadius(state, this.displayed.values()),
      );
      visual.mesh.renderOrder = this.occlusion.renderOrder(state, this.displayed.values());
      if (id === "saturn") this.rings.updateState(state, visibility);
    }
    this.satellites.setEnabled(this.masterVisible && this.satellitesVisible);
    this.satellites.updateStates(satelliteStates, this.displayed, this.occlusion);
    if (this.latestSolarEclipse !== null) {
      const moon = this.displayed.get("moon");
      if (moon !== undefined) {
        this.moonSurface.updateSolarOccultation(
          this.latestSolarEclipse,
          threeFromEnu(sun.directionENU).normalize(),
          threeFromEnu(moon.directionENU).normalize(),
          this.latestTerrainLimb,
        );
      }
    }
  }

  private isVisible(id: SolarSystemBodyId): boolean {
    if (!this.masterVisible) return false;
    if (id === "sun") return this.sunVisible;
    if (id === "moon") return this.moonVisible;
    if (id.startsWith("naif-") || id.startsWith("provisional-")) return this.satellitesVisible;
    return this.planetsVisible;
  }
}

export function phaseLightDirectionThree(
  body: SolarSystemBodyState,
  sun: SolarSystemBodyState,
): THREE.Vector3 {
  const exact = body.bodyToSunDirectionENU;
  if (exact !== undefined && exact !== null) return threeFromEnu(exact).normalize();
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
  for (const satellite of snapshot.satellites ?? []) states.set(satellite.id, satellite);
  return states;
}

function isEclipseGeometryBody(id: SolarSystemBodyId): boolean {
  return id === "sun" || id === "moon";
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
    apparentMagnitude: (
      start.apparentMagnitude === null || target.apparentMagnitude === null
        ? target.apparentMagnitude
        : lerp(start.apparentMagnitude, target.apparentMagnitude)
    ),
    orientation: interpolateOrientation(start.orientation, target.orientation, fraction),
    bodyToSunDirectionENU: interpolateDirection(
      start.bodyToSunDirectionENU ?? null,
      target.bodyToSunDirectionENU ?? null,
      fraction,
    ),
  };
}

function interpolateOrientation(
  start: LunarOrientationState | BodyOrientationState | null,
  target: LunarOrientationState | BodyOrientationState | null,
  fraction: number,
): LunarOrientationState | BodyOrientationState | null {
  if (start === null || target === null) return target;
  if (isBodyOrientation(start) && isBodyOrientation(target)) {
    return {
      ...target,
      bodyToENUQuaternion: interpolateQuaternion(
        start.bodyToENUQuaternion, target.bodyToENUQuaternion, fraction,
      ),
      equatorialToENUQuaternion: interpolateQuaternion(
        start.equatorialToENUQuaternion, target.equatorialToENUQuaternion, fraction,
      ),
      bodyToSunDirectionENU: interpolateDirection(
        start.bodyToSunDirectionENU, target.bodyToSunDirectionENU, fraction,
      ),
    };
  }
  if (isBodyOrientation(start) || isBodyOrientation(target)) return target;
  if (
    start.quality !== "precise"
    || target.quality !== "precise"
    || start.bodyToENUQuaternion === null
    || target.bodyToENUQuaternion === null
  ) return target;
  return {
    ...target,
    bodyToENUQuaternion: interpolateQuaternion(
      start.bodyToENUQuaternion, target.bodyToENUQuaternion, fraction,
    ),
    librationLongitudeDeg: interpolateAngleNullable(
      start.librationLongitudeDeg, target.librationLongitudeDeg, fraction,
    ),
    librationLatitudeDeg: lerpNullable(
      start.librationLatitudeDeg, target.librationLatitudeDeg, fraction,
    ),
    subEarthLongitudeDeg: interpolateAngleNullable(
      start.subEarthLongitudeDeg, target.subEarthLongitudeDeg, fraction,
    ),
    subEarthLatitudeDeg: lerpNullable(
      start.subEarthLatitudeDeg, target.subEarthLatitudeDeg, fraction,
    ),
    subObserverLongitudeDeg: interpolateAngleNullable(
      start.subObserverLongitudeDeg, target.subObserverLongitudeDeg, fraction,
    ),
    subObserverLatitudeDeg: lerpNullable(
      start.subObserverLatitudeDeg, target.subObserverLatitudeDeg, fraction,
    ),
    northPolePositionAngleDeg: interpolateAngleNullable(
      start.northPolePositionAngleDeg, target.northPolePositionAngleDeg, fraction,
    ),
    brightLimbPositionAngleDeg: interpolateAngleNullable(
      start.brightLimbPositionAngleDeg, target.brightLimbPositionAngleDeg, fraction,
    ),
    moonToSunDirectionENU: interpolateDirection(
      start.moonToSunDirectionENU, target.moonToSunDirectionENU, fraction,
    ),
  };
}

function interpolateQuaternion(
  start: readonly [number, number, number, number] | null,
  target: readonly [number, number, number, number] | null,
  fraction: number,
): readonly [number, number, number, number] | null {
  if (start === null || target === null) return target;
  const value = new THREE.Quaternion(...start)
    .slerp(new THREE.Quaternion(...target), fraction)
    .normalize();
  return [value.x, value.y, value.z, value.w];
}

function interpolateDirection(
  start: readonly [number, number, number] | null,
  target: readonly [number, number, number] | null,
  fraction: number,
): readonly [number, number, number] | null {
  if (start === null || target === null) return target;
  const value = new THREE.Vector3(...start).lerp(new THREE.Vector3(...target), fraction).normalize();
  return [value.x, value.y, value.z];
}

function interpolateAngleNullable(
  start: number | null,
  target: number | null,
  fraction: number,
): number | null {
  return start === null || target === null ? target : interpolateAngle(start, target, fraction);
}

function lerpNullable(start: number | null, target: number | null, fraction: number): number | null {
  return start === null || target === null ? target : THREE.MathUtils.lerp(start, target, fraction);
}

function interpolateAngle(start: number, target: number, fraction: number): number {
  const delta = ((target - start + 540) % 360) - 180;
  return (start + delta * fraction + 360) % 360;
}

function renderAlpha(body: SolarSystemBodyState, environment: SkyEnvironmentSnapshot | null): number {
  if (body.id === "sun" || body.id === "moon" || body.apparentMagnitude === null) return 1;
  const night = environment?.twilightFactor ?? 1;
  const limit = environment?.visibility.zenithMagnitudeLimit ?? 6;
  const magnitudeVisibility = clamp01((limit - body.apparentMagnitude + 0.75) / 1.5);
  return magnitudeVisibility * night;
}

function isPlanetBodyId(id: string): id is PlanetBodyId {
  return (PLANET_IDS as readonly string[]).includes(id);
}

function isBodyOrientation(
  orientation: LunarOrientationState | BodyOrientationState,
): orientation is BodyOrientationState {
  return "equatorialToENUQuaternion" in orientation;
}

function browserTextureLoader(): MoonTextureLoad {
  const loader = new THREE.TextureLoader();
  return (url, onLoad, onError) => loader.load(url, onLoad, undefined, onError);
}

function clamp01(value: number): number {
  return Math.max(0, Math.min(1, value));
}
