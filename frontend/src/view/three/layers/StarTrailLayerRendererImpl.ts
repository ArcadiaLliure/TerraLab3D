import * as THREE from "three";
import type { SceneDelta } from "../../../contracts/scene";
import type { CelestialTransformState } from "../CelestialTransformState";
import type { StarFieldRenderer, StarResourceEntry } from "../StarFieldRenderer";
import type { StarTrailLayerRenderer } from "./StarTrailLayerRenderer";
import {
  buildTrailRibbonGeometryData,
  estimateTrailGpuBytes,
  exposureSecondsToSiderealRadians,
  legacyStereographicZoom,
  quantizeTrailLinearChannel,
  selectTrailStarIndices,
  TRAIL_ANTIALIAS_RADIUS_PHYSICAL_PX,
  TRAIL_MAX_SEGMENTS,
  TRAIL_LINE_WIDTH_CSS_PX,
  TRAIL_STABLE_ALPHA,
  trailSegmentCountForDuration,
} from "./starTrailMath";

export interface StarTrailsComponentPayload {
  readonly sessionId: string;
  readonly sessionVersion: number;
  readonly state: string;
  readonly playbackRate: number;
  readonly magnitudeLimit: number;
  readonly startUtcIso?: string;
  readonly accumulatedExposureSeconds?: number;
  readonly durationSeconds?: number;
}

export interface StarTrailRendererMetrics {
  readonly state: string;
  readonly starCount: number;
  readonly segmentCount: number;
  readonly vertexCount: number;
  readonly gpuBytes: number;
  readonly geometryBuildCount: number;
  readonly geometryDisposeCount: number;
  readonly cumulativeUploadBytes: number;
  readonly exposureAngleRad: number;
  readonly drawCalls: number;
}

type StarTrailCatalogSource = Pick<
  StarFieldRenderer,
  "getResources" | "setTrailSuppressed"
>;

interface StarTrailViewport {
  getDrawingBufferSize(target: THREE.Vector2): THREE.Vector2;
  getPixelRatio(): number;
}

const TRAIL_RADIUS = 1_000_000.0;

const TRAIL_VERTEX_SHADER = /* glsl */ `
attribute vec3 equatorialPosition;
attribute vec3 trailColor;

uniform mat3 u_equatorialToENUMatrix;
uniform float u_exposureAngle;
uniform float u_radius;
uniform float u_stereoZoom;
uniform float u_aspect;
uniform float u_trailTimeScale;
uniform vec2 u_viewportSize;
uniform float u_lineWidthPx;
uniform float u_rasterWidthPx;

varying vec3 vColor;
varying float vLineDistancePx;
varying float vTrailValid;

void trailViewFrame(
    float trailT,
    out vec3 viewDirection,
    out vec3 viewTangent
) {
    // The current transform is authoritative. Increasing RA by the elapsed
    // sidereal angle reconstructs the same fixed star at the earlier LST.
    float angle = u_exposureAngle * (1.0 - trailT);
    float cosA = cos(angle);
    float sinA = sin(angle);
    vec3 rotatedEquatorial = vec3(
        equatorialPosition.x * cosA - equatorialPosition.y * sinA,
        equatorialPosition.x * sinA + equatorialPosition.y * cosA,
        equatorialPosition.z
    );
    vec3 worldDirection = u_equatorialToENUMatrix * rotatedEquatorial;
    vec3 worldTangent = u_equatorialToENUMatrix * vec3(
        rotatedEquatorial.y,
        -rotatedEquatorial.x,
        0.0
    );
    vec3 viewPosition = (modelViewMatrix * vec4(worldDirection * u_radius, 1.0)).xyz;
    vec3 rawViewTangent = mat3(modelViewMatrix) * worldTangent * u_radius;
    viewDirection = normalize(viewPosition);
    viewTangent = rawViewTangent
        - viewDirection * dot(viewDirection, rawViewTangent);
}

vec2 stereographicNdc(vec3 viewDirection) {
    float denominator = max(1e-6, 1.0 - viewDirection.z);
    vec2 projected = (2.0 * viewDirection.xy) / denominator;
    return vec2(
        projected.x * u_stereoZoom / max(1e-6, u_aspect),
        projected.y * u_stereoZoom
    );
}

vec2 stereographicNdcTangent(vec3 viewDirection, vec3 viewTangent) {
    float denominator = max(1e-6, 1.0 - viewDirection.z);
    float denominatorSquared = denominator * denominator;
    vec2 projectedTangent = 2.0 * vec2(
        viewTangent.x * denominator + viewDirection.x * viewTangent.z,
        viewTangent.y * denominator + viewDirection.y * viewTangent.z
    ) / denominatorSquared;
    return vec2(
        projectedTangent.x * u_stereoZoom / max(1e-6, u_aspect),
        projectedTangent.y * u_stereoZoom
    );
}

void main() {
    vColor = trailColor;

    float currentT = min(1.0, position.x * u_trailTimeScale);
    vec3 currentViewDirection;
    vec3 currentViewTangent;
    trailViewFrame(currentT, currentViewDirection, currentViewTangent);
    float currentDenominator = 1.0 - currentViewDirection.z;
    vec2 currentNdc = stereographicNdc(currentViewDirection);
    vec2 currentNdcTangent = stereographicNdcTangent(
        currentViewDirection,
        currentViewTangent
    );

    vec2 viewport = max(u_viewportSize, vec2(1.0));
    vec2 tangentPx = currentNdcTangent * viewport * 0.5;
    float tangentLengthPx = length(tangentPx);
    vec2 tangentDirection = tangentPx / max(1e-6, tangentLengthPx);
    vec2 normalPx = vec2(-tangentDirection.y, tangentDirection.x);
    vec2 ribbonOffsetNdc = normalPx
        * position.y
        * u_rasterWidthPx
        / viewport;
    vLineDistancePx = position.y * u_rasterWidthPx * 0.5;
    bool invalidPoint = currentDenominator <= 1e-6
        || tangentLengthPx <= 1e-6
        || max(abs(currentNdc.x), abs(currentNdc.y)) > 3.0;
    vTrailValid = invalidPoint ? 0.0 : 1.0;

    gl_Position = invalidPoint
        ? vec4(2.0, 2.0, 2.0, 1.0)
        : vec4(currentNdc + ribbonOffsetNdc, 0.999999, 1.0);
}
`;

const TRAIL_FRAGMENT_SHADER = /* glsl */ `
uniform float u_alpha;
uniform float u_lineWidthPx;
varying vec3 vColor;
varying float vLineDistancePx;
varying float vTrailValid;

void main() {
    if (vTrailValid < 0.999) discard;
    float halfLineWidthPx = u_lineWidthPx * 0.5;
    float coverage = clamp(
        halfLineWidthPx + ${TRAIL_ANTIALIAS_RADIUS_PHYSICAL_PX.toFixed(1)} - abs(vLineDistancePx),
        0.0,
        1.0
    );
    gl_FragColor = vec4(vColor, u_alpha * coverage);
    #include <tonemapping_fragment>
    #include <colorspace_fragment>
}
`;

export class StarTrailLayerRendererImpl implements StarTrailLayerRenderer {
  private readonly rootGroup = new THREE.Group();

  private activeSessionId: string | null = null;
  private state = "idle";
  private accumulatedExposureSeconds = 0.0;
  private durationSeconds = 86_400.0;
  private lastMagnitudeLimit = 6.0;
  private startUtcMs: number | null = null;
  private currentSimUtcMs: number | null = null;

  private linesGeometry: THREE.InstancedBufferGeometry | null = null;
  private linesMaterial: THREE.ShaderMaterial | null = null;
  private linesMesh: THREE.Mesh<
    THREE.InstancedBufferGeometry,
    THREE.ShaderMaterial
  > | null = null;
  private selectedStarsCount = 0;
  private allocatedSegmentsPerStar = TRAIL_MAX_SEGMENTS;
  private visibleSegmentsPerStar = 0;
  private sourceResourceKey: string | null = null;
  private transformState: CelestialTransformState | null = null;

  private geometryBuildCount = 0;
  private geometryDisposeCount = 0;
  private cumulativeUploadBytes = 0;
  private exposureAngleRad = 0.0;
  private readonly drawingBufferSize = new THREE.Vector2(1.0, 1.0);

  constructor(
    parent: THREE.Group,
    private readonly starCatalog: StarTrailCatalogSource,
    private readonly camera: THREE.PerspectiveCamera,
    private readonly viewport: StarTrailViewport,
  ) {
    this.rootGroup.name = "starTrailsRoot";
    parent.add(this.rootGroup);
  }

  public applyDelta(_delta: SceneDelta): void {}

  public setTransformState(state: CelestialTransformState): void {
    this.transformState = state;
  }

  public getStarCount(): number {
    return this.selectedStarsCount;
  }

  public getSegmentCount(): number {
    return this.selectedStarsCount * this.visibleSegmentsPerStar;
  }

  public getGpuBytes(): number {
    return this.linesGeometry
      ? estimateTrailGpuBytes(this.selectedStarsCount, this.allocatedSegmentsPerStar)
      : 0;
  }

  public getMetrics(): StarTrailRendererMetrics {
    return {
      state: this.state,
      starCount: this.selectedStarsCount,
      segmentCount: this.getSegmentCount(),
      vertexCount: this.visibleSegmentsPerStar > 0
        ? this.selectedStarsCount * (this.visibleSegmentsPerStar + 1) * 2
        : 0,
      gpuBytes: this.getGpuBytes(),
      geometryBuildCount: this.geometryBuildCount,
      geometryDisposeCount: this.geometryDisposeCount,
      cumulativeUploadBytes: this.cumulativeUploadBytes,
      exposureAngleRad: this.exposureAngleRad,
      drawCalls: this.linesMesh ? 1 : 0,
    };
  }

  public applySnapshot(payload: StarTrailsComponentPayload): void {
    if (!payload.sessionId || payload.state === "idle") {
      this.clearSession();
      return;
    }

    const sessionChanged = this.activeSessionId !== payload.sessionId;
    const magnitudeChanged = this.lastMagnitudeLimit !== payload.magnitudeLimit;

    this.activeSessionId = payload.sessionId;
    this.state = payload.state;
    this.lastMagnitudeLimit = payload.magnitudeLimit;
    this.durationSeconds = finiteNonNegative(payload.durationSeconds, 86_400.0);
    this.accumulatedExposureSeconds = finiteNonNegative(
      payload.accumulatedExposureSeconds,
      this.accumulatedExposureSeconds,
    );
    if (payload.startUtcIso !== undefined) {
      this.startUtcMs = parseUtcMs(payload.startUtcIso);
    }

    if (sessionChanged) {
      this.sourceResourceKey = null;
      this.releaseGeometry();
      this.rebuildGeometry();
    } else if (magnitudeChanged) {
      this.rebuildGeometry();
    }

    this.updateUniforms();
    this.syncStarFieldSuppression();
  }

  public setCurrentSimulationTime(isoUtc: string): void {
    this.currentSimUtcMs = parseUtcMs(isoUtc);
  }

  public update(_timestampMs: number): void {
    if (this.state === "idle") return;

    const currentResourceKey = this.currentCatalogResourceKey();
    if (currentResourceKey !== null && currentResourceKey !== this.sourceResourceKey) {
      this.rebuildGeometry();
    }

    if (
      this.state === "running"
      && this.startUtcMs !== null
      && this.currentSimUtcMs !== null
    ) {
      this.accumulatedExposureSeconds = Math.max(
        0.0,
        Math.min(
          (this.currentSimUtcMs - this.startUtcMs) / 1000.0,
          this.durationSeconds,
        ),
      );
    }

    this.updateUniforms();
    this.syncStarFieldSuppression();
  }

  public dispose(): void {
    this.clearSession();
    this.rootGroup.removeFromParent();
  }

  private clearSession(): void {
    this.activeSessionId = null;
    this.state = "idle";
    this.accumulatedExposureSeconds = 0.0;
    this.startUtcMs = null;
    this.sourceResourceKey = null;
    this.releaseGeometry();
    this.starCatalog.setTrailSuppressed(false);
  }

  private rebuildGeometry(): void {
    const targetEntry = this.currentCatalogResource();
    if (targetEntry === undefined) return;

    this.releaseGeometry();
    this.sourceResourceKey = `${targetEntry.resourceId}@${targetEntry.version}`;
    this.allocatedSegmentsPerStar = trailSegmentCountForDuration(this.durationSeconds);

    const selectedIndices = selectTrailStarIndices(
      targetEntry.magnitudesArray,
      this.lastMagnitudeLimit,
    );
    this.selectedStarsCount = selectedIndices.length;
    if (selectedIndices.length === 0) return;

    const positions = new Float32Array(selectedIndices.length * 3);
    const colors = new Float32Array(selectedIndices.length * 3);
    const sourceColors = targetEntry.geometry.getAttribute("color")?.array as
      | Float32Array
      | undefined;

    for (let outputIndex = 0; outputIndex < selectedIndices.length; outputIndex++) {
      const catalogIndex = selectedIndices[outputIndex]!;
      const sourceOffset = catalogIndex * 3;
      const outputOffset = outputIndex * 3;
      positions[outputOffset] = targetEntry.equatorialPositions[sourceOffset]!;
      positions[outputOffset + 1] = targetEntry.equatorialPositions[sourceOffset + 1]!;
      positions[outputOffset + 2] = targetEntry.equatorialPositions[sourceOffset + 2]!;
      colors[outputOffset] = quantizeTrailLinearChannel(sourceColors?.[sourceOffset] ?? 1.0);
      colors[outputOffset + 1] = quantizeTrailLinearChannel(sourceColors?.[sourceOffset + 1] ?? 1.0);
      colors[outputOffset + 2] = quantizeTrailLinearChannel(sourceColors?.[sourceOffset + 2] ?? 1.0);
    }

    const ribbon = buildTrailRibbonGeometryData(this.allocatedSegmentsPerStar);
    this.linesGeometry = new THREE.InstancedBufferGeometry();
    this.linesGeometry.setAttribute("position", new THREE.BufferAttribute(ribbon.parameters, 3));
    this.linesGeometry.setIndex(new THREE.BufferAttribute(ribbon.indices, 1));
    this.linesGeometry.setAttribute(
      "equatorialPosition",
      new THREE.InstancedBufferAttribute(positions, 3),
    );
    this.linesGeometry.setAttribute(
      "trailColor",
      new THREE.InstancedBufferAttribute(colors, 3),
    );
    this.linesGeometry.instanceCount = selectedIndices.length;

    const transform = new THREE.Matrix3();
    if (this.transformState?.isValid) {
      transform.copy(this.transformState.equatorialToThree);
    }

    this.linesMaterial = new THREE.ShaderMaterial({
      vertexShader: TRAIL_VERTEX_SHADER,
      fragmentShader: TRAIL_FRAGMENT_SHADER,
      uniforms: {
        u_equatorialToENUMatrix: { value: transform },
        u_exposureAngle: { value: 0.0 },
        u_radius: { value: TRAIL_RADIUS },
        u_stereoZoom: { value: 1.0 },
        u_aspect: { value: 1.0 },
        u_trailTimeScale: { value: 1.0 },
        u_viewportSize: { value: this.drawingBufferSize.clone() },
        u_lineWidthPx: { value: TRAIL_LINE_WIDTH_CSS_PX },
        u_rasterWidthPx: {
          value: TRAIL_LINE_WIDTH_CSS_PX
            + 2.0 * TRAIL_ANTIALIAS_RADIUS_PHYSICAL_PX,
        },
        u_alpha: { value: TRAIL_STABLE_ALPHA },
      },
      blending: THREE.NormalBlending,
      transparent: true,
      depthTest: true,
      depthWrite: false,
      toneMapped: true,
      side: THREE.DoubleSide,
    });

    this.linesMesh = new THREE.Mesh(this.linesGeometry, this.linesMaterial);
    this.linesMesh.name = "starTrailLines";
    this.linesMesh.frustumCulled = false;
    this.linesMesh.renderOrder = 1;
    this.rootGroup.add(this.linesMesh);

    const uploadBytes = estimateTrailGpuBytes(
      this.selectedStarsCount,
      this.allocatedSegmentsPerStar,
    );
    this.geometryBuildCount++;
    this.cumulativeUploadBytes += uploadBytes;
    this.updateUniforms();
  }

  private releaseGeometry(): void {
    if (this.linesMesh === null) {
      this.selectedStarsCount = 0;
      return;
    }

    this.rootGroup.remove(this.linesMesh);
    this.linesGeometry?.dispose();
    this.linesMaterial?.dispose();
    this.linesMesh = null;
    this.linesGeometry = null;
    this.linesMaterial = null;
    this.selectedStarsCount = 0;
    this.visibleSegmentsPerStar = 0;
    this.geometryDisposeCount++;
  }

  private updateUniforms(): void {
    if (this.linesMaterial === null) return;

    this.exposureAngleRad = exposureSecondsToSiderealRadians(
      this.accumulatedExposureSeconds,
      this.durationSeconds,
    );
    const uniforms = this.linesMaterial.uniforms;
    const transform = uniform<THREE.Matrix3>(uniforms, "u_equatorialToENUMatrix").value;
    if (this.transformState?.isValid) {
      transform.copy(this.transformState.equatorialToThree);
    }
    uniform<number>(uniforms, "u_exposureAngle").value = this.exposureAngleRad;

    this.visibleSegmentsPerStar = this.accumulatedExposureSeconds > 1e-4
      ? Math.min(
        this.allocatedSegmentsPerStar,
        trailSegmentCountForDuration(this.accumulatedExposureSeconds),
      )
      : 0;
    this.linesGeometry?.setDrawRange(0, this.visibleSegmentsPerStar * 6);
    uniform<number>(uniforms, "u_trailTimeScale").value = this.visibleSegmentsPerStar > 0
      ? this.allocatedSegmentsPerStar / this.visibleSegmentsPerStar
      : 1.0;

    const aspect = Math.max(1e-6, this.camera.aspect || 1.0);
    const verticalFovRad = THREE.MathUtils.degToRad(this.camera.fov);
    const horizontalFovDeg = THREE.MathUtils.radToDeg(
      2.0 * Math.atan(Math.tan(verticalFovRad * 0.5) * aspect),
    );
    uniform<number>(uniforms, "u_stereoZoom").value = legacyStereographicZoom(horizontalFovDeg);
    uniform<number>(uniforms, "u_aspect").value = aspect;
    this.viewport.getDrawingBufferSize(this.drawingBufferSize);
    uniform<THREE.Vector2>(uniforms, "u_viewportSize").value.copy(this.drawingBufferSize);
    const pixelRatio = Math.max(1e-6, this.viewport.getPixelRatio());
    uniform<number>(uniforms, "u_lineWidthPx").value = TRAIL_LINE_WIDTH_CSS_PX * pixelRatio;
    uniform<number>(uniforms, "u_rasterWidthPx").value = TRAIL_LINE_WIDTH_CSS_PX
      * pixelRatio
      + 2.0 * TRAIL_ANTIALIAS_RADIUS_PHYSICAL_PX;
  }

  private syncStarFieldSuppression(): void {
    const trailOwnsStellarAppearance = this.state !== "idle"
      && this.accumulatedExposureSeconds > 1e-4
      && this.selectedStarsCount > 0;
    this.starCatalog.setTrailSuppressed(trailOwnsStellarAppearance);
  }

  private currentCatalogResource(): StarResourceEntry | undefined {
    const resources = this.starCatalog.getResources();
    return resources.get("stars:general")
      ?? resources.get("stars:fallback")
      ?? resources.values().next().value;
  }

  private currentCatalogResourceKey(): string | null {
    const resource = this.currentCatalogResource();
    return resource ? `${resource.resourceId}@${resource.version}` : null;
  }
}

function parseUtcMs(isoUtc: string): number | null {
  const parsed = Date.parse(isoUtc);
  return Number.isFinite(parsed) ? parsed : null;
}

function finiteNonNegative(value: number | undefined, fallback: number): number {
  return value !== undefined && Number.isFinite(value) ? Math.max(0.0, value) : fallback;
}

function uniform<T>(
  uniforms: Record<string, THREE.IUniform>,
  name: string,
): THREE.IUniform<T> {
  const value = uniforms[name];
  if (value === undefined) throw new Error(`Missing star-trail shader uniform: ${name}`);
  return value as THREE.IUniform<T>;
}
