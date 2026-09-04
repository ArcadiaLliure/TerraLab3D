import * as THREE from "three";

import type {
  BodyOrientationState,
  PlanetTextureAsset,
  SatelliteCatalogManifest,
  SatelliteDefinition,
  SolarSystemBodyState,
} from "../contracts/solar_system_contracts";
import { NaturalSatelliteRenderer } from "../view/three/NaturalSatelliteRenderer";
import { threeQuaternionFromBodyToEnu } from "../view/three/celestialCoordinates";
import { PhysicalBodyVisual } from "../view/three/PhysicalBodyVisual";
import { SatelliteOrbitRenderer } from "../view/three/SatelliteOrbitRenderer";
import {
  SATURN_RING_RADII_KM,
  ringPointOccludedByPlanet,
  SaturnRingRenderer,
} from "../view/three/SaturnRingRenderer";

let passed = 0;
let failed = 0;

function assert(condition: boolean, message: string): void {
  if (condition) passed++;
  else {
    failed++;
    console.error(`FAIL: ${message}`);
  }
}

function orientation(
  body: readonly [number, number, number, number],
  equatorial: readonly [number, number, number, number],
): BodyOrientationState {
  return {
    frame: "IAU_SATURN",
    source: "NAIF PCK pck00011",
    quality: "IAU_MODEL",
    bodyToENUQuaternion: body,
    equatorialToENUQuaternion: equatorial,
    bodyToSunDirectionENU: [1, 0, 0],
    northPoleICRF: [0, 0, 1],
    computeMs: 0.1,
    detail: null,
  };
}

function body(
  id: SolarSystemBodyState["id"],
  type: SolarSystemBodyState["type"],
  bodyOrientation: BodyOrientationState | null,
): SolarSystemBodyState {
  return {
    id,
    displayName: id,
    type,
    rightAscensionDeg: 0,
    declinationDeg: 0,
    altitudeDeg: 30,
    azimuthDeg: 90,
    directionENU: [1, 0.5, 0],
    distanceKm: 1_000_000,
    angularRadiusDeg: 0.1,
    angularDiameterDeg: 0.2,
    illuminationFraction: 0.75,
    phaseAngleDeg: 60,
    apparentMagnitude: null,
    brightLimbPositionAngleDeg: null,
    orientation: bodyOrientation,
    bodyToSunDirectionENU: [1, 0, 0],
    horizonVisible: true,
    source: "SPICE/DE440",
    quality: "precise",
  };
}

assert(SATURN_RING_RADII_KM.cInner === 74_658, "C-ring inner radius uses the NASA fixture");
assert(SATURN_RING_RADII_KM.cOuter === 91_975, "C/B boundary uses the NASA fixture");
assert(SATURN_RING_RADII_KM.bOuter === 117_507, "B-ring outer radius uses the NASA fixture");
assert(SATURN_RING_RADII_KM.aInner === 122_340, "Cassini Division keeps physical width");
assert(SATURN_RING_RADII_KM.aOuter === 136_780, "A-ring outer radius uses the NASA fixture");
const saturnRadiiLocal = [1, 1, 54_364 / 60_268] as const;
assert(
  !ringPointOccludedByPlanet([0, -10, 3], [0, -1.5, 0], saturnRadiiLocal),
  "the near ring segment remains visible in front of Saturn",
);
assert(
  ringPointOccludedByPlanet([0, -10, 3], [0, 1.5, 0], saturnRadiiLocal),
  "the far ring segment is analytically hidden behind Saturn",
);
assert(
  !ringPointOccludedByPlanet([0, -10, 3], [2, 1.5, 0], saturnRadiiLocal),
  "a far ring point outside Saturn's limb remains visible",
);
const identityBodyToThree = threeQuaternionFromBodyToEnu([0, 0, 0, 1]);
assert(
  new THREE.Vector3(1, 0, 0).applyQuaternion(identityBodyToThree).distanceTo(new THREE.Vector3(1, 0, 0)) < 1e-12,
  "renderer-neutral east maps to Three +X",
);
assert(
  new THREE.Vector3(0, 1, 0).applyQuaternion(identityBodyToThree).distanceTo(new THREE.Vector3(0, 0, -1)) < 1e-12,
  "renderer-neutral north maps to Three -Z",
);
assert(
  new THREE.Vector3(0, 0, 1).applyQuaternion(identityBodyToThree).distanceTo(new THREE.Vector3(0, 1, 0)) < 1e-12,
  "renderer-neutral up maps to Three +Y",
);

const noTexture = (_url: string, _loaded: (texture: THREE.Texture) => void): void => {};
const physical = new PhysicalBodyVisual(
  "saturn",
  new THREE.SphereGeometry(1, 8, 8),
  0xffffff,
  noTexture,
);
const ellipsoid = {
  ...body("saturn", "planet", orientation([0, 0, 0, 1], [0, 0, 0, 1])),
  radiiKm: [60_268, 60_268, 54_364] as const,
  meanRadiusKm: Math.cbrt(60_268 * 60_268 * 54_364),
};
physical.updateState(ellipsoid, 100, new THREE.Vector3(1, 0, 0), true);
assert(physical.mesh.scale.y < physical.mesh.scale.x, "generic visual preserves PCK oblateness");
assert(physical.bodyRoot.name === "saturnSurfaceSpinRoot", "surface spin has an explicit persistent root");
physical.dispose();

let ringTextureLoads = 0;
const ring = new SaturnRingRenderer(new THREE.Group(), (_url, loaded) => {
  ringTextureLoads++;
  loaded(new THREE.Texture());
});
const equatorial = new THREE.Quaternion().setFromAxisAngle(
  new THREE.Vector3(1, 0, 0), Math.PI / 4,
).toArray() as [number, number, number, number];
ring.updateState(body("saturn", "planet", orientation([0, 0, 0, 1], equatorial)), true);
const ringPlaneBeforeSpin = ring.root.quaternion.clone();
ring.updateState(body("saturn", "planet", orientation([0, 0, 1, 0], equatorial)), true);
assert(ring.root.quaternion.equals(ringPlaneBeforeSpin), "surface W does not rotate the ring plane");
assert(ring.mesh.material.side === THREE.DoubleSide, "rings are visible from both sides");
assert(
  !ring.mesh.material.depthTest && !ring.mesh.material.depthWrite,
  "analytic planet occlusion replaces the imprecise celestial-sphere depth buffer",
);
ring.updateState(ellipsoid, true);
assert(ring.root.scale.x > 1, "ring radii retain their physical ratio to Saturn's equatorial radius");
const ringAsset: PlanetTextureAsset = {
  bodyId: "saturn", naifId: 699, role: "rings", name: "saturn_rings.png",
  url: "/planet-assets/saturn_rings.png", sha256: "a".repeat(64), byteSize: 10,
  widthPx: 8192, heightPx: 500, format: "PNG", colorSpace: "sRGB",
  projection: "radial", centralMeridianDeg: null, uvFlipX: false, uvFlipY: false,
  uvRotationDeg: 0, textureQuality: "VISUAL_REFERENCE", credits: "NASA", license: "CC BY 4.0",
};
ring.configureTexture(ringAsset);
ring.configureTexture(ringAsset);
assert(ringTextureLoads === 1, "ring texture is loaded only once");
assert(ring.metrics().bridgeTextureBytes === 0, "ring texture bytes never cross the bridge");
ring.dispose();

function definition(index: number): SatelliteDefinition {
  const moon = index === 0;
  return {
    id: moon ? "naif-301" : `naif-${10_000 + index}`,
    naifId: moon ? 301 : 10_000 + index,
    name: moon ? "Moon" : `Satellite ${index}`,
    displayName: moon ? "Moon" : `Satellite ${index}`,
    provisionalDesignation: null,
    parentNaifId: moon ? 399 : 599,
    parentId: moon ? "earth" : "jupiter",
    spkKernelIds: ["fixture.bsp"],
    spkCoverageStartET: 0,
    spkCoverageEndET: 1,
    bodyFixedFrame: null,
    hasOrientationModel: false,
    radiiKm: null,
    meanRadiusKm: null,
    ephemerisQuality: "HIGH_PRECISION",
    orientationQuality: "UNAVAILABLE",
    shapeQuality: "UNAVAILABLE",
    textureQuality: "UNAVAILABLE",
  };
}

const catalog: SatelliteCatalogManifest = {
  status: "partial",
  catalogVersion: "fixture",
  catalogDate: "2026-07-09",
  counts: { total: 461, byParent: { earth: 1, jupiter: 460 } },
  coverage: { withSpk: 461, withOrientation: 0, withRadius: 0, withTexture: 0, withoutSpk: [] },
  satellites: Array.from({ length: 461 }, (_, index) => definition(index)),
};
const satellites = new NaturalSatelliteRenderer(new THREE.Group());
satellites.configureCatalog(catalog);
satellites.setEnabled(true);
const satelliteState = body("naif-10001", "natural_satellite", null);
const dummyMap = new Map<any, any>();
const dummyOcclusion = {
  preparedPresentationRadius: () => 0,
};
satellites.updateStates([{ ...satelliteState, parentBodyId: "jupiter" }], dummyMap, dummyOcclusion);
assert(satellites.metrics().catalogCount === 461, "one data-driven catalog keeps all 461 entries");
assert(satellites.metrics().entityBuildCount === 460, "the existing Moon is not duplicated");
assert(satellites.metrics().stateCount === 1, "only requested system states enter each tick");
assert(satellites.getPickableBodies().length === 1, "visible natural satellites are selectable");
const entityBuildCount = satellites.metrics().entityBuildCount;
satellites.updateStates([{ ...satelliteState, parentBodyId: "jupiter", azimuthDeg: 91 }], dummyMap, dummyOcclusion);
assert(satellites.metrics().entityBuildCount === entityBuildCount, "timeline updates rebuild no satellite entities");
satellites.dispose();

const orbits = new SatelliteOrbitRenderer(new THREE.Group());
const orbitMetadata = {
  resourceId: "orbit:naif-401", version: "1", role: "solar_system_orbit" as const,
  bodyId: "naif-401", parentBodyId: "mars", sampleCount: 4,
  frame: "J2000 planetocentric" as const, kernelGeneration: "fixture",
  orbitGeneration: 1, componentType: "float32" as const, componentsPerVertex: 3 as const,
};
assert(orbits.registerBinaryResource(orbitMetadata, new Float32Array(12).buffer), "first orbit buffer is accepted");
assert(!orbits.registerBinaryResource(orbitMetadata, new Float32Array(12).buffer), "stale orbit generation is rejected");
assert(orbits.registerBinaryResource(
  { ...orbitMetadata, version: "2", orbitGeneration: 2 },
  new Float32Array(12).buffer,
), "new orbit generation replaces the old buffer");
assert(orbits.metrics().geometryBuildCount === 2, "orbit geometries build only per generation");
assert(orbits.metrics().disposedGeometryCount === 1, "replaced orbit GPU geometry is disposed");
orbits.dispose();

console.log(`Solar system Step 8.6 tests: ${passed} passed, ${failed} failed`);
if (failed > 0) (globalThis as { process?: { exitCode: number } }).process!.exitCode = 1;
