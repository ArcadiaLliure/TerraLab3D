import * as THREE from "three";

import {
  projectCoordinateToTerrainWorld,
  projectTerrainCoordinate,
} from "../application/TerrainCoordinateProjector";
import { CameraRigImpl, GOTO_FLIGHT_DURATION_S } from "../view/three/CameraRigImpl";
import { GroundFollower } from "../view/three/terrain/GroundFollower";
import type { GroundSample, TerrainSampler } from "../contracts/TerrainSampler";

let passed = 0;
let failed = 0;

function assert(condition: boolean, message: string): void {
  if (condition) passed++;
  else {
    failed++;
    console.error(`FAIL: ${message}`);
  }
}

function assertNear(actual: number, expected: number, tolerance: number, message: string): void {
  assert(Math.abs(actual - expected) <= tolerance, `${message}: ${actual} vs ${expected}`);
}

class FlatDemSampler implements TerrainSampler {
  isReady(): boolean { return true; }

  sampleGround(): GroundSample {
    return {
      heightM: 0,
      normal: { east: 0, up: 1, north: 0 },
      slopeDeg: 0,
      valid: true,
      surfaceId: "test-dem",
    };
  }
}

const anchor = { latitudeDeg: 0, longitudeDeg: 0 };
const origin = projectTerrainCoordinate(anchor, 0, 0);
assert(origin !== null, "world origin resolves to WGS84 coordinates");
assertNear(origin?.latitudeDeg ?? Number.NaN, 0, 1e-12, "origin latitude is retained");
assertNear(origin?.longitudeDeg ?? Number.NaN, 0, 1e-12, "origin longitude is retained");

const eastKilometre = projectTerrainCoordinate(anchor, 1_000, 0);
assert(eastKilometre !== null, "eastward ENU target resolves");
assertNear(eastKilometre?.latitudeDeg ?? Number.NaN, 0, 1e-10, "eastward equatorial target remains on the equator");
assertNear(
  eastKilometre?.longitudeDeg ?? Number.NaN,
  1_000 / 6_378_137 * 180 / Math.PI,
  1e-10,
  "eastward coordinate uses the WGS84 geodesic distance",
);
assert(projectTerrainCoordinate(anchor, Number.NaN, 0) === null, "invalid terrain coordinates are rejected");

const roundTripTarget = projectTerrainCoordinate(anchor, 12_500, -4_000);
const roundTripWorld = roundTripTarget && projectCoordinateToTerrainWorld(anchor, roundTripTarget);
assert(roundTripWorld !== null, "configured WGS84 relocation resolves into the resident terrain world");
assertNear(roundTripWorld?.eastM ?? Number.NaN, 12_500, 0.02, "inverse projection retains east distance");
assertNear(roundTripWorld?.northM ?? Number.NaN, -4_000, 0.02, "inverse projection retains north distance");
assert(projectCoordinateToTerrainWorld(anchor, { latitudeDeg: Number.NaN, longitudeDeg: 0 }) === null, "invalid configured coordinates are rejected");

const rig = new CameraRigImpl(new THREE.PerspectiveCamera());
rig.setTerrainDependencies(new FlatDemSampler(), new GroundFollower());
assert(rig.gotoFlightTo(100, 0, 0), "Goto accepts a valid clicked DEM point");
assert(rig.getNavigationPose().navigationMode === "flight", "Goto switches to aircraft mode");
const internalRig = rig as unknown as { updateFlightMode(deltaSeconds: number): void };
const startPose = rig.getNavigationPose();
const plannedDistanceM = Math.hypot(
  100 - startPose.positionEastM,
  -startPose.positionNorthM,
  100 - startPose.positionUpM,
);
internalRig.updateFlightMode(1);
assert(
  Math.abs(rig.getMotionState().speedMps - plannedDistanceM / GOTO_FLIGHT_DURATION_S) < 1e-6,
  "Goto derives its speed from the current journey distance",
);
internalRig.updateFlightMode(GOTO_FLIGHT_DURATION_S - 1);
assertNear(rig.getNavigationPose().positionEastM, 100, 1e-6, "Goto reaches clicked east coordinate continuously");
assertNear(rig.getNavigationPose().positionNorthM, 0, 1e-6, "Goto reaches clicked north coordinate continuously");
assert(rig.getMotionState().speedMps === 0, "Goto stops after reaching its terrain destination");

assert(rig.gotoFlightTo(250, 0, 0), "a new Goto command starts a replacement journey");
const pointerRig = rig as unknown as { onPointerDown(event: PointerEvent): void };
pointerRig.onPointerDown({ button: 0, clientX: 20, clientY: 20, pointerId: 1 } as PointerEvent);
const pointerMoveRig = rig as unknown as { onPointerMove(event: PointerEvent): void };
pointerMoveRig.onPointerMove({ clientX: 40, clientY: 10 } as PointerEvent);
internalRig.updateFlightMode(1);
assert(
  rig.getNavigationPose().positionEastM > 100,
  "turning the camera does not interrupt an active Goto journey",
);

assert(rig.gotoFlightTo(400, 0, 0), "a new coordinate replaces the active Goto destination");
internalRig.updateFlightMode(GOTO_FLIGHT_DURATION_S);
assertNear(rig.getNavigationPose().positionEastM, 400, 1e-6, "the replacement Goto reaches the new destination");

assert(rig.gotoFlightTo(500, 0, 0), "Goto can start another journey after arrival");
const keyboardRig = rig as unknown as { onKeyDown(event: KeyboardEvent): void };
keyboardRig.onKeyDown({ code: "Escape", preventDefault() {} } as KeyboardEvent);
assert(rig.getMotionState().speedMps === 0, "Escape explicitly cancels the active Goto journey");
internalRig.updateFlightMode(1);
assertNear(rig.getNavigationPose().positionEastM, 400, 1e-6, "an Escape-cancelled Goto does not advance");

console.log(`Terrain Goto tests: ${passed} passed, ${failed} failed`);
if (failed > 0) (globalThis as { process?: { exit(code: number): void } }).process?.exit(1);
