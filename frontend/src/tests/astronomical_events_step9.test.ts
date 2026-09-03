import * as THREE from "three";

import type {
  ApparentTrajectoryMetadata,
  AstronomicalEventSnapshot,
  LunarEclipseState,
} from "../contracts/astronomical_event_contracts";
import type {
  LunarOrientationState,
  SolarSystemBodyState,
  SolarSystemSnapshot,
} from "../contracts/solar_system_contracts";
import { ApparentTrajectoryRenderer } from "../view/three/ApparentTrajectoryRenderer";
import { CelestialOcclusionPolicy } from "../view/three/CelestialOcclusionPolicy";
import { MoonSurfaceRenderer } from "../view/three/MoonSurfaceRenderer";
import { SolarSystemRenderer } from "../view/three/SolarSystemRenderer";
import { SolarTotalityRenderer } from "../view/three/SolarTotalityRenderer";
import { skyFragmentShader } from "../view/three/shaders/skyShader";
import { formatLocalAndUtcTime } from "../view/ui/timeFormatting";

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

function near(actual: number, expected: number, tolerance: number, message: string): void {
  assert(Math.abs(actual - expected) <= tolerance, `${message}: ${actual} vs ${expected}`);
}

function orientation(): LunarOrientationState {
  return {
    frame: "MOON_ME_DE421",
    source: "NAIF",
    quality: "precise",
    bodyToENUQuaternion: [0, 0, 0, 1],
    librationLongitudeDeg: 0,
    librationLatitudeDeg: 0,
    subEarthLongitudeDeg: 0,
    subEarthLatitudeDeg: 0,
    subObserverLongitudeDeg: 0,
    subObserverLatitudeDeg: 0,
    northPolePositionAngleDeg: 0,
    brightLimbPositionAngleDeg: 0,
    moonToSunDirectionENU: [0, 0, -1],
    computeMs: 1,
    detail: null,
  };
}

function body(id: "sun" | "moon" | "mars", distanceKm: number): SolarSystemBodyState {
  const radius = id === "sun" ? 0.262957 : id === "moon" ? 0.27159 : 0.001;
  return {
    id,
    type: id === "sun" ? "sun" : id === "moon" ? "moon" : "planet",
    rightAscensionDeg: 0,
    declinationDeg: 0,
    altitudeDeg: 20,
    azimuthDeg: 180,
    directionENU: [0, 0.4, -0.916515],
    distanceKm,
    angularRadiusDeg: radius,
    angularDiameterDeg: radius * 2,
    illuminationFraction: 1,
    phaseAngleDeg: 0,
    apparentMagnitude: id === "sun" ? -26.7 : -12,
    brightLimbPositionAngleDeg: null,
    orientation: id === "moon" ? orientation() : null,
    source: "DE440",
    quality: "precise",
  };
}

function snapshot(): SolarSystemSnapshot {
  return {
    generation: 1,
    timestampUtc: "2026-08-12T18:29:58.953151Z",
    observerGeneration: 3,
    source: "DE440",
    quality: "precise",
    detail: null,
    computeMs: 2,
    sun: body("sun", 151_000_000),
    moon: body("moon", 366_000),
    planets: [body("mars", 300_000_000)],
  };
}

function lunarState(classification: LunarEclipseState["classification"] = "none"): LunarEclipseState {
  return {
    classification,
    penumbraRadiusKm: 8_500,
    umbraRadiusKm: 4_600,
    moonRadiusKm: 1_737.4,
    shadowAxisOffsetKm: classification === "total" ? 500 : 20_000,
    penumbralMagnitude: classification === "none" ? 0 : 2,
    umbralMagnitude: classification === "total" ? 1.15 : 0,
    penumbraRadiusMoonRadii: 4.9,
    umbraRadiusMoonRadii: 2.65,
    shadowOffsetMoonRadii: classification === "total" ? 0.29 : 11,
    shadowOffsetPositionAngleDeg: 73,
    meanLunarLightTransmission: classification === "total" ? 0.08 : 1,
    sourceAltitudeDeg: 30,
    locallyVisible: true,
    atmosphereEnlargementFactor: 1.02,
    geometryQuality: "scientific",
  };
}

function eventSnapshot(generation = 1): AstronomicalEventSnapshot {
  return {
    generation,
    timestampUtc: "2026-08-12T18:29:58.953151Z",
    observerGeneration: 3,
    sourceSolarSystemGeneration: 1,
    kernelGeneration: "fixture",
    solar: {
      classification: "total",
      sunAngularRadius: 0.262957,
      moonAngularRadius: 0.27159,
      moonToSunRadiusRatio: 1.0328,
      centerSeparation: 0.00626,
      moonPositionAngleDeg: 70,
      eclipseMagnitude: 1.0045,
      obscuration: 1,
      solarDiscTransmission: 0,
      sourceAltitudeDeg: 4.52,
      locallyVisible: true,
      separationRateDegS: 0,
      geometryQuality: "scientific",
    },
    lunar: lunarState(),
    skyEclipseDimmingFactor: 0.06,
    sceneAppearance: {
      quality: "visual",
      strength: 1,
      saturation: 0.82,
      colorTemperatureShift: -0.12,
      contrast: 1.16,
      midtoneExposure: 0.78,
      directToDiffuseRatio: 1.2,
    },
    totalityAppearance: {
      phase: "totality",
      limbQuality: "lro_lola",
      beads: [
        { lunarPositionAngle: 75, angularWidth: 0.2, exposedPhotosphereArea: 1e-8, brightness: 0.8 },
      ],
      dominantPhotosphereRegionCount: 1,
      exposedPhotosphereArea: 1e-8,
      corona: {
        mode: "magnetic_procedural_fallback",
        quality: "approximate",
        solarNorthPositionAngleDeg: 22,
        visibility: 1,
        structures: [
          { kind: "polar_plume", positionAngleDeg: 0, angularWidthDeg: 6, radialExtentSolarRadii: 1.8, brightness: 0.5 },
          { kind: "helmet_streamer", positionAngleDeg: 90, angularWidthDeg: 30, radialExtentSolarRadii: 3.4, brightness: 0.8 },
        ],
        assetTimestampUtc: null,
        assetSha256: null,
      },
      chromosphereVisibility: 1,
      prominenceQuality: "visual/approximate",
      terrainCorrectedLimb: {
        datasetId: "nasa-cgi-moon-kit-lro-lola-ldem16",
        assetSha256: "fixture",
        sampleCount: 8,
        radiusScaleSamples: [1.001, 0.999, 1.002, 0.998, 1.0015, 0.9995, 1.001, 0.9985],
        maximumRadiusScale: 1.002,
      },
    },
    geometryQuality: "scientific",
    limbQuality: "lro_lola",
    coronaQuality: "approximate",
    appearanceQuality: "visual",
    computeMs: 1,
  };
}

function trajectoryMetadata(version: string, observerGeneration: number): ApparentTrajectoryMetadata {
  return {
    resourceId: "apparent-trajectory:sun",
    version,
    role: "apparent_trajectory",
    bodyId: "sun",
    sampleCount: 3,
    startUtc: "2026-08-12T17:00:00Z",
    endUtc: "2026-08-12T19:00:00Z",
    frame: "topocentric ENU East/Up/North",
    generation: observerGeneration,
    observerGeneration,
    kernelGeneration: "fixture",
    quality: "scientific",
    directionComponentType: "float32",
    directionComponents: 3,
    timeOffsetComponentType: "float32",
    validityComponentType: "uint8",
    directionByteOffset: 0,
    timeOffsetByteOffset: 36,
    validityByteOffset: 48,
  };
}

function trajectoryPayload(): ArrayBuffer {
  const value = new ArrayBuffer(51);
  new Float32Array(value, 0, 9).set([1, 0, 0, 0.9, 0.1, 0, 0.8, 0.2, 0]);
  new Float32Array(value, 36, 3).set([0, 3600, 7200]);
  new Uint8Array(value, 48, 3).set([1, 1, 1]);
  return value;
}

console.log("=== TerraLab3D Step 9 frontend tests ===");

const policy = new CelestialOcclusionPolicy();
const states = [body("sun", 151_000_000), body("moon", 366_000), body("mars", 300_000_000)];
policy.prepare(states);
const sunRadius = policy.preparedPresentationRadius(states[0]!);
const moonRadius = policy.preparedPresentationRadius(states[1]!);
assert(moonRadius < sunRadius, "nearer Moon receives the foreground radial layer");
near(
  policy.apparentRadius(moonRadius, states[1]!.angularRadiusDeg) / moonRadius,
  Math.sin(THREE.MathUtils.degToRad(states[1]!.angularRadiusDeg)),
  1e-15,
  "occlusion policy preserves angular radius exactly",
);
assert(
  policy.preparedRenderOrder(states[1]!) > policy.preparedRenderOrder(states[0]!),
  "foreground renders after background",
);

const trajectoryParent = new THREE.Group();
const trajectory = new ApparentTrajectoryRenderer(trajectoryParent);
assert(trajectory.registerBinaryResource(trajectoryMetadata("v1", 1), trajectoryPayload()), "first trajectory accepted");
assert(trajectory.metrics().geometryBuildCount === 1, "one persistent trajectory geometry built");
assert(!trajectory.registerBinaryResource(trajectoryMetadata("v1", 1), trajectoryPayload()), "duplicate resource is stale");
assert(trajectory.registerBinaryResource(trajectoryMetadata("v2", 2), trajectoryPayload()), "new version updates existing buffer");
assert(trajectory.metrics().geometryBuildCount === 1, "version update performs zero geometry rebuilds");
trajectory.dispose();

const moonParent = new THREE.Group();
const moon = new MoonSurfaceRenderer(moonParent, () => undefined as never);
const beforeMaterials = moon.metrics().materialBuildCount;
moon.updateEclipse(lunarState("total"));
moon.setPresentationScale(100);
moon.updateSolarOccultation(
  eventSnapshot().solar,
  new THREE.Vector3(0, 0.4, -0.916515),
  new THREE.Vector3(0.0001, 0.4, -0.916515),
  eventSnapshot().totalityAppearance.terrainCorrectedLimb,
);
const shader = {
  uniforms: {} as Record<string, unknown>,
  vertexShader: "#include <common>\n#include <normal_vertex>",
  fragmentShader: [
    "#include <common>",
    "#include <map_fragment>",
    "#include <lights_lambert_fragment>",
    "#include <lights_fragment_begin>",
    "#include <lights_fragment_maps>",
    "#include <lights_fragment_end>",
    "#include <opaque_fragment>",
  ].join("\n"),
};
moon.mesh.material.onBeforeCompile(shader as never, {} as never);
assert(shader.fragmentShader.includes("uMoonEclipseShadowOffset"), "Moon shader receives a spatial shadow offset");
assert(shader.fragmentShader.includes("moonShadowDistance"), "Moon shadow boundary is per fragment");
assert(shader.fragmentShader.includes("moonFragmentToSun"), "solar overlap is evaluated independently for each lunar fragment");
assert(shader.fragmentShader.includes("mix(moonAtmosphericOpacity, 1.0, moonOverSolarDisc)"), "only Moon pixels over the Sun become opaque");
assert(shader.fragmentShader.includes("sampleMoonTerrainLimb"), "LOLA limb profile shapes the occulting edge in the Moon shader");
assert(shader.fragmentShader.includes("terrainDisc * mix"), "terrain valleys reveal the real solar disc below");
assert("uMoonSolarOccultationEnabled" in shader.uniforms, "solar occultation is a persistent Moon uniform");
near(moon.root.scale.x, 100.2, 1e-6, "Moon geometry expands only to the persistent LOLA limb envelope");
assert(moon.metrics().materialBuildCount === beforeMaterials, "lunar eclipse changes uniforms without material rebuild");
moon.dispose();

const totalityParent = new THREE.Group();
const totality = new SolarTotalityRenderer(totalityParent);
totality.updateSun(body("sun", 151_000_000), 900_000);
totality.updateMoon(body("moon", 366_000));
totality.updateEvent(eventSnapshot());
const corona = totality.root.getObjectByName("solarCorona") as THREE.Mesh<THREE.PlaneGeometry, THREE.ShaderMaterial>;
assert(totality.root.visible, "corona appearance becomes visible only near totality");
assert(corona.material.fragmentShader.includes("finePlumes"), "corona shader has narrow polar plumes");
assert(corona.material.fragmentShader.includes("helmetStreamers"), "corona shader has broader helmet streamers");
assert(corona.material.fragmentShader.includes("innerStructure"), "inner corona is structured instead of a saturated white donut");
assert(corona.material.fragmentShader.includes("uContactIsolation"), "chromosphere can be isolated to the physical contact sector");
assert(corona.material.fragmentShader.includes("phaseArc"), "Baily and diamond phases do not draw a full chromosphere ring");
const contactEvent = eventSnapshot(2);
totality.updateEvent({
  ...contactEvent,
  totalityAppearance: {
    ...contactEvent.totalityAppearance,
    phase: "diamond_ingress",
  },
});
assert(corona.material.uniforms.uContactIsolation!.value === 1, "diamond phase isolates chromosphere around its sole photospheric region");
assert(
  Number(corona.material.uniforms.uContactHalfWidth!.value) < Math.PI / 2,
  "diamond chromosphere remains a local arc rather than a second luminous ring",
);
totality.updateEvent(eventSnapshot(2));
assert(totality.geometryBuildCount === 2 && totality.materialBuildCount === 2, "totality updates rebuild zero GPU resources");
assert(totality.root.userData.quality.corona === "approximate", "procedural corona quality remains explicit");
const earlyEvent = eventSnapshot(3);
totality.updateEvent({
  ...earlyEvent,
  solar: { ...earlyEvent.solar, classification: "partial", obscuration: 0.965 },
  totalityAppearance: {
    ...earlyEvent.totalityAppearance,
    beads: [],
    corona: { ...earlyEvent.totalityAppearance.corona, visibility: 0 },
    chromosphereVisibility: 0,
  },
});
assert(!totality.root.visible, "corona renderer stays hidden two minutes before internal contact");
totality.dispose();

const systemParent = new THREE.Group();
const system = new SolarSystemRenderer(systemParent, () => undefined as never);
system.updateSnapshot(snapshot(), 100, 0);
assert(system.updateEventSnapshot(eventSnapshot()), "coherent event generation is accepted");
const sunRoot = system.getBodyObject("sun")!;
const moonRoot = system.root.getObjectByName("moonRoot")!;
assert(moonRoot.position.length() < sunRoot.position.length(), "Moon is in front of Sun independent of creation order");
const beforeCamera = system.metrics().trajectories.geometryBuildCount;
system.updateCamera(60, 1080);
system.updateCamera(2, 1080);
assert(system.metrics().trajectories.geometryBuildCount === beforeCamera, "camera/FOV causes zero trajectory rebuilds");
const nextSystemSnapshot: SolarSystemSnapshot = {
  ...snapshot(),
  generation: 2,
  timestampUtc: "2026-08-12T18:29:59.953151Z",
  sun: { ...snapshot().sun, directionENU: [0.0002, 0.4001, -0.91647] },
  moon: { ...snapshot().moon!, directionENU: [0.0003, 0.4, -0.91647] },
};
assert(system.updateSnapshot(nextSystemSnapshot, 100, 100), "next scientific generation is accepted");
assert(system.updateEventSnapshot({
  ...eventSnapshot(2),
  timestampUtc: nextSystemSnapshot.timestampUtc,
  sourceSolarSystemGeneration: 2,
}), "matching eclipse generation is accepted atomically");
const coherentSunPosition = sunRoot.position.clone();
const coherentTotalityOrientation = system.root.getObjectByName("solarTotalityAppearance")!.quaternion.clone();
system.update(600);
near(sunRoot.position.distanceTo(coherentSunPosition), 0, 1e-9, "Sun does not drift between totality snapshots");
near(
  system.root.getObjectByName("solarTotalityAppearance")!.quaternion.angleTo(coherentTotalityOrientation),
  0,
  1e-7,
  "corona does not rotate and self-correct between coherent snapshots",
);
assert(!system.updateEventSnapshot({ ...eventSnapshot(3), sourceSolarSystemGeneration: 99 }), "temporally incoherent event is rejected");
system.dispose();

assert(skyFragmentShader.includes("u_solarDiscTransmission"), "atmospheric halo consumes solar disc transmission");
assert(skyFragmentShader.includes("u_skyEclipseDimmingFactor"), "sky consumes a distinct eclipse dimming transfer");
assert(!skyFragmentShader.includes("u_moonDirectionENU"), "Step 8.7 regression: no lunar aureole was reintroduced");
const madridClock = formatLocalAndUtcTime(
  "2026-08-12T18:29:58Z",
  "Europe/Madrid",
  "es-ES",
);
assert(madridClock.includes("20:29:58") && madridClock.includes("18:29:58 UTC"), "event clock shows CEST and UTC without a hidden two-hour offset");

console.log(`Step 9 frontend tests: ${passed} passed, ${failed} failed`);
if (failed > 0) process.exitCode = 1;
