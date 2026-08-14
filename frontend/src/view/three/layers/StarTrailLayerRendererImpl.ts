import * as THREE from "three";
import type { SceneDelta } from "../../../contracts/scene";
import type { StarTrailLayerRenderer } from "./StarTrailLayerRenderer";
import type { StarFieldRenderer } from "../StarFieldRenderer";
import type { CelestialTransformState } from "../CelestialTransformState";
import type { SolarSystemSnapshot, SolarSystemBodyState } from "../../../contracts/solar_system_contracts";

export interface StarTrailsComponentPayload {
  sessionId: string;
  sessionVersion: number;
  state: string;
  playbackRate: number;
  magnitudeLimit: number;
}

const BODY_COLORS: Record<string, [number, number, number]> = {
  sun: [1.0, 0.95, 0.69],
  moon: [0.9, 0.9, 0.9],
  mercury: [0.86, 0.78, 0.69],
  venus: [1.0, 0.96, 0.82],
  mars: [1.0, 0.45, 0.31],
  jupiter: [0.96, 0.84, 0.69],
  saturn: [0.92, 0.80, 0.53],
  uranus: [0.65, 0.88, 0.92],
  neptune: [0.43, 0.61, 1.0],
  pluto: [0.78, 0.70, 0.62],
};

const TRAIL_VERTEX_SHADER = `
attribute float segmentIndex;
attribute vec3 color;

uniform mat3 u_equatorialToENUMatrix;
uniform float u_exposureAngle;
uniform float u_radius;

varying vec3 vColor;

void main() {
    vColor = color;
    
    // Angle cap al passat: rota enrere de 0 a u_exposureAngle segons el segment
    float angle = -u_exposureAngle * (1.0 - segmentIndex);
    
    // Rotació equatorial al voltant de l'eix polar Z
    float cosA = cos(angle);
    float sinA = sin(angle);
    vec3 eq_rot = vec3(
        position.x * cosA - position.y * sinA,
        position.x * sinA + position.y * cosA,
        position.z
    );
    
    vec3 posWorld = u_equatorialToENUMatrix * eq_rot;
    gl_Position = projectionMatrix * modelViewMatrix * vec4(posWorld * u_radius, 1.0);
}
`;

const TRAIL_FRAGMENT_SHADER = `
varying vec3 vColor;

void main() {
    // TerraLab authentic stellar trail color tone (0.70 intensity with AdditiveBlending matches the original golden-azure palette)
    gl_FragColor = vec4(vColor * 0.70, 1.0);
    #include <tonemapping_fragment>
    #include <colorspace_fragment>
}
`;

export class StarTrailLayerRendererImpl implements StarTrailLayerRenderer {
  private readonly rootGroup = new THREE.Group();
  
  private activeSessionId: string | null = null;
  private activeVersion: number = -1;
  private state: string = "idle";
  
  private playbackRate: number = 1.0;
  private accumulatedPlaybackTimeSeconds: number = 0.0;
  private lastMagnitudeLimit: number = 6.0;
  
  private linesGeometry: THREE.BufferGeometry | null = null;
  private linesMaterial: THREE.ShaderMaterial | null = null;
  private linesMesh: THREE.LineSegments | null = null;
  
  private selectedStarsCount: number = 0;
  
  private transformState: CelestialTransformState | null = null;
  private observerLatitude: number = 0.0;
  private latestSolarSystemSnapshot: SolarSystemSnapshot | null = null;

  constructor(parent: THREE.Group, private starFieldRenderer: StarFieldRenderer) {
    this.rootGroup.name = "starTrailsRoot";
    parent.add(this.rootGroup);
  }

  public applyDelta(_delta: SceneDelta): void {}

  public updateSolarSystemSnapshot(snapshot: SolarSystemSnapshot): void {
    this.latestSolarSystemSnapshot = snapshot;
  }

  public setTransformState(state: CelestialTransformState): void {
    this.transformState = state;
  }
  
  public setObserverLatitude(latDeg: number): void {
    this.observerLatitude = latDeg;
  }
  
  public getStarCount(): number {
    return this.selectedStarsCount;
  }
  
  public getSegmentCount(): number {
    return this.selectedStarsCount * 128; 
  }
  
  public getGpuBytes(): number {
    if (!this.linesGeometry) return 0;
    const totalVertices = this.selectedStarsCount * 128 * 2;
    return totalVertices * 3 * 4 + totalVertices * 4 + totalVertices * 3 * 4;
  }

  private startUtcMs: number | null = null;
  private currentSimUtcMs: number | null = null;

  public applySnapshot(payload: StarTrailsComponentPayload & { startUtcIso?: string; accumulatedExposureSeconds?: number }): void {
    this.playbackRate = payload.playbackRate;
    this.lastMagnitudeLimit = payload.magnitudeLimit;
    if (payload.startUtcIso) {
      this.startUtcMs = new Date(payload.startUtcIso).getTime();
    }
    if (payload.accumulatedExposureSeconds !== undefined) {
      this.accumulatedPlaybackTimeSeconds = payload.accumulatedExposureSeconds;
    }
    
    if (this.activeSessionId === payload.sessionId && this.selectedStarsCount === 0 && this.starFieldRenderer.getResources().size > 0) {
      if (payload.state !== "idle") {
         this.initNewSession(payload);
      }
    }
    
    if (this.activeSessionId !== payload.sessionId || this.activeVersion !== payload.sessionVersion) {
      if (payload.sessionId && payload.state !== "idle") {
        this.initNewSession(payload);
      } else {
        this.clearSession();
      }
    }
    this.state = payload.state;
  }

  private clearSession(): void {
    this.activeSessionId = null;
    this.activeVersion = -1;
    this.state = "idle";
    this.selectedStarsCount = 0;
    this.accumulatedPlaybackTimeSeconds = 0.0;
    this.startUtcMs = null;
    
    if (this.linesMesh) {
      this.rootGroup.remove(this.linesMesh);
      this.linesGeometry?.dispose();
      this.linesMaterial?.dispose();
      this.linesMesh = null;
      this.linesGeometry = null;
      this.linesMaterial = null;
    }
  }

  public setCurrentSimulationTime(isoUtc: string): void {
    this.currentSimUtcMs = new Date(isoUtc).getTime();
  }

  private initNewSession(payload: StarTrailsComponentPayload & { startUtcIso?: string; accumulatedExposureSeconds?: number }): void {
    this.clearSession();
    this.activeSessionId = payload.sessionId;
    this.activeVersion = payload.sessionVersion;
    this.state = payload.state;
    this.accumulatedPlaybackTimeSeconds = payload.accumulatedExposureSeconds ?? 0.0;
    this.lastMagnitudeLimit = payload.magnitudeLimit;
    if (payload.startUtcIso) {
      this.startUtcMs = new Date(payload.startUtcIso).getTime();
    }
    
    this.allocateGeometry(payload.magnitudeLimit);
  }

  private allocateGeometry(magnitudeLimit: number): void {
    this.lastMagnitudeLimit = magnitudeLimit;
    const resources = this.starFieldRenderer.getResources();
    if (resources.size === 0) return;

    // Utilitzem el catàleg general (o fallback)
    const targetEntry = resources.get("stars:general") || resources.get("stars:fallback") || resources.values().next().value;
    if (!targetEntry) return;

    const count = targetEntry.catalogIndices.length;
    const effectiveLimit = Math.max(2.5, magnitudeLimit);

    // Seleccionem tots els estels visibles fins a la magnitud límit (com a TerraLab original)
    const validStarIndices: number[] = [];
    for (let i = 0; i < count; i++) {
      const mag = targetEntry.magnitudesArray[i]!;
      if (mag <= effectiveLimit) {
        validStarIndices.push(i);
      }
    }

    // Si hi ha més de 10.000 estels, triem els més brillants per garantir fluïdesa i definició impecable
    const MAX_TRAIL_STARS = 10000;
    if (validStarIndices.length > MAX_TRAIL_STARS) {
      validStarIndices.sort((a, b) => targetEntry.magnitudesArray[a]! - targetEntry.magnitudesArray[b]!);
      validStarIndices.length = MAX_TRAIL_STARS;
    }

    // Afegim els cossos del Sistema Solar (Sol, Lluna, Planetes)
    const solarBodies: { x: number; y: number; z: number; r: number; g: number; b: number }[] = [];
    if (this.latestSolarSystemSnapshot) {
      const candidates: (SolarSystemBodyState | null | undefined)[] = [
        this.latestSolarSystemSnapshot.sun,
        this.latestSolarSystemSnapshot.moon,
        ...(this.latestSolarSystemSnapshot.planets ?? [])
      ];
      for (const body of candidates) {
        if (body && typeof body.rightAscensionDeg === "number" && typeof body.declinationDeg === "number") {
          const raRad = THREE.MathUtils.degToRad(body.rightAscensionDeg);
          const decRad = THREE.MathUtils.degToRad(body.declinationDeg);
          const x = Math.cos(decRad) * Math.cos(raRad);
          const y = Math.cos(decRad) * Math.sin(raRad);
          const z = Math.sin(decRad);
          const c = BODY_COLORS[body.id] || [1.0, 1.0, 1.0];
          solarBodies.push({ x, y, z, r: c[0], g: c[1], b: c[2] });
        }
      }
    }

    const totalObjects = validStarIndices.length + solarBodies.length;
    this.selectedStarsCount = totalObjects;
    if (totalObjects === 0) return;

    const SEGMENTS = 128;
    const VERTICES_PER_OBJECT = SEGMENTS * 2;
    const totalVertices = totalObjects * VERTICES_PER_OBJECT;

    const positions = new Float32Array(totalVertices * 3);
    const segmentIndices = new Float32Array(totalVertices);
    const colors = new Float32Array(totalVertices * 3);
    
    let vIdx = 0;
    const colorsAttr = targetEntry.geometry.getAttribute("color")?.array as Float32Array | undefined;

    // 1. Estels del catàleg
    for (const i of validStarIndices) {
      const eqX = targetEntry.equatorialPositions[i * 3 + 0]!;
      const eqY = targetEntry.equatorialPositions[i * 3 + 1]!;
      const eqZ = targetEntry.equatorialPositions[i * 3 + 2]!;

      const r = colorsAttr ? colorsAttr[i * 3 + 0]! : 1.0;
      const g = colorsAttr ? colorsAttr[i * 3 + 1]! : 1.0;
      const b = colorsAttr ? colorsAttr[i * 3 + 2]! : 1.0;

      for (let seg = 0; seg < SEGMENTS; seg++) {
         positions[vIdx * 3 + 0] = eqX;
         positions[vIdx * 3 + 1] = eqY;
         positions[vIdx * 3 + 2] = eqZ;
         segmentIndices[vIdx] = seg / SEGMENTS;
         colors[vIdx * 3 + 0] = r;
         colors[vIdx * 3 + 1] = g;
         colors[vIdx * 3 + 2] = b;
         vIdx++;
         
         positions[vIdx * 3 + 0] = eqX;
         positions[vIdx * 3 + 1] = eqY;
         positions[vIdx * 3 + 2] = eqZ;
         segmentIndices[vIdx] = (seg + 1) / SEGMENTS;
         colors[vIdx * 3 + 0] = r;
         colors[vIdx * 3 + 1] = g;
         colors[vIdx * 3 + 2] = b;
         vIdx++;
      }
    }

    // 2. Cossos del Sistema Solar (Planetes, Lluna, Sol)
    for (const body of solarBodies) {
      for (let seg = 0; seg < SEGMENTS; seg++) {
         positions[vIdx * 3 + 0] = body.x;
         positions[vIdx * 3 + 1] = body.y;
         positions[vIdx * 3 + 2] = body.z;
         segmentIndices[vIdx] = seg / SEGMENTS;
         colors[vIdx * 3 + 0] = body.r;
         colors[vIdx * 3 + 1] = body.g;
         colors[vIdx * 3 + 2] = body.b;
         vIdx++;
         
         positions[vIdx * 3 + 0] = body.x;
         positions[vIdx * 3 + 1] = body.y;
         positions[vIdx * 3 + 2] = body.z;
         segmentIndices[vIdx] = (seg + 1) / SEGMENTS;
         colors[vIdx * 3 + 0] = body.r;
         colors[vIdx * 3 + 1] = body.g;
         colors[vIdx * 3 + 2] = body.b;
         vIdx++;
      }
    }

    if (this.linesMesh) {
      this.rootGroup.remove(this.linesMesh);
      this.linesGeometry?.dispose();
      this.linesMaterial?.dispose();
    }

    this.linesGeometry = new THREE.BufferGeometry();
    this.linesGeometry.setAttribute("position", new THREE.BufferAttribute(positions, 3));
    this.linesGeometry.setAttribute("segmentIndex", new THREE.BufferAttribute(segmentIndices, 1));
    this.linesGeometry.setAttribute("color", new THREE.BufferAttribute(colors, 3));

    const mat3 = new THREE.Matrix3();
    if (this.transformState && this.transformState.isValid) {
      mat3.copy(this.transformState.equatorialToThree);
    }

    this.linesMaterial = new THREE.ShaderMaterial({
      vertexShader: TRAIL_VERTEX_SHADER,
      fragmentShader: TRAIL_FRAGMENT_SHADER,
      uniforms: {
        u_equatorialToENUMatrix: { value: mat3 },
        u_exposureAngle: { value: 0.0 },
        u_radius: { value: 1000000.0 }
      },
      blending: THREE.AdditiveBlending,
      transparent: true,
      depthTest: true,
      depthWrite: false
    });

    this.linesMesh = new THREE.LineSegments(this.linesGeometry, this.linesMaterial);
    this.linesMesh.frustumCulled = false;
    this.linesMesh.renderOrder = 1;
    this.rootGroup.add(this.linesMesh);
  }

  private lastUpdateMs: number | null = null;

  public update(timestampMs: number): void {
    if (this.state !== "idle" && this.selectedStarsCount === 0 && this.starFieldRenderer.getResources().size > 0) {
      this.allocateGeometry(this.lastMagnitudeLimit);
    }

    if (this.startUtcMs !== null && this.currentSimUtcMs !== null && this.state === "running") {
      let elapsedSeconds = (this.currentSimUtcMs - this.startUtcMs) / 1000.0;
      if (elapsedSeconds < 0) elapsedSeconds = 0;
      this.accumulatedPlaybackTimeSeconds = elapsedSeconds;
    }

    if (this.linesMaterial && this.transformState?.isValid) {
      const uniforms = this.linesMaterial.uniforms;
      // 1. Matriu actual equatorial -> ENU
      const mat3 = uniforms.u_equatorialToENUMatrix?.value as THREE.Matrix3 | undefined;
      if (mat3) mat3.copy(this.transformState.equatorialToThree);

      // 2. El cel es mou exactament 15º per hora (15 * (PI / 180) / 3600 rad/s)
      const radiansPerSecond = (15.0 * (Math.PI / 180.0)) / 3600.0;
      if (uniforms.u_exposureAngle) {
        uniforms.u_exposureAngle.value = this.accumulatedPlaybackTimeSeconds * radiansPerSecond;
      }
    }
  }

  public dispose(): void {
    this.clearSession();
    if (this.rootGroup.parent) {
      this.rootGroup.parent.remove(this.rootGroup);
    }
  }
}

