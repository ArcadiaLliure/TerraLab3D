import * as THREE from "three";
import { CelestialTransformState } from "../view/three/CelestialTransformState";
import type { StarResourceEntry } from "../view/three/StarFieldRenderer";
import { StarTrailLayerRendererImpl } from "../view/three/layers/StarTrailLayerRendererImpl";
import {
  buildTrailRibbonGeometryData,
  estimateTrailGpuBytes,
  exposureSecondsToSiderealRadians,
  projectStereographicViewDirectionToNdc,
  quantizeTrailLinearChannel,
  selectTrailStarIndices,
  SIDEREAL_DAY_SECONDS,
  TRAIL_ANTIALIAS_RADIUS_PHYSICAL_PX,
  TRAIL_LINE_WIDTH_CSS_PX,
  TRAIL_STABLE_ALPHA,
  trailSegmentCountForDuration,
} from "../view/three/layers/starTrailMath";

let passed = 0;

function assert(condition: boolean, message: string): void {
  if (!condition) throw new Error(`FAIL: ${message}`);
  passed++;
}

function near(actual: number, expected: number, tolerance: number, message: string): void {
  assert(Math.abs(actual - expected) <= tolerance, `${message}: ${actual} != ${expected}`);
}

function makeResource(version: string, magnitudes: readonly number[]): StarResourceEntry {
  const positions = new Float32Array(magnitudes.length * 3);
  const colors = new Float32Array(magnitudes.length * 3);
  for (let index = 0; index < magnitudes.length; index++) {
    const angle = index * 0.4;
    positions[index * 3] = Math.cos(angle);
    positions[index * 3 + 1] = Math.sin(angle);
    colors[index * 3] = 1.0;
    colors[index * 3 + 1] = 0.5;
    colors[index * 3 + 2] = 0.25;
  }
  const geometry = new THREE.BufferGeometry();
  geometry.setAttribute("position", new THREE.BufferAttribute(positions, 3));
  geometry.setAttribute("color", new THREE.BufferAttribute(colors, 3));
  const material = new THREE.ShaderMaterial();
  const points = new THREE.Points(geometry, material);
  return {
    resourceId: "stars:general",
    version,
    role: "general",
    starCount: magnitudes.length,
    points,
    geometry,
    material,
    catalogIndices: Uint32Array.from(magnitudes.map((_magnitude, index) => index)),
    magnitudesArray: Float32Array.from(magnitudes),
    equatorialPositions: positions,
  };
}

const selected = selectTrailStarIndices(Float32Array.from([6.0, 2.0, Number.NaN, 5.0, 2.0]), 6.0, 3);
assert(Array.from(selected).join(",") === "1,4,3", "selection is inclusive, finite and brightest-first");
assert(selectTrailStarIndices(Float32Array.from([1.0]), Number.NaN).length === 0, "invalid magnitude limit selects nothing");

near(exposureSecondsToSiderealRadians(SIDEREAL_DAY_SECONDS), Math.PI * 2.0, 1e-12, "one sidereal day is one turn");
near(exposureSecondsToSiderealRadians(7_200.0, 3_600.0), exposureSecondsToSiderealRadians(3_600.0), 1e-12, "exposure angle is duration-clamped");
assert(trailSegmentCountForDuration(3_600.0) === 12, "short exposures retain minimum tessellation");
assert(trailSegmentCountForDuration(21_600.0) === 52, "six-hour exposure follows reference density");
assert(trailSegmentCountForDuration(86_400.0) === 96, "full-day exposure matches the reference quality cap");

const ribbon = buildTrailRibbonGeometryData(2);
assert(ribbon.parameters.length === 18, "two segments share three pairs of 3D-safe ribbon vertices");
assert(ribbon.indices.length === 12, "two segments produce four ribbon triangles");
near(ribbon.parameters[0]!, 0.0, 1e-7, "first segment starts at zero");
near(ribbon.parameters[1]!, -1.0, 1e-7, "first vertex is the left ribbon edge");
near(ribbon.parameters[2]!, 0.0, 1e-7, "ribbon position keeps a finite third component");
near(ribbon.parameters[3]!, 0.0, 1e-7, "second vertex shares the first trail sample");
near(ribbon.parameters[4]!, 1.0, 1e-7, "second vertex is the right ribbon edge");
near(ribbon.parameters[6]!, 0.5, 1e-7, "adjacent segments share the middle trail sample");
near(ribbon.parameters[12]!, 1.0, 1e-7, "final vertex pair reaches the full exposure");
assert(
  Array.from(ribbon.indices.slice(0, 6)).join(",") === "0,2,1,2,3,1",
  "ribbon segment uses a stable indexed quad winding",
);

const center = projectStereographicViewDirectionToNdc([0.0, 0.0, -1.0], 100.0, 2.0);
assert(center !== null, "projection center is valid");
near(center![0], 0.0, 1e-12, "projection center x");
near(center![1], 0.0, 1e-12, "projection center y");
const eastHorizon = projectStereographicViewDirectionToNdc([1.0, 0.0, 0.0], 100.0, 2.0);
near(eastHorizon![0], 1.0, 1e-12, "projection matches TerraLab scale at nominal zoom");
assert(projectStereographicViewDirectionToNdc([0.0, 0.0, 1.0], 100.0, 2.0) === null, "antipode is clipped");

near(quantizeTrailLinearChannel(1.0), 1.0, 1e-12, "white remains white after reference color bucketing");
assert(quantizeTrailLinearChannel(0.0) > 0.0, "reference color bucket reproduces TerraLab's lowest midpoint");
assert(
  estimateTrailGpuBytes(6_793, 96) === 166_512,
  "reference catalog resident-byte estimate is exact",
);
assert(
  estimateTrailGpuBytes(6_793, 96) * 250 < 6_793 * 128 * 2 * 28,
  "instancing removes more than 250x of the former duplicated vertex payload",
);

const parent = new THREE.Group();
const camera = new THREE.PerspectiveCamera(60.0, 16.0 / 9.0, 0.01, 2_000_000.0);
let resource = makeResource("v1", [6.0, 2.0, 7.0]);
const resources = new Map<string, StarResourceEntry>([[resource.resourceId, resource]]);
let starFieldSuppressed = false;
const catalog = {
  getResources: () => resources,
  setTrailSuppressed: (suppressed: boolean) => {
    starFieldSuppressed = suppressed;
  },
};
const viewport = {
  getDrawingBufferSize: (target: THREE.Vector2) => target.set(1920.0, 1080.0),
  getPixelRatio: () => 1.0,
};
const renderer = new StarTrailLayerRendererImpl(parent, catalog, camera, viewport);
const transform = new CelestialTransformState();
transform.update(1, [1, 0, 0, 0, 1, 0, 0, 0, 1]);
renderer.setTransformState(transform);

renderer.applySnapshot({
  sessionId: "session-a",
  sessionVersion: 1,
  state: "running",
  playbackRate: 1.0,
  magnitudeLimit: 6.0,
  startUtcIso: "2026-08-14T22:00:00Z",
  accumulatedExposureSeconds: 3_600.0,
  durationSeconds: 21_600.0,
});
renderer.setCurrentSimulationTime("2026-08-14T23:00:00Z");
renderer.update(1_000.0);

let metrics = renderer.getMetrics();
assert(metrics.starCount === 2, "renderer applies deterministic magnitude selection");
assert(metrics.segmentCount === 2 * 12, "renderer reports only the visible one-hour segments");
assert(metrics.gpuBytes === estimateTrailGpuBytes(2, 52), "renderer reports resident instanced bytes");
assert(metrics.geometryBuildCount === 1, "session allocates geometry once");
assert(metrics.drawCalls === 1, "all stellar trails share one draw call");
near(metrics.exposureAngleRad, exposureSecondsToSiderealRadians(3_600.0), 1e-12, "renderer uses sidereal exposure rate");
assert(starFieldSuppressed, "point-star field is suppressed once trails are visible");

const initialLines = parent.getObjectByName("starTrailLines") as THREE.Mesh;
const initialGeometry = initialLines.geometry as THREE.InstancedBufferGeometry;
const initialMaterial = initialLines.material as THREE.ShaderMaterial;
assert(initialLines instanceof THREE.Mesh, "trails use geometric ribbons instead of implementation-defined GL lines");
assert(initialMaterial instanceof THREE.ShaderMaterial, "trail material is shader-backed");
assert(initialMaterial.blending === THREE.NormalBlending, "trails use SourceOver-equivalent blending");
assert(!initialMaterial.alphaToCoverage, "trails avoid stippled alpha-to-coverage tearing");
near((initialMaterial.uniforms.u_alpha?.value as number), TRAIL_STABLE_ALPHA, 1e-12, "trail alpha matches stable TerraLab renderer");
near((initialMaterial.uniforms.u_lineWidthPx?.value as number), TRAIL_LINE_WIDTH_CSS_PX, 1e-12, "trail width matches TerraLab's one-pixel cosmetic pen without reducing brightness");
near(
  (initialMaterial.uniforms.u_rasterWidthPx?.value as number),
  TRAIL_LINE_WIDTH_CSS_PX + 2.0 * TRAIL_ANTIALIAS_RADIUS_PHYSICAL_PX,
  1e-12,
  "trail raster span contains a transparent analytic-antialias fringe",
);
assert(initialGeometry.instanceCount === 2, "one GPU instance is allocated per selected star");
assert(initialGeometry.getAttribute("position").count === 106, "adjacent segments share their ribbon vertex pair");
assert(initialGeometry.getAttribute("position").itemSize === 3, "ribbon positions remain valid Three.js geometry coordinates");
assert(initialGeometry.getIndex()?.count === 312, "shared ribbon layout has six indices per segment");
assert(initialGeometry.drawRange.count === 72, "indexed draw range grows without reallocating the shared layout");
assert(initialGeometry.getAttribute("equatorialPosition").count === 2, "equatorial positions are not duplicated per segment");

renderer.applySnapshot({
  sessionId: "session-a",
  sessionVersion: 2,
  state: "paused",
  playbackRate: 1.0,
  magnitudeLimit: 6.0,
  startUtcIso: "2026-08-14T22:00:00Z",
  accumulatedExposureSeconds: 3_600.0,
  durationSeconds: 21_600.0,
});
renderer.update(2_000.0);
assert(renderer.getMetrics().geometryBuildCount === 1, "pause does not rebuild geometry");
assert(parent.getObjectByName("starTrailLines") === initialLines, "pause retains the same GPU object");

renderer.applySnapshot({
  sessionId: "session-a",
  sessionVersion: 3,
  state: "running",
  playbackRate: 1.0,
  magnitudeLimit: 6.0,
  startUtcIso: "2026-08-14T22:00:00Z",
  accumulatedExposureSeconds: 3_600.0,
  durationSeconds: 21_600.0,
});
renderer.update(3_000.0);
assert(renderer.getMetrics().geometryBuildCount === 1, "resume does not rebuild geometry");

renderer.applySnapshot({
  sessionId: "session-a",
  sessionVersion: 4,
  state: "running",
  playbackRate: 1.0,
  magnitudeLimit: 7.0,
  startUtcIso: "2026-08-14T22:00:00Z",
  accumulatedExposureSeconds: 3_600.0,
  durationSeconds: 21_600.0,
});
assert(renderer.getMetrics().starCount === 3, "magnitude change updates selected catalog rows");
assert(renderer.getMetrics().geometryBuildCount === 2, "magnitude change performs one justified rebuild");

resource = makeResource("v2", [1.0, 2.0, 3.0, 4.0]);
resources.set(resource.resourceId, resource);
renderer.update(4_000.0);
metrics = renderer.getMetrics();
assert(metrics.starCount === 4, "new catalog version replaces trail instances");
assert(metrics.geometryBuildCount === 3, "catalog version change performs one rebuild");

const buildCountBeforeUniformUpdates = metrics.geometryBuildCount;
renderer.update(5_000.0);
camera.fov = 75.0;
renderer.update(6_000.0);
assert(renderer.getMetrics().geometryBuildCount === buildCountBeforeUniformUpdates, "growth and camera frames update uniforms without allocations");

renderer.setCurrentSimulationTime("2026-08-15T04:00:00Z");
renderer.update(7_000.0);
assert(renderer.getMetrics().segmentCount === 4 * 52, "draw range reaches the requested six-hour quality without reallocating");
assert(renderer.getMetrics().geometryBuildCount === buildCountBeforeUniformUpdates, "draw-range growth retains the geometry");

renderer.applySnapshot({
  sessionId: "session-a",
  sessionVersion: 5,
  state: "stopped",
  playbackRate: 1.0,
  magnitudeLimit: 7.0,
  startUtcIso: "2026-08-14T22:00:00Z",
  accumulatedExposureSeconds: 21_600.0,
  durationSeconds: 21_600.0,
});
assert(renderer.getMetrics().drawCalls === 1, "stop retains the completed trail image");
assert(renderer.getMetrics().geometryBuildCount === buildCountBeforeUniformUpdates, "stop does not rebuild geometry");
assert(starFieldSuppressed, "stop keeps point stars suppressed behind retained trails");

renderer.applySnapshot({
  sessionId: "session-a",
  sessionVersion: 6,
  state: "completed",
  playbackRate: 1.0,
  magnitudeLimit: 7.0,
  startUtcIso: "2026-08-14T22:00:00Z",
  accumulatedExposureSeconds: 21_600.0,
  durationSeconds: 21_600.0,
});
assert(renderer.getMetrics().geometryBuildCount === buildCountBeforeUniformUpdates, "completion does not rebuild geometry");

const completedLines = parent.getObjectByName("starTrailLines");
renderer.applySnapshot({
  sessionId: "session-b",
  sessionVersion: 1,
  state: "running",
  playbackRate: 1.0,
  magnitudeLimit: 7.0,
  startUtcIso: "2026-08-15T04:00:00Z",
  accumulatedExposureSeconds: 60.0,
  durationSeconds: 21_600.0,
});
assert(renderer.getMetrics().geometryBuildCount === buildCountBeforeUniformUpdates + 1, "a new session performs exactly one rebuild");
assert(parent.getObjectByName("starTrailLines") !== completedLines, "a new session replaces the retained trail object");

renderer.applySnapshot({
  sessionId: "",
  sessionVersion: 0,
  state: "idle",
  playbackRate: 1.0,
  magnitudeLimit: 6.0,
  accumulatedExposureSeconds: 0.0,
  durationSeconds: 86_400.0,
});
assert(renderer.getMetrics().drawCalls === 0, "clear releases the trail draw object");
assert(!starFieldSuppressed, "clear restores the user's point-star visibility policy");
renderer.dispose();

console.log(`Star trail tests: ${passed} passed, 0 failed`);
