import * as THREE from "three";

import type { ApparentTrajectoryMetadata } from "../contracts/astronomical_event_contracts";
import { ApparentTrajectoryRenderer } from "../view/three/ApparentTrajectoryRenderer";

declare const process: { exitCode?: number };

let passed = 0;
let failed = 0;

function assert(condition: boolean, message: string): void {
  if (condition) passed++;
  else {
    failed++;
    console.error(`FAIL: ${message}`);
  }
}

function metadata(requestId: string, objectId = "fixture"): ApparentTrajectoryMetadata {
  return {
    resourceId: `apparent-trajectory:${objectId}`,
    version: `visibility-v1:${requestId}`,
    role: "apparent_trajectory",
    contractVersion: 2,
    requestId,
    bodyId: objectId,
    objectId,
    objectFamily: "coordinate",
    displayName: "Fixture",
    sampleCount: 5,
    startUtc: "2026-09-16T20:00:00Z",
    endUtc: "2026-09-17T00:00:00Z",
    frame: "topocentric ENU East/Up/North",
    generation: 1,
    observerGeneration: 4,
    kernelGeneration: "fixture",
    quality: "scientific",
    horizonVersion: 7,
    horizonQuality: "REAL",
    resolution: "automatic",
    intervalClassification: "mixed",
    astronomicallyCircumpolar: false,
    temporalToleranceSeconds: 1,
    angularToleranceDeg: 0.05,
    computeMs: 2,
    directionComponentType: "float32",
    directionComponents: 3,
    timeOffsetComponentType: "float32",
    validityComponentType: "uint8",
    visibilityComponentType: "uint8",
    horizonProvenanceComponentType: "uint8",
    directionByteOffset: 0,
    timeOffsetByteOffset: 60,
    validityByteOffset: 80,
    visibilityByteOffset: 85,
    horizonProvenanceByteOffset: 90,
    segments: [
      { startIndex: 0, endIndex: 1, visibility: "visible", horizonProvenance: "real" },
      { startIndex: 1, endIndex: 3, visibility: "terrain_occluded", horizonProvenance: "real" },
      { startIndex: 3, endIndex: 4, visibility: "visible", horizonProvenance: "real" },
    ],
    events: [
      {
        kind: "set",
        instantUtc: "2026-09-16T21:00:00Z",
        directionENU: [0.7, 0.1, 0.7],
        azimuthDeg: 45,
        altitudeDeg: 5.7,
        horizonElevationDeg: 5.7,
        horizonProvenance: "real",
      },
      {
        kind: "rise",
        instantUtc: "2026-09-16T23:00:00Z",
        directionENU: [-0.7, 0.1, 0.7],
        azimuthDeg: 315,
        altitudeDeg: 5.7,
        horizonElevationDeg: 5.7,
        horizonProvenance: "real",
      },
    ],
  };
}

function payload(): ArrayBuffer {
  const value = new ArrayBuffer(95);
  new Float32Array(value, 0, 15).set([
    1, 0, 0,
    0.7, 0.1, 0.7,
    0, 0.2, 0.98,
    -0.7, 0.1, 0.7,
    -1, 0, 0,
  ]);
  new Float32Array(value, 60, 5).set([0, 3_600, 7_200, 10_800, 14_400]);
  new Uint8Array(value, 80, 5).fill(1);
  new Uint8Array(value, 85, 5).set([0, 1, 1, 0, 0]);
  new Uint8Array(value, 90, 5).fill(0);
  return value;
}

console.log("=== TerraLab3D Step 22 frontend tests ===");

const parent = new THREE.Group();
const renderer = new ApparentTrajectoryRenderer(parent);
renderer.beginRequest("request-2", "fixture");
assert(
  !renderer.registerBinaryResource(metadata("request-1"), payload()),
  "a stale request cannot relabel or mutate the active trajectory",
);
assert(
  renderer.registerBinaryResource(metadata("request-2"), payload()),
  "the latest visibility trajectory is accepted",
);
assert(
  renderer.root.getObjectByName("apparentTrajectory:visible") !== undefined,
  "the visible segment has its own retained visual",
);
const visibleCore = renderer.root.getObjectByName("apparentTrajectory:visible:core") as any;
const visibleHalo = renderer.root.getObjectByName("apparentTrajectory:visible:halo") as any;
assert(
  visibleCore.material.color.getHex() === 0x38bdf8
    && visibleHalo.material.linewidth > (visibleCore.material.coreWidth ?? 0),
  "the visible segment preserves cyan semantics and adds a wider shared halo",
);
assert(
  visibleCore.geometry === visibleHalo.geometry,
  "trajectory core and halo share one retained segmented geometry",
);
assert(
  renderer.root.getObjectByName("apparentTrajectory:terrain_occluded")!.visible,
  "terrain-occluded segments are visible by default",
);
renderer.setHiddenSegmentsVisible(false);
assert(
  !renderer.root.getObjectByName("apparentTrajectory:terrain_occluded")!.visible,
  "terrain-occluded segments can be hidden independently",
);
renderer.setHiddenSegmentsVisible(true);
assert(
  renderer.root.getObjectByName("apparentTrajectory:terrain_occluded")!.visible,
  "terrain-occluded segments can be shown again",
);
const geometryBuilds = renderer.metrics().geometryBuildCount;
assert(
  renderer.updateSimulationTime("2026-09-16T22:00:00Z") === "covered",
  "the global time moves one active marker inside the sampled interval",
);
assert(
  renderer.root.getObjectByName("apparentTrajectory:active-time")!.visible,
  "the active-time marker is visible inside coverage",
);
assert(
  renderer.metrics().geometryBuildCount === geometryBuilds,
  "moving time updates a buffer and rebuilds no trajectory geometry",
);
assert(
  renderer.updateSimulationTime("2026-09-17T02:00:00Z") === "outside_interval",
  "time outside coverage is explicit and never extrapolated",
);
assert(
  !renderer.root.getObjectByName("apparentTrajectory:active-time")!.visible,
  "the active marker disappears outside coverage",
);
assert(
  renderer.root.getObjectByName("apparentTrajectory:rise-events") !== undefined
    && renderer.root.getObjectByName("apparentTrajectory:set-events") !== undefined,
  "validated rise and set events receive distinct marker sets",
);
assert(
  renderer.metrics().bridgeBytes === payload().byteLength
    && renderer.root.userData.trajectoryMetadata.sampleCount === 5
    && renderer.root.userData.trajectoryMetadata.computeMs === 2,
  "sample, transfer, and calculation metrics remain observable",
);
const activeGeometries = renderer.metrics().activeGeometryCount;
const activeOverlayMaterials = renderer.metrics().activeOverlayMaterialCount;
for (let cycle = 0; cycle < 5; cycle++) {
  const requestId = `cycle-${cycle}`;
  renderer.beginRequest(requestId, "fixture");
  renderer.registerBinaryResource(metadata(requestId), payload());
}
assert(
  renderer.metrics().activeGeometryCount === activeGeometries,
  "repeated replacement cycles retain a bounded number of live geometries",
);
assert(
  renderer.metrics().activeOverlayMaterialCount === activeOverlayMaterials,
  "repeated replacement cycles retain a bounded number of overlay materials",
);
renderer.beginRequest("request-3", "other-object");
assert(
  renderer.root.userData.trajectoryStatus === "calculating"
    && renderer.root.userData.trajectoryMetadata === undefined
    && !renderer.root.getObjectByName("apparentTrajectory:visible")!.visible,
  "changing object invalidates the old visual identity and metadata immediately",
);
renderer.clear();
assert(
  !renderer.registerBinaryResource(metadata("request-3", "other-object"), payload()),
  "a response already in flight cannot repopulate a disabled trajectory",
);
renderer.dispose();
assert(renderer.metrics().activeGeometryCount === 0, "dispose releases all owned trajectory resources");
assert(renderer.metrics().activeOverlayMaterialCount === 0, "dispose releases all trajectory overlay materials");

console.log(`Step 22 frontend tests: ${passed} passed, ${failed} failed`);
if (failed > 0) process.exitCode = 1;
