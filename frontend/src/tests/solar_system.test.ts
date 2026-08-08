import * as THREE from "three";

import type { SolarSystemBodyState, SolarSystemSnapshot } from "../contracts/solar_system_contracts";
import { threeFromEnu } from "../view/three/celestialCoordinates";
import {
  phaseLightDirectionThree,
  PLANET_PRESENTATIONS,
  SolarSystemRenderer,
} from "../view/three/SolarSystemRenderer";
import { formatPlanetLabel } from "../view/three/SolarSystemLabels";

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

function body(
  id: SolarSystemBodyState["id"],
  directionENU: readonly [number, number, number],
  altitudeDeg = 30,
  phaseAngleDeg = 30,
): SolarSystemBodyState {
  return {
    id,
    type: id === "sun" ? "sun" : id === "moon" ? "moon" : "planet",
    rightAscensionDeg: 10,
    declinationDeg: 20,
    altitudeDeg,
    azimuthDeg: 90,
    directionENU,
    distanceKm: id === "moon" ? 384_400 : 149_597_870,
    angularRadiusDeg: id === "sun" ? 0.266 : id === "moon" ? 0.25 : 0.01,
    angularDiameterDeg: id === "sun" ? 0.532 : id === "moon" ? 0.5 : 0.02,
    illuminationFraction: (1 + Math.cos(THREE.MathUtils.degToRad(phaseAngleDeg))) / 2,
    phaseAngleDeg,
    apparentMagnitude: id === "sun" ? -26.7 : -4,
    brightLimbPositionAngleDeg: id === "sun" ? null : 90,
    source: "DE421",
    quality: "precise",
  };
}

function snapshot(
  generation: number,
  timestampUtc: string,
  observerGeneration = 1,
  includeBodies = true,
): SolarSystemSnapshot {
  return {
    generation,
    timestampUtc,
    observerGeneration,
    source: includeBodies ? "DE421" : "fallback",
    quality: includeBodies ? "precise" : "fallback",
    detail: null,
    computeMs: 8,
    sun: body("sun", [1, 0.5, 0]),
    moon: includeBodies ? body("moon", [0, 0.5, 1]) : null,
    planets: includeBodies ? [body("venus", [-1, 0.25, 0])] : [],
  };
}

const north = threeFromEnu([0, 0, 1]);
near(north.x, 0, 1e-12, "north x");
near(north.y, 0, 1e-12, "north y");
near(north.z, -1, 1e-12, "north maps to Three -Z");
near(threeFromEnu([1, 0, 0]).x, 1, 1e-12, "east maps to Three +X");
near(threeFromEnu([0, 1, 0]).y, 1, 1e-12, "up maps to Three +Y");
assert(formatPlanetLabel("neptune", 7.8) === "Neptune 7.8", "planet tag includes the apparent magnitude");
assert(PLANET_PRESENTATIONS.neptune.cssColor === "#6e9bff", "Neptune tag uses its characteristic colour");
assert(PLANET_PRESENTATIONS.mars.cssColor === "#ff7350", "Mars tag uses its characteristic colour");

const parent = new THREE.Group();
const renderer = new SolarSystemRenderer(parent);
assert(parent.children.includes(renderer.root), "persistent root is attached once");
assert(renderer.metrics().entityBuildCount === 9, "nine persistent entities are built");
assert(renderer.metrics().geometryBuildCount === 1, "one geometry is shared");
assert(renderer.metrics().materialBuildCount === 9, "materials are built only at construction");

assert(renderer.updateSnapshot(snapshot(1, "2024-01-01T00:00:00Z"), 2048, 1_000), "first snapshot accepted");
assert(renderer.getBodyObject("sun")?.visible === true, "sun above horizon is visible");
assert(renderer.getBodyObject("moon")?.visible === true, "moon above horizon is visible");
near(
  renderer.getBodyObject("sun")!.scale.x,
  900_000 * Math.sin(THREE.MathUtils.degToRad(0.266)),
  1e-9,
  "sphere scale preserves the scientific angular radius",
);
assert(renderer.metrics().lastBridgeBytes === 2048, "compact bridge byte count is retained");

const before = renderer.getBodyObject("sun")!.position.clone().normalize();
const next = snapshot(2, "2024-01-01T00:00:01Z");
const movedSun = body("sun", [0, 0.5, 1]);
const moving = { ...next, sun: movedSun };
renderer.updateSnapshot(moving, 1900, 2_000);
renderer.update(2_050);
const midway = renderer.getBodyObject("sun")!.position.clone().normalize();
const target = threeFromEnu(movedSun.directionENU).normalize();
assert(midway.distanceTo(before) > 0.01 && midway.distanceTo(target) > 0.01, "ordinary updates interpolate");

renderer.updateSnapshot({ ...moving, generation: 3, observerGeneration: 2 }, 1900, 3_000);
near(renderer.getBodyObject("sun")!.position.clone().normalize().distanceTo(target), 0, 1e-9, "observer change snaps");
assert(!renderer.updateSnapshot({ ...moving, generation: 2 }, 1900, 3_100), "stale generation is rejected");
assert(renderer.metrics().staleSnapshotCount === 1, "stale snapshot is measured");

const partialHorizon = { ...body("moon", [0, -0.001, 1], -0.1), angularRadiusDeg: 0.25 };
renderer.updateSnapshot({ ...snapshot(4, "2024-01-01T00:00:02Z", 3), moon: partialHorizon }, 1800, 4_000);
assert(renderer.getBodyObject("moon")?.visible === true, "disc intersecting horizon remains visible for shader clipping");
const belowHorizon = { ...partialHorizon, altitudeDeg: -1 };
renderer.updateSnapshot({ ...snapshot(5, "2024-01-01T00:00:03Z", 4), moon: belowHorizon }, 1800, 5_000);
assert(renderer.getBodyObject("moon")?.visible === false, "body fully below horizon is hidden");

renderer.updateSnapshot(snapshot(6, "2024-01-01T00:00:04Z", 5, false), 900, 6_000);
assert(renderer.getBodyObject("moon")?.visible === false, "honest fallback hides unavailable moon");
assert(renderer.getBodyObject("venus")?.visible === false, "honest fallback hides unavailable planets");

const quarter = body("moon", [0, 0, 1], 30, 90);
const sunEast = body("sun", [1, 0, 0]);
const sunWest = body("sun", [-1, 0, 0]);
assert(phaseLightDirectionThree(quarter, sunEast).x > 0.99, "bright limb points toward an eastern Sun");
assert(phaseLightDirectionThree(quarter, sunWest).x < -0.99, "bright limb reverses for a western Sun");

for (let generation = 7; generation < 107; generation++) {
  renderer.updateSnapshot(snapshot(generation, `2024-01-01T00:00:${String(generation % 60).padStart(2, "0")}Z`), 1000, generation * 1000);
}
assert(renderer.metrics().entityBuildCount === 9, "timeline updates do not rebuild entities");
assert(renderer.metrics().geometryBuildCount === 1, "timeline updates do not rebuild geometry");
assert(renderer.metrics().materialBuildCount === 9, "timeline updates do not rebuild materials");

renderer.dispose();
assert(!parent.children.includes(renderer.root), "dispose detaches the root");

console.log(`Solar system tests: ${passed} passed, ${failed} failed`);
if (failed > 0) (globalThis as { process?: { exit(code: number): void } }).process?.exit(1);
