import * as THREE from "three";

import { CelestialSelectionController } from "../application/CelestialSelectionController";
import type { HorizonProfileMetadata, HorizonQuality } from "../contracts/horizon_contracts";
import { AtmosphereRenderer } from "../view/three/AtmosphereRenderer";
import { CelestialTransformState } from "../view/three/CelestialTransformState";
import { HorizonOcclusionState } from "../view/three/HorizonOcclusionState";
import type { StarResourceEntry } from "../view/three/StarFieldRenderer";
import { HorizonLayerRenderer } from "../view/three/layers/HorizonLayerRenderer";
import { DeepSkyPickProvider } from "../view/three/picking/DeepSkyPickProvider";
import { StarPickProvider } from "../view/three/picking/StarPickProvider";
import { STAR_VERTEX_SHADER } from "../view/three/shaders/starShader";

let passed = 0;
let failed = 0;

function assert(condition: boolean, message: string): void {
  if (condition) passed++;
  else {
    failed++;
    console.error(`FAIL: ${message}`);
  }
}

function near(actual: number, expected: number, tolerance: number, message: string): void {
  assert(Math.abs(actual - expected) <= tolerance, `${message}: ${actual} vs ${expected}`);
}

const state = new HorizonOcclusionState(64);
const ridge = new Float32Array(360);
ridge[90] = 20;
state.applyBinaryResource(metadata(1, "REAL"), payload(ridge));
assert(state.hasDemBackedProfile, "REAL profile is recognized as DEM-backed terrain authority");

assert(state.isOccludedAzimuthAltitude(90, 10), "star/NGC center at az90 alt10 is hidden");
assert(!state.isOccludedAzimuthAltitude(90, 30), "star/NGC center at az90 alt30 is visible");
assert(state.isDiscFullyOccluded(90, 10, 0.25), "small planet below ridge is fully hidden");
assert(!state.isDiscFullyOccluded(90, 19, 2), "partially emerging solar/lunar disc remains logical-visible");

const seam = new Float32Array(360);
seam[359] = 15;
seam[0] = 15;
seam[1] = 15;
state.applyBinaryResource(metadata(2, "REAL"), payload(seam));
near(state.horizonElevationAtAzimuth(359.5), 15, 1e-6, "359/0 circular interpolation");
near(state.horizonElevationAtAzimuth(0.5), 15, 1e-6, "0/1 circular interpolation");
assert(state.active.textureWidth === 64 && state.active.textureHeight === 6, "2D GPU packing respects maxTextureSize");
const highPrecisionState = new HorizonOcclusionState(4096);
const highPrecision = new Float32Array(72_000);
highPrecisionState.applyBinaryResource(
  metadata(1, "REAL", 72_000, 0.005),
  payload(highPrecision),
);
assert(
  highPrecisionState.active.textureWidth === 4096
    && highPrecisionState.active.textureHeight === 18,
  "0.005-degree profile keeps all 72k samples in a bounded 2D texture",
);
assert(highPrecisionState.active.metadata.byteLength === 936_000, "0.005-degree binary size is 936000 bytes");
highPrecisionState.dispose();

const parent = new THREE.Group();
const curtain = new HorizonLayerRenderer(parent, state);
assert(curtain.root.children.length === 1, "horizon owns exactly one active mesh");
const atmosphere = new AtmosphereRenderer(parent);
const atmosphereMesh = parent.getObjectByName("atmosphere") as THREE.Mesh;
const curtainMesh = curtain.root.getObjectByName("horizonNoDemFog") as THREE.Mesh;
assert(
  atmosphereMesh.renderOrder < curtainMesh.renderOrder,
  "atmosphere background renders before the DEM horizon curtain",
);
assert(
  atmosphereMesh.material instanceof THREE.ShaderMaterial
    && !atmosphereMesh.material.depthWrite
    && curtainMesh.material instanceof THREE.MeshBasicMaterial
    && !curtainMesh.material.depthWrite
    && curtainMesh.material.transparent
    && curtainMesh.material.colorWrite,
  "missing DEM uses transparent 0-degree fog instead of a black depth curtain",
);
assert(
  !curtain.root.visible,
  "a fully covered real DEM profile needs no fog layer",
);
const partialDemState = new HorizonOcclusionState(64);
const partialDemParent = new THREE.Group();
const partialDemCurtain = new HorizonLayerRenderer(partialDemParent, partialDemState);
const partialValidMask = new Uint8Array(360).fill(1);
partialValidMask[180] = 0;
partialDemState.applyBinaryResource(
  metadata(1, "PARTIAL_DEM"),
  payload(new Float32Array(360), partialValidMask),
);
assert(
  !partialDemCurtain.root.visible,
  "a real partial DEM profile must not become a full-screen fog curtain",
);
partialDemCurtain.dispose();
partialDemState.dispose();
const buildsBeforeToggle = curtain.metrics().geometryBuildCount;
state.setEnabled(false);
assert(!curtain.root.visible, "disabling horizon hides the persistent curtain");
state.setEnabled(true);
assert(!curtain.root.visible, "a DEM-backed profile does not restore the fallback curtain");
assert(
  curtain.metrics().geometryBuildCount === buildsBeforeToggle,
  "visibility toggles do not rebuild the persistent fog geometry",
);
const firstTexture = state.active.texture;
let disposedTextures = 0;
firstTexture.addEventListener("dispose", () => disposedTextures++);
const fallback = new Float32Array(360);
state.applyBinaryResource(metadata(3, "FLAT_FALLBACK"), payload(fallback));
assert(!state.hasDemBackedProfile, "flat fallback is not presented as DEM-backed terrain");
assert(
  curtainMesh.material instanceof THREE.MeshBasicMaterial
    && curtainMesh.material.transparent
    && curtainMesh.material.colorWrite,
  "the no-DEM fallback remains a visible transparent fog layer",
);
assert(curtain.root.visible, "the fallback silhouette is restored only without a DEM");
assert(disposedTextures === 1, "atomic texture swap disposes v2");
assert(curtain.root.children.length === 1, "atomic geometry swap retains one mesh");

const transform = new CelestialTransformState();
transform.update(1, [1, 0, 0, 0, 1, 0, 0, 0, 1]);
const camera = new THREE.PerspectiveCamera(60, 1000 / 600, 0.01, 2_000_000);
const hiddenDirection = direction(90, 10);
camera.lookAt(hiddenDirection);
camera.updateProjectionMatrix();
camera.updateMatrixWorld(true);
const geometry = new THREE.BufferGeometry();
const material = new THREE.ShaderMaterial();
const entry: StarResourceEntry = {
  resourceId: "ridge-stars",
  version: "1",
  role: "general",
  starCount: 1,
  points: new THREE.Points(geometry, material),
  geometry,
  material,
  catalogIndices: new Uint32Array([0]),
  magnitudesArray: new Float32Array([0]),
  equatorialPositions: new Float32Array(hiddenDirection.toArray()),
};
const resources = new Map([[entry.resourceId, entry]]);
const renderer = {
  domElement: { getBoundingClientRect: () => ({ left: 0, top: 0, width: 1000, height: 600 }) },
  getPixelRatio: () => 1,
} as unknown as THREE.WebGLRenderer;
const picker = new StarPickProvider({
  camera,
  transformState: transform,
  renderer,
  worldRoot: new THREE.Group(),
  getStarResources: () => resources,
  getMagnitudeLimit: () => 8,
  getSkyVisibilityState: () => null,
  getPointScale: () => 1,
  isStarLayerVisible: () => true,
  horizonOcclusionState: state,
});

state.applyBinaryResource(metadata(4, "REAL"), payload(ridge));
assert(picker.pick(500, 300) === null, "hidden star cannot be picked");
state.applyBinaryResource(metadata(5, "REAL"), payload(fallback));
assert(picker.pick(500, 300)?.kind === "star", "same star becomes pickable above active profile");

state.applyBinaryResource(metadata(6, "REAL"), payload(ridge));
const deepSkyFixture = deepSkyPayload(hiddenDirection);
const deepSkyPicker = new DeepSkyPickProvider({
  camera,
  transformState: transform,
  renderer,
  deepSkyRenderer: {
    visible: true,
    metadata: deepSkyFixture.metadata,
    payloadBuffer: deepSkyFixture.buffer,
    catalogIndexToBufferIndex: new Map([[7, 0]]),
  } as never,
  getSkyVisibilityState: () => null,
  isDeepSkyLayerVisible: () => true,
  horizonOcclusionState: state,
});
assert(deepSkyPicker.pick(500, 300) === null, "hidden NGC object cannot be picked");

const selection = new CelestialSelectionController();
selection.select({
  kind: "star",
  resourceId: "ridge-stars",
  resourceVersion: "1",
  catalogIndex: 0,
}, "pick");
state.applyBinaryResource(metadata(7, "REAL"), payload(ridge));
assert(selection.getState().selectedTarget?.kind === "star", "selection persists after horizon swap");

assert(STAR_VERTEX_SHADER.includes("horizonElevationAtDirection"), "Gaia shader consumes shared horizon helper");
assert(!STAR_VERTEX_SHADER.includes("u_cameraHeight"), "camera height is not a scientific horizon authority");
assert(!STAR_VERTEX_SHADER.includes("dip_angle"), "flat dip authority was removed");
assert(!STAR_VERTEX_SHADER.includes("abs(h"), "negative-altitude abs regression was removed");
assert(state.isOccludedAzimuthAltitude(90, -20), "alt=-20 star cannot reappear through abs()");
for (let index = 0; index < 10_000; index++) {
  state.horizonElevationAtAzimuth(index * 0.037);
}
console.log("Horizon frontend metrics:", JSON.stringify({
  ...state.metrics(),
  ...curtain.metrics(),
}));

picker.dispose();
deepSkyPicker.dispose();
selection.dispose();
geometry.dispose();
material.dispose();
atmosphere.dispose();
curtain.dispose();
state.dispose();
assert(curtain.metrics().activeMeshCount === 0, "horizon mesh is released");
assert(state.metrics().activeTextureCount === 0, "horizon texture is released");

console.log(`Horizon Step 15 tests: ${passed} passed, ${failed} failed`);
if (failed > 0) (globalThis as { process?: { exit(code: number): void } }).process?.exit(1);

function direction(azimuthDeg: number, altitudeDeg: number): THREE.Vector3 {
  const az = THREE.MathUtils.degToRad(azimuthDeg);
  const alt = THREE.MathUtils.degToRad(altitudeDeg);
  const horizontal = Math.cos(alt);
  return new THREE.Vector3(
    Math.sin(az) * horizontal,
    Math.sin(alt),
    -Math.cos(az) * horizontal,
  );
}

function metadata(
  version: number,
  quality: HorizonQuality,
  count = 360,
  angularStepDeg = 1,
): HorizonProfileMetadata {
  return {
    role: "horizon_profile",
    resourceId: "earth.horizon.profile",
    version,
    contentKey: `fixture-${version}`,
    sourceIds: quality === "FLAT_FALLBACK" ? [] : ["fixture"],
    sourceFingerprint: "fixture-v1",
    observerGeneration: 1,
    latitudeDeg: 0,
    longitudeDeg: 0,
    terrainElevationM: quality === "FLAT_FALLBACK" ? null : 100,
    eyeElevationM: quality === "FLAT_FALLBACK" ? null : 102,
    visibleRadiusM: 150_000,
    azimuthStartDeg: 0,
    angularStepDeg,
    sampleCount: count,
    quality,
    resolvedFraction: 1,
    kernelVersion: "fixture-v1",
    byteLength: count * 13,
    bufferLayout: {
      horizonElevationDeg: { offset: 0, length: count * 4, dtype: "float32" },
      occluderDistanceM: { offset: count * 4, length: count * 4, dtype: "float32" },
      occluderHeightM: { offset: count * 8, length: count * 4, dtype: "float32" },
      validMask: { offset: count * 12, length: count, dtype: "uint8" },
    },
  };
}

function payload(horizon: Float32Array, validMask?: Uint8Array): ArrayBuffer {
  const count = horizon.length;
  const buffer = new ArrayBuffer(count * 13);
  new Float32Array(buffer, 0, count).set(horizon);
  new Float32Array(buffer, count * 4, count).fill(1_000);
  new Float32Array(buffer, count * 8, count).fill(100);
  const destinationMask = new Uint8Array(buffer, count * 12, count);
  destinationMask.set(validMask ?? new Uint8Array(count).fill(1));
  return buffer;
}

function deepSkyPayload(eqDirection: THREE.Vector3): { metadata: any; buffer: ArrayBuffer } {
  const buffer = new ArrayBuffer(40);
  new Float32Array(buffer, 0, 3).set(eqDirection.toArray());
  new Float32Array(buffer, 12, 5).set([10, 8, 0, 2, 20]);
  new Uint32Array(buffer, 32, 2).set([0, 7]);
  return {
    buffer,
    metadata: {
      resourceId: "ngc-fixture",
      version: "1",
      renderableCount: 1,
      objectLabels: ["NGC fixture"],
      bufferLayout: {
        equatorialDirections: { offset: 0 },
        majorAxisArcmin: { offset: 12 },
        minorAxisArcmin: { offset: 16 },
        positionAngleDeg: { offset: 20 },
        magnitude: { offset: 24 },
        surfaceBrightness: { offset: 28 },
        familyCode: { offset: 32 },
        catalogIndex: { offset: 36 },
      },
    },
  };
}
