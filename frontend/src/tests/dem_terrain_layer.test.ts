import * as THREE from "three";

import { DemTerrainLayerRenderer } from "../view/three/layers/DemTerrainLayerRenderer";
import { TechnicalTerrainSampler } from "../view/three/terrain/TechnicalTerrainSampler";

let passed = 0;
let failed = 0;

function assert(condition: boolean, message: string): void {
  if (condition) passed++;
  else {
    failed++;
    console.error(`FAIL: ${message}`);
  }
}

const parent = new THREE.Group();
const renderer = new DemTerrainLayerRenderer(parent);
const fixture = payload();
assert(renderer.applyBinaryResource(fixture.metadata, fixture.buffer), "DEM mesh binary is accepted");
const mesh = renderer.root.getObjectByName("demTerrainMeshV3") as THREE.Mesh;
assert(mesh instanceof THREE.Mesh, "visible terrain is a world mesh, not a horizon curtain");
assert(mesh.renderOrder > -1_000, "world terrain renders after the celestial horizon depth mask");
assert(mesh.geometry.getAttribute("terrainClassId").itemSize === 1, "semantic class identity is retained separately");
assert(mesh.geometry.getAttribute("terrainSourceId").itemSize === 1, "surface source identity is retained separately");
assert(renderer.metrics().triangleCount === 2, "indexed valid DEM cell forms two triangles");
assert(renderer.getNavigationMesh() === mesh, "the visible DEM mesh is exposed for navigation collision");
assert(
  renderer.getNavigationSampling()?.polarAzimuthStepDeg === 90,
  "DEM topology metadata is retained for direct navigation sampling",
);

const streamed = payload();
streamed.metadata = {
  ...streamed.metadata,
  role: "terrain_stream_chunk",
  resourceId: "earth.terrain.stream",
  version: 1,
  contentKey: "stream-fixture",
  navigationSampling: {
    ...streamed.metadata.navigationSampling,
    centerEastM: 2_000,
    centerNorthM: -500,
  },
};
assert(renderer.applyBinaryResource(streamed.metadata, streamed.buffer), "streamed detail DEM is accepted");
assert(
  renderer.root.getObjectByName("demTerrainStreamChunk") instanceof THREE.Mesh,
  "detail chunk is a second resident GPU mesh rather than a horizon profile",
);
assert(renderer.metrics().activeMeshCount === 2, "base mesh and moving detail chunk coexist");
assert(
  renderer.getStreamingNavigationSampling()?.centerEastM === 2_000,
  "streamed chunk keeps its global ENU centre for collision",
);

const secondStreamed = payload();
secondStreamed.metadata = {
  ...secondStreamed.metadata,
  role: "terrain_stream_chunk",
  resourceId: "earth.terrain.stream",
  version: 2,
  contentKey: "stream-fixture-2",
  navigationSampling: {
    ...secondStreamed.metadata.navigationSampling,
    centerEastM: 20_000,
    centerNorthM: 10_000,
  },
};
assert(
  renderer.applyBinaryResource(secondStreamed.metadata, secondStreamed.buffer),
  "a second streamed DEM chunk is accepted without replacing the first",
);
assert(renderer.metrics().activeMeshCount === 3, "base and two streamed DEM chunks coexist in GPU memory");
assert(
  renderer.getStreamingNavigationLayers().map((layer) => layer.contentKey).join(",")
    === "stream-fixture,stream-fixture-2",
  "all retained chunks are exposed to layered navigation in age order",
);

const boundedRenderer = new DemTerrainLayerRenderer(
  new THREE.Group(),
  { maxMeshCount: 2, maxGpuBytes: 1024 * 1024 },
);
let evictedMesh: THREE.Mesh | null = null;
for (let index = 0; index < 3; index++) {
  const chunk = payload();
  chunk.metadata = {
    ...chunk.metadata,
    role: "terrain_stream_chunk",
    version: index + 1,
    contentKey: `bounded-${index}`,
  };
  assert(boundedRenderer.applyBinaryResource(chunk.metadata, chunk.buffer), `bounded chunk ${index} is accepted`);
  if (index === 0) evictedMesh = boundedRenderer.getStreamingNavigationMesh();
}
assert(boundedRenderer.metrics().activeMeshCount === 2, "streaming GPU cache obeys its mesh budget");
assert(evictedMesh?.parent === null, "the oldest evicted streaming geometry leaves the scene");
boundedRenderer.dispose();

const sampler = new TechnicalTerrainSampler();
(mesh.material as THREE.MeshStandardMaterial).side = THREE.DoubleSide;
sampler.setTerrainMesh(mesh);
const deepProbe = sampler.sampleGround(2, 2, -5_000);
assert(deepProbe?.valid === true, "terrain probe remains valid even when the camera is below the mesh");

const structured = structuredDemMesh();
const directSampler = new TechnicalTerrainSampler();
directSampler.setTerrainMesh(structured.mesh, structured.sampling);
assert(
  directSampler.sampleGround(0, 0)?.heightM === 7,
  "navigation samples the resident near DEM grid without a triangle raycast",
);
assert(
  directSampler.sampleGround(3, 0)?.heightM === 7,
  "navigation samples the resident polar DEM rings without a triangle raycast",
);

const boundaryRenderer = new DemTerrainLayerRenderer(new THREE.Group());
const boundaryFixture = coverageBoundaryPayload();
assert(
  boundaryRenderer.applyBinaryResource(boundaryFixture.metadata, boundaryFixture.buffer),
  "structured DEM coverage boundary is accepted",
);
const coverageFog = boundaryRenderer.root.getObjectByName("demCoverageFogBoundary") as THREE.Mesh;
assert(
  coverageFog instanceof THREE.Mesh,
  "the DEM coverage edge gets a world-space fog boundary",
);
boundaryRenderer.updateCoverageFogTop(1_000);
const fogPositions = coverageFog.geometry.getAttribute("position") as THREE.BufferAttribute;
assert(
  Array.from(fogPositions.array as Float32Array).some((value) => value === 1_000),
  "the retained fog boundary follows the observer 0-degree height",
);
boundaryRenderer.dispose();

assert(renderer.applyBinaryResource({ ...fixture.metadata, cleared: true, version: 2 }, new ArrayBuffer(0)), "clear resource is accepted");
assert(renderer.metrics().activeMeshCount === 0, "base replacement clears its stale streamed detail too");
renderer.dispose();

console.log(`DEM terrain layer tests: ${passed} passed, ${failed} failed`);
if (failed > 0) (globalThis as { process?: { exit(code: number): void } }).process?.exit(1);

function payload(): { metadata: any; buffer: ArrayBuffer } {
  const positions = new Float32Array([
    0, 0, 0,
    10, 0, 0,
    0, 0, -10,
    10, 1, -10,
  ]);
  const normals = new Float32Array([
    0, 1, 0,
    0, 1, 0,
    0, 1, 0,
    0, 1, 0,
  ]);
  const colors = new Uint8Array([
    80, 100, 60, 255,
    80, 100, 60, 255,
    80, 100, 60, 255,
    80, 100, 60, 255,
  ]);
  const classes = new Uint16Array([62, 82, 102, 162]);
  const sources = new Int16Array([1, 1, 1, 1]);
  const indices = new Uint32Array([0, 2, 1, 1, 2, 3]);
  const normalOffset = positions.byteLength;
  const colorOffset = normalOffset + normals.byteLength;
  const classOffset = colorOffset + colors.byteLength;
  const sourceOffset = classOffset + classes.byteLength;
  const indexOffset = sourceOffset + sources.byteLength;
  const buffer = new ArrayBuffer(indexOffset + indices.byteLength);
  new Float32Array(buffer, 0, positions.length).set(positions);
  new Float32Array(buffer, normalOffset, normals.length).set(normals);
  new Uint8Array(buffer, colorOffset, colors.length).set(colors);
  new Uint16Array(buffer, classOffset, classes.length).set(classes);
  new Int16Array(buffer, sourceOffset, sources.length).set(sources);
  new Uint32Array(buffer, indexOffset, indices.length).set(indices);
  return {
    buffer,
    metadata: {
      role: "terrain_mesh",
      resourceId: "earth.terrain.mesh",
      version: 1,
      contentKey: "fixture",
      vertexCount: 4,
      indexCount: 6,
      navigationSampling: {
        nearAxisM: [-1, 1],
        polarDistanceM: [2, 4],
        polarAzimuthStepDeg: 90,
      },
      bufferLayout: {
        position: { offset: 0, length: positions.byteLength },
        normal: { offset: normalOffset, length: normals.byteLength },
        color: { offset: colorOffset, length: colors.byteLength },
        classId: { offset: classOffset, length: classes.byteLength },
        sourceId: { offset: sourceOffset, length: sources.byteLength },
        index: { offset: indexOffset, length: indices.byteLength },
      },
    },
  };
}

function structuredDemMesh(): {
  mesh: THREE.Mesh;
  sampling: {
    nearAxisM: Float32Array;
    polarDistanceM: Float32Array;
    polarAzimuthStepDeg: number;
  };
} {
  const positions = new Float32Array([
    -1, 7, 1, 1, 7, 1, -1, 7, -1, 1, 7, -1,
    0, 7, -2, 2, 7, 0, 0, 7, 2, -2, 7, 0,
    0, 7, -4, 4, 7, 0, 0, 7, 4, -4, 7, 0,
  ]);
  const indices: number[] = [0, 2, 1, 1, 2, 3];
  for (let azimuth = 0; azimuth < 4; azimuth++) {
    const next = (azimuth + 1) % 4;
    const inner = 4 + azimuth;
    const outer = 8 + azimuth;
    indices.push(inner, 4 + next, outer, 4 + next, 8 + next, outer);
  }
  const geometry = new THREE.BufferGeometry();
  geometry.setAttribute("position", new THREE.BufferAttribute(positions, 3));
  geometry.setAttribute("normal", new THREE.BufferAttribute(new Float32Array(positions.length).map((_, index) => index % 3 === 1 ? 1 : 0), 3));
  geometry.setIndex(indices);
  return {
    mesh: new THREE.Mesh(geometry, new THREE.MeshStandardMaterial()),
    sampling: {
      nearAxisM: new Float32Array([-1, 1]),
      polarDistanceM: new Float32Array([2, 4]),
      polarAzimuthStepDeg: 90,
    },
  };
}

function coverageBoundaryPayload(): { metadata: any; buffer: ArrayBuffer } {
  const structured = structuredDemMesh();
  const geometry = structured.mesh.geometry;
  const positions = new Float32Array((geometry.getAttribute("position") as THREE.BufferAttribute).array as Float32Array);
  const normals = new Float32Array((geometry.getAttribute("normal") as THREE.BufferAttribute).array as Float32Array);
  const colors = new Uint8Array(positions.length / 3 * 4).fill(180);
  for (let offset = 3; offset < colors.length; offset += 4) colors[offset] = 255;
  const classes = new Uint16Array(positions.length / 3);
  const sources = new Int16Array(positions.length / 3);
  const indices = new Uint32Array(geometry.getIndex()!.array as Uint32Array);
  const normalOffset = positions.byteLength;
  const colorOffset = normalOffset + normals.byteLength;
  const classOffset = colorOffset + colors.byteLength;
  const sourceOffset = classOffset + classes.byteLength;
  const indexOffset = sourceOffset + sources.byteLength;
  const buffer = new ArrayBuffer(indexOffset + indices.byteLength);
  new Float32Array(buffer, 0, positions.length).set(positions);
  new Float32Array(buffer, normalOffset, normals.length).set(normals);
  new Uint8Array(buffer, colorOffset, colors.length).set(colors);
  new Uint16Array(buffer, classOffset, classes.length).set(classes);
  new Int16Array(buffer, sourceOffset, sources.length).set(sources);
  new Uint32Array(buffer, indexOffset, indices.length).set(indices);
  return {
    buffer,
    metadata: {
      role: "terrain_mesh",
      resourceId: "earth.terrain.mesh",
      version: 1,
      contentKey: "coverage-boundary",
      vertexCount: positions.length / 3,
      indexCount: indices.length,
      navigationSampling: {
        nearAxisM: Array.from(structured.sampling.nearAxisM),
        polarDistanceM: Array.from(structured.sampling.polarDistanceM),
        polarAzimuthStepDeg: structured.sampling.polarAzimuthStepDeg,
      },
      bufferLayout: {
        position: { offset: 0, length: positions.byteLength },
        normal: { offset: normalOffset, length: normals.byteLength },
        color: { offset: colorOffset, length: colors.byteLength },
        classId: { offset: classOffset, length: classes.byteLength },
        sourceId: { offset: sourceOffset, length: sources.byteLength },
        index: { offset: indexOffset, length: indices.byteLength },
      },
    },
  };
}
