import * as THREE from "three";

import type { SkyEnvironmentSnapshot } from "../contracts/sky_environment_contracts";
import type { ResourceCatalogSnapshotMessage } from "../contracts/bridge_messages";
import { ResourceManager } from "../application/ResourceManager";
import type { BackendMessageListener, WebSocketBridge } from "../bridge/WebSocketBridge";
import { CelestialTransformState } from "../view/three/CelestialTransformState";
import {
  GalacticSkyRenderer,
  galacticVisibilityFactor,
  type GalacticTextureLoader,
  type GalacticTextureResource,
} from "../view/three/GalacticSkyRenderer";
import {
  equatorialDirectionFromRaDec,
  milkyWayUvFromRaDec,
  planckUvFromEquatorialDirection,
} from "../view/three/galacticCoordinates";

declare const process: { exitCode?: number };

let passed = 0;
let failed = 0;

function check(condition: boolean, message: string): void {
  if (!condition) {
    failed++;
    console.error(`  ✗ ${message}`);
    return;
  }
  passed++;
}

function near(actual: number, expected: number, tolerance: number, message: string): void {
  check(Math.abs(actual - expected) <= tolerance, `${message}: ${actual} ≈ ${expected}`);
}

class FakeTextureLoader implements GalacticTextureLoader {
  milkyLoads = 0;
  dustLoads = 0;

  async loadMilkyWay(): Promise<THREE.Texture> {
    this.milkyLoads++;
    return new THREE.DataTexture(new Float32Array([1, 0.5, 0.2, 1]), 1, 1);
  }

  async loadPlanckDust(): Promise<THREE.Texture> {
    this.dustLoads++;
    return new THREE.DataTexture(new Uint8Array([180, 180, 180, 255]), 1, 1);
  }
}

class FakeResourceBridge {
  listener: BackendMessageListener | null = null;

  addMessageListener(listener: BackendMessageListener): void {
    this.listener = listener;
  }
}

function resource(
  resourceId: "sky.milky_way" | "sky.planck_dust",
  version: string,
  width = 4096,
  height = 2048,
): GalacticTextureResource {
  return { resourceId, version, width, height, url: `/asset/${resourceId}/${version}` };
}

function environment(brightness: number, bortleClass: number | null): SkyEnvironmentSnapshot {
  return {
    generation: 1,
    solarSystemGeneration: 1,
    sunAltitudeDeg: -30,
    sunAzimuthDeg: 180,
    sunDirectionENU: [0, -1, 0],
    twilightPhase: "night",
    twilightFactor: 1,
    atmosphereEnabled: true,
    turbidity: 2.5,
    horizonHaze: 0.1,
    lightPollutionEnabled: bortleClass !== null,
    lightPollutionMode: "bortle",
    lightPollutionSource: "manual_bortle",
    bortleClass,
    sqmZenith: null,
    configuredMagnitudeLimit: null,
    visibility: {
      zenithMagnitudeLimit: 6.5,
      extinctionCoefficient: 0.25,
      twilightSuppression: 0,
      fadeWidthMag: 0.75,
      skyBrightnessNormalized: brightness,
    },
    zenithColorLinear: [0, 0, 0],
    horizonColorLinear: [0, 0, 0],
    groundColorLinear: [0, 0, 0],
    skyDiffuseIntensity: 0,
    solarDiscTransmission: 1,
    skyEclipseDimmingFactor: 1,
  };
}

const BARCELONA_WINTER_MIDNIGHT = [
  -0.8939312321067816, -0.44820414128391467, 0,
  -0.33626806206300347, 0.6706777009624397, 0.6611468912943087,
  -0.29632877467509533, 0.5910198551382898, -0.750256481566052,
];

const BARCELONA_SUMMER_MIDNIGHT = [
  0.9060812402202294, 0.4231037533761324, 0,
  0.31743633334536764, -0.679793323300634, 0.6611468912943087,
  0.2797337312395838, -0.5990527952316964, -0.750256481566052,
];

const BARCELONA_SUMMER_LST = [
  0.9817094327929432, 0.19038537119578747, 0,
  0.14283785873499827, -0.7365338649674381, 0.6611468912943087,
  0.1258726963140079, -0.6490541396453535, -0.750256481566052,
];

const SYDNEY_SAME_LST = [
  0.9817094327929432, 0.19038537119578747, 0,
  0.1580799966546527, -0.8151289296915436, -0.5572930491559926,
  -0.10610044402839588, 0.5470998431863794, -0.830315878062329,
];

function localDirection(matrix: THREE.Matrix3, equatorial: THREE.Vector3): THREE.Vector3 {
  return equatorial.clone().normalize().applyMatrix3(matrix).normalize();
}

function galacticPlaneInclinationDeg(matrix: THREE.Matrix3): number {
  const center = localDirection(
    matrix,
    equatorialDirectionFromRaDec(266.4051, -28.936175),
  );
  const planeTangent = localDirection(
    matrix,
    new THREE.Vector3(0.4941094279, -0.44482963, 0.7469822445),
  );
  const localUp = new THREE.Vector3(0, 1, 0)
    .addScaledVector(center, -center.y)
    .normalize();
  const localRight = new THREE.Vector3().crossVectors(center, localUp).normalize();
  const angle = THREE.MathUtils.radToDeg(Math.atan2(
    planeTangent.dot(localUp),
    planeTangent.dot(localRight),
  ));
  return (angle + 180) % 180;
}

function transformState(matrix: number[]): CelestialTransformState {
  const state = new CelestialTransformState();
  state.update(1, matrix);
  return state;
}

async function run(): Promise<void> {
  console.log("=== TerraLab3D Step 10 galactic tests ===");

  const resourceBridge = new FakeResourceBridge();
  const resourceManager = new ResourceManager(resourceBridge as unknown as WebSocketBridge);
  const catalogSnapshot: ResourceCatalogSnapshotMessage = {
    type: "resource_catalog_snapshot",
    descriptors: [{
      id: "sky.milky_way",
      name: "Via Làctia",
      description: "",
      domain: "sky",
      category: "deep_sky",
      provider: "NASA SVS",
      acquisitionKind: "STATIC_FILE",
      citation: "",
      license: "",
      variants: [
        { id: "4k", title: "4K", metadata: {} },
        { id: "64k", title: "64K", metadata: {} },
      ],
      credits: [],
      dependencies: [],
      metadata: {},
    }],
    installedStates: {
      "sky.milky_way::4k": {
        status: "READY",
        variantId: "4k",
        downloadedBytes: 36_436_668,
        verifiedAt: "v1",
        error: null,
        manifestData: null,
      },
      "sky.milky_way::64k": {
        status: "PARTIAL",
        variantId: "64k",
        downloadedBytes: 671_901_255,
        verifiedAt: null,
        error: null,
        manifestData: null,
      },
    },
  };
  resourceBridge.listener?.onResourceCatalogSnapshot?.(catalogSnapshot);
  const detectedMilkyWay = resourceManager.getEffectiveInstallState("sky.milky_way");
  check(
    detectedMilkyWay.status === "READY" && detectedMilkyWay.variantId === "4k",
    "resource-backed rows detect a READY variant instead of querying an undefined variant",
  );
  check(
    resourceManager.getEffectiveInstallState("sky.milky_way", "64k").status === "PARTIAL",
    "an explicitly selected resource variant remains authoritative",
  );

  const center = milkyWayUvFromRaDec(0, 0);
  near(center[0], 0.5, 1e-12, "RA=0h is at the horizontal centre");
  near(center[1], 0.5, 1e-12, "Dec=0 is at the vertical centre");
  check(milkyWayUvFromRaDec(15, 0)[0] < center[0], "increasing RA moves left");
  check(milkyWayUvFromRaDec(345, 0)[0] > center[0], "decreasing RA moves right");
  check(
    milkyWayUvFromRaDec(0, 30)[1] > center[1],
    "increasing Dec increases GPU v after EXR scanline decoding",
  );
  check(
    milkyWayUvFromRaDec(0, -30)[1] < center[1],
    "decreasing Dec decreases GPU v after EXR scanline decoding",
  );
  near(milkyWayUvFromRaDec(360, 0)[0], center[0], 1e-12, "RA seam wraps exactly");

  const milkyWayGalacticCenter = milkyWayUvFromRaDec(266.4051, -28.936175);
  near(milkyWayGalacticCenter[0], 0.7599858333333334, 1e-12,
    "Galactic centre retains the NASA horizontal coordinate");
  near(milkyWayGalacticCenter[1], 0.3392434722222222, 1e-12,
    "Galactic centre remains at negative declination after EXR decoding");
  const observerLatitudeDeg = 41.21124;
  const realCoreCulminationDeg = 90 - Math.abs(observerLatitudeDeg - (-28.936175));
  const verticallyMirroredCulminationDeg = 90 - Math.abs(observerLatitudeDeg - 28.936175);
  check(realCoreCulminationDeg < 20, "real Galactic centre cannot culminate near zenith");
  check(verticallyMirroredCulminationDeg > 77,
    "the rejected vertical mirror reproduces the screenshot's false zenith core");

  const galacticCenter = equatorialDirectionFromRaDec(266.4051, -28.936175);
  const planckCenter = planckUvFromEquatorialDirection(galacticCenter);
  check(
    Math.min(Math.abs(planckCenter[0]), Math.abs(planckCenter[0] - 1)) < 0.001,
    "known Galactic centre maps to l=0 seam",
  );
  near(planckCenter[1], 0.5, 0.001, "known Galactic centre maps to b=0");

  const parent = new THREE.Group();
  const loader = new FakeTextureLoader();
  const renderer = new GalacticSkyRenderer(parent, 8192, loader);
  check(parent.children.length === 1, "one persistent skydome is attached");
  await renderer.installMilkyWay(resource("sky.milky_way", "4k:v1"));
  await renderer.installMilkyWay(resource("sky.milky_way", "4k:v1"));
  await renderer.installPlanckDust(resource("sky.planck_dust", "r2.01:v1", 3600, 1800));
  check(loader.milkyLoads === 1, "same Milky Way version is not uploaded twice");
  check(loader.dustLoads === 1, "Planck texture is loaded once");
  check(renderer.metrics().geometryBuildCount === 1, "geometry remains persistent");
  check(renderer.metrics().activeTextureCount === 2, "both independent layers are resident");

  renderer.setMilkyWayVisible(true);
  check(
    !renderer.getLayerVisibility().milkyWayVisible,
    "Milky Way stays hidden until the observer-local frame is ready",
  );

  const sharedTransform = new CelestialTransformState();
  sharedTransform.update(1, [0, 1, 0, 0, 0, 1, 1, 0, 0]);
  renderer.setTransformState(sharedTransform);
  const rendererMatrix = renderer.getTransformMatrix().elements;
  const sharedMatrix = sharedTransform.equatorialToThree.elements;
  check(rendererMatrix.every((value, index) => Math.abs(value - sharedMatrix[index]!) < 1e-12),
    "skydome consumes the same celestial transform as Gaia");
  check(
    renderer.getLayerVisibility().milkyWayVisible,
    "requested Milky Way becomes visible when the local frame arrives",
  );

  const galacticCenterDirection = equatorialDirectionFromRaDec(266.4051, -28.936175);
  renderer.setTransformState(transformState(BARCELONA_WINTER_MIDNIGHT));
  const winterCenter = localDirection(renderer.getTransformMatrix(), galacticCenterDirection);
  renderer.setTransformState(transformState(BARCELONA_SUMMER_MIDNIGHT));
  const summerCenter = localDirection(renderer.getTransformMatrix(), galacticCenterDirection);
  check(winterCenter.y < -0.85, "Galactic centre is far below Barcelona's winter horizon");
  check(summerCenter.y > 0.25, "Galactic centre rises above Barcelona's summer horizon");

  const barcelonaInclination = galacticPlaneInclinationDeg(
    transformState(BARCELONA_SUMMER_LST).equatorialToThree,
  );
  const sydneyInclination = galacticPlaneInclinationDeg(
    transformState(SYDNEY_SAME_LST).equatorialToThree,
  );
  const rawInclinationDifference = Math.abs(barcelonaInclination - sydneyInclination);
  const inclinationDifference = Math.min(
    rawInclinationDifference,
    180 - rawInclinationDifference,
  );
  check(
    inclinationDifference > 60,
    "Galactic plane inclination changes with observer latitude at the same LST",
  );

  const darkBortle1 = galacticVisibilityFactor(environment(0, 1));
  const brightBortle8 = galacticVisibilityFactor(environment(0.7, 8));
  const daylight = galacticVisibilityFactor(environment(1, 1));
  check(darkBortle1 > brightBortle8, "light pollution attenuates diffuse galactic layers");
  near(daylight, 0, 1e-12, "daylight attenuation emerges continuously from sky brightness");

  let oversizedRejected = false;
  try {
    await renderer.installMilkyWay(resource("sky.milky_way", "64k:v1", 65536, 32768));
  } catch {
    oversizedRejected = true;
  }
  check(oversizedRejected, "GPU-incompatible variants fail explicitly");

  renderer.dispose();
  check(parent.children.length === 0, "dispose detaches the persistent skydome");
  check(renderer.metrics().activeTextureCount === 0, "dispose releases resident textures");

  console.log(`Step 10 galactic tests: ${passed} passed, ${failed} failed`);
  if (failed > 0) process.exitCode = 1;
}

void run();
