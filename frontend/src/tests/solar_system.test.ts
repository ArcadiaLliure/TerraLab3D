import * as THREE from "three";

import type { SkyEnvironmentSnapshot } from "../contracts/sky_environment_contracts";
import type {
  LunarOrientationState,
  MoonSurfaceResourceDescriptor,
  SolarSystemBodyState,
  SolarSystemPreviewSnapshot,
  SolarSystemSnapshot,
} from "../contracts/solar_system_contracts";
import { threeFromEnu } from "../view/three/celestialCoordinates";
import {
  phaseLightDirectionThree,
  PLANET_PRESENTATIONS,
  SolarSystemRenderer,
} from "../view/three/SolarSystemRenderer";
import {
  LUNAR_INDEPENDENT_LIGHTING_CACHE_KEY,
  LUNAR_NIGHT_SIDE_VISIBILITY,
  lunarAtmosphericOpacity,
  lunarDaylightVeil,
  moonIlluminationFractionFromGeometry,
  moonLightDirectionThree,
} from "../view/three/MoonSurfaceRenderer";
import { SolarSystemPickProvider } from "../view/three/picking/SolarSystemPickProvider";
import { StarPickProvider } from "../view/three/picking/StarPickProvider";
import { CelestialTransformState } from "../view/three/CelestialTransformState";
import type { StarResourceEntry } from "../view/three/StarFieldRenderer";
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
  const angularRadiusDeg = id === "sun" ? 0.266 : id === "moon" ? 0.25 : 0.01;
  return {
    id,
    type: id === "sun" ? "sun" : id === "moon" ? "moon" : "planet",
    rightAscensionDeg: 10,
    declinationDeg: 20,
    altitudeDeg,
    azimuthDeg: 90,
    directionENU,
    distanceKm: id === "moon" ? 384_400 : 149_597_870,
    angularRadiusDeg,
    angularDiameterDeg: id === "sun" ? 0.532 : id === "moon" ? 0.5 : 0.02,
    illuminationFraction: (1 + Math.cos(THREE.MathUtils.degToRad(phaseAngleDeg))) / 2,
    phaseAngleDeg,
    apparentMagnitude: id === "sun" ? -26.7 : -4,
    brightLimbPositionAngleDeg: id === "sun" ? null : 90,
    orientation: id === "moon" ? lunarOrientation() : null,
    source: "DE421",
    quality: "precise",
    horizonElevationDeg: 0,
    horizonVisible: altitudeDeg + angularRadiusDeg > 0,
  };
}

function lunarOrientation(
  bodyToENUQuaternion: readonly [number, number, number, number] = [0, 0, 0, 1],
): LunarOrientationState {
  return {
    frame: "MOON_ME_DE421",
    source: "JPL DE421 + NAIF lunar PCK",
    quality: "precise",
    bodyToENUQuaternion,
    librationLongitudeDeg: 1.52,
    librationLatitudeDeg: -6.749,
    subEarthLongitudeDeg: 1.52,
    subEarthLatitudeDeg: -6.749,
    subObserverLongitudeDeg: 0.73,
    subObserverLatitudeDeg: -6.41,
    northPolePositionAngleDeg: 22.59,
    brightLimbPositionAngleDeg: 114.09,
    moonToSunDirectionENU: [1, 0, 0],
    computeMs: 2,
    detail: null,
  };
}

function moonResource(): MoonSurfaceResourceDescriptor {
  const asset = (
    role: "albedo_8k" | "albedo_4k" | "normal_4k",
    widthPx: number,
    heightPx: number,
  ) => ({
    role,
    name: `${role}.png`,
    url: `/moon-assets/${role}.png`,
    widthPx,
    heightPx,
    sha256: role.repeat(8).slice(0, 64),
    byteSize: 1024,
  });
  return {
    status: "ready",
    label: "LRO 2025 8K",
    datasetId: "nasa-cgi-moon-kit-lro-lola",
    version: "LROC color map 2025",
    projection: "global equirectangular/cylindrical",
    centralLongitudeDeg: 0,
    colorSpace: "sRGB",
    albedo8k: asset("albedo_8k", 8192, 4096),
    albedo4k: asset("albedo_4k", 4096, 2048),
    normalMap: asset("normal_4k", 4096, 2048),
    credits: ["NASA's Scientific Visualization Studio"],
    detail: null,
  };
}

function skyEnvironment(
  twilightFactor: number,
  atmosphereEnabled = true,
  horizonHaze = 0.3,
): SkyEnvironmentSnapshot {
  return {
    generation: 1,
    solarSystemGeneration: 1,
    sunAltitudeDeg: twilightFactor === 0 ? 20 : -20,
    sunAzimuthDeg: 180,
    sunDirectionENU: [0, 1, 0],
    twilightPhase: twilightFactor === 0 ? "day" : "night",
    twilightFactor,
    solarDiscTransmission: 1,
    skyEclipseDimmingFactor: 1,
    atmosphereEnabled,
    turbidity: 2.5,
    horizonHaze,
    lightPollutionEnabled: true,
    lightPollutionMode: "bortle",
    lightPollutionSource: "manual_bortle",
    bortleClass: 4,
    sqmZenith: 20.5,
    configuredMagnitudeLimit: 6,
    visibility: {
      zenithMagnitudeLimit: 6,
      extinctionCoefficient: 0.25,
      twilightSuppression: 0,
      fadeWidthMag: 0.75,
      skyBrightnessNormalized: 1 - twilightFactor,
    },
    zenithColorLinear: [0.02, 0.1, 0.4],
    horizonColorLinear: [0.25, 0.35, 0.5],
    groundColorLinear: [0.001, 0.001, 0.001],
    skyDiffuseIntensity: atmosphereEnabled ? 0.5 : 0,
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
assert(renderer.metrics().entityBuildCount === 10, "Sun, Moon and eight persistent planetary entities are built");
assert(renderer.metrics().geometryBuildCount === 4, "shared bodies, Moon, Saturn rings and satellite batch are built once");
assert(renderer.metrics().materialBuildCount === 13, "persistent body, ring and satellite materials are built once");

assert(renderer.updateSnapshot(snapshot(1, "2024-01-01T00:00:00Z"), 2048, 1_000), "first snapshot accepted");
const firstLabelRevision = renderer.labelRevision;
assert(firstLabelRevision > 0, "accepted snapshot invalidates solar-system labels");
assert(renderer.getBodyObject("sun")?.visible === true, "sun above horizon is visible");
assert(renderer.getBodyObject("moon")?.visible === true, "moon above horizon is visible");
near(
  renderer.getBodyObject("sun")!.scale.x,
  renderer.getBodyObject("sun")!.position.length() * Math.sin(THREE.MathUtils.degToRad(0.266)),
  1e-9,
  "sphere scale preserves the scientific angular radius",
);
assert(renderer.metrics().lastBridgeBytes === 2048, "compact bridge byte count is retained");

const previewParent = new THREE.Group();
const previewRenderer = new SolarSystemRenderer(previewParent);
const previewSatellite: SolarSystemBodyState = {
  ...body("venus", [0.25, 0.5, 1]),
  id: "naif-501",
  type: "natural_satellite",
  parentBodyId: "jupiter",
  parentNaifId: 599,
  naifId: 501,
};
previewRenderer.updateSnapshot({
  ...snapshot(1, "2024-01-01T00:00:00Z"),
  satellites: [previewSatellite],
}, 100, 0);
const preview: SolarSystemPreviewSnapshot = {
  generation: 1,
  observerGeneration: 1,
  bodies: [
    {
      id: "sun",
      directionENU: [0, 0.5, 1],
      altitudeDeg: 30,
      azimuthDeg: 0,
      distanceKm: 149_597_870,
      angularRadiusDeg: 0.266,
      illuminationFraction: 1,
      phaseAngleDeg: 0,
      apparentMagnitude: -26.74,
    },
    {
      id: "naif-501",
      directionENU: [-1, 0.25, 0],
      altitudeDeg: 14,
      azimuthDeg: 270,
      distanceKm: 628_000_000,
      angularRadiusDeg: 0,
      illuminationFraction: 0.75,
      phaseAngleDeg: 60,
      apparentMagnitude: null,
    },
  ],
};
assert(previewRenderer.updatePreviewSnapshot(preview), "timeline preview is applied immediately");
near(
  previewRenderer.getBodyObject("sun")!.position.clone().normalize()
    .distanceTo(threeFromEnu(preview.bodies[0]!.directionENU).normalize()),
  0,
  1e-9,
  "timeline preview moves the Sun before the authoritative snapshot arrives",
);
const previewDisplayed = (
  previewRenderer as unknown as {
    displayed: Map<SolarSystemBodyState["id"], SolarSystemBodyState>;
  }
).displayed;
assert(
  previewDisplayed.get("naif-501")?.directionENU[0] === -1,
  "timeline preview also moves active natural satellites",
);
assert(
  previewDisplayed.get("naif-501")?.angularRadiusDeg === previewSatellite.angularRadiusDeg,
  "unknown preview radii do not make natural satellites disappear",
);
assert(
  !previewRenderer.updatePreviewSnapshot(preview),
  "duplicate timeline preview generations are rejected",
);
assert(previewRenderer.metrics().geometryBuildCount === 4, "timeline preview rebuilds no geometry");
previewRenderer.updateSnapshot(snapshot(2, "2024-01-01T12:00:00Z"), 100, 100);
assert(
  previewRenderer.updatePreviewSnapshot(preview),
  "an authoritative snapshot resets preview sequencing for the next drag",
);
previewRenderer.dispose();

const before = renderer.getBodyObject("sun")!.position.clone().normalize();
const next = snapshot(2, "2024-01-01T00:00:01Z");
const movedSun = body("sun", [0, 0.5, 1]);
const moving = { ...next, sun: movedSun };
renderer.updateSnapshot(moving, 1900, 2_000);
renderer.update(2_050);
assert(renderer.labelRevision > firstLabelRevision, "visual interpolation keeps labels synchronized");
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
const belowHorizon = { ...partialHorizon, altitudeDeg: -1, horizonVisible: false };
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
assert(renderer.metrics().entityBuildCount === 10, "timeline updates do not rebuild entities");
assert(renderer.metrics().geometryBuildCount === 4, "timeline updates do not rebuild geometry");
assert(renderer.metrics().materialBuildCount === 13, "timeline updates do not rebuild materials");

renderer.dispose();
assert(!parent.children.includes(renderer.root), "dispose detaches the root");

const loadedUrls: string[] = [];
const loadedTextures: THREE.Texture[] = [];
let disposedTextures = 0;
const fakeTextureLoad = (
  url: string,
  onLoad: (texture: THREE.Texture) => void,
  _onError: (error: unknown) => void,
): void => {
  const texture = new THREE.Texture();
  texture.addEventListener("dispose", () => disposedTextures++);
  loadedUrls.push(url);
  loadedTextures.push(texture);
  onLoad(texture);
};
const moonParent = new THREE.Group();
const texturedRenderer = new SolarSystemRenderer(moonParent, fakeTextureLoad);
texturedRenderer.configureMoonSurface(moonResource(), 4096);
assert(loadedUrls[0]?.endsWith("albedo_4k.png") === true, "4K fallback is selected for a 4096 texture limit");
assert(loadedUrls[1]?.endsWith("normal_4k.png") === true, "LOLA normal map is loaded once when supported");
texturedRenderer.updateSnapshot(snapshot(1, "2024-01-01T00:00:00Z"), 1600, 1_000);
assert(texturedRenderer.metrics().moon.surfaceApplied, "LRO surface is applied only with precise body orientation");
assert(
  texturedRenderer.getBodyObject("moon")?.visible === false,
  "the neutral fallback is hidden once the LRO albedo is ready",
);
assert(
  texturedRenderer.getLabelAnchor("moon")?.visible === true,
  "the Moon label stays anchored while its visual layer changes",
);
const activeMoonObject = texturedRenderer.getPickableBodies()
  .find((candidate) => candidate.id === "moon")?.object as THREE.Mesh;
const activeMoonMaterial = activeMoonObject.material as THREE.MeshLambertMaterial;
assert(
  activeMoonMaterial.transparent
    && !activeMoonMaterial.depthWrite
    && activeMoonMaterial.emissive.getHex() === 0x000000
    && activeMoonMaterial.color.getHex() === 0xffffff
    && activeMoonMaterial.customProgramCacheKey() === LUNAR_INDEPENDENT_LIGHTING_CACHE_KEY,
  "the LRO material restores the Pas 8 atmospheric phase transparency without fill light",
);
near(
  lunarAtmosphericOpacity(0),
  LUNAR_NIGHT_SIDE_VISIBILITY,
  1e-12,
  "the lunar night side restores the exact 0.015 visibility from commit 439b9f6",
);
near(lunarAtmosphericOpacity(0.5), 0.515, 1e-12, "phase alpha preserves the Pas 8 direct-light formula");
near(lunarAtmosphericOpacity(1), 1, 1e-12, "phase alpha is clamped at full illumination");
near(lunarDaylightVeil(skyEnvironment(0)), 0.3, 1e-12, "daylight haze whitens the lunar albedo");
near(lunarDaylightVeil(skyEnvironment(1)), 0, 1e-12, "night preserves the unmodified LRO albedo");
near(lunarDaylightVeil(skyEnvironment(0, false)), 0, 1e-12, "disabled atmosphere adds no lunar veil");
const shaderProbe = {
  uniforms: {},
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
activeMoonMaterial.onBeforeCompile(
  shaderProbe as Parameters<typeof activeMoonMaterial.onBeforeCompile>[0],
  {} as THREE.WebGLRenderer,
);
assert(
  shaderProbe.fragmentShader.includes("moonDirectLight + 0.015")
    && shaderProbe.fragmentShader.includes("uMoonDaylightNeutral")
    && shaderProbe.fragmentShader.includes("Independent Moon -> Sun lighting")
    && !shaderProbe.fragmentShader.includes("<lights_fragment_begin>"),
  "the compiled lunar material keeps atmospheric alpha and ignores all scene-light accumulation",
);
const shaderUniforms = shaderProbe.uniforms as Record<string, THREE.IUniform<unknown>>;
texturedRenderer.updateEnvironment(skyEnvironment(0));
near(
  shaderUniforms.uMoonDaylightVeil?.value as number,
  0.3,
  1e-12,
  "the authoritative sky snapshot reaches the persistent lunar material",
);
const uploadBytes = texturedRenderer.metrics().moon.textureUploadBytes;
assert(uploadBytes > 0, "estimated persistent GPU upload bytes are recorded");

const moonMesh = texturedRenderer.getBodyObject("moon")!;
assert(
  moonMesh.parent?.parent?.parent?.getObjectByProperty("isLight", true) === undefined,
  "the Moon subtree owns no Three.js light and cannot leak Body→Sun light onto terrain",
);
const calibration = moonMesh.parent!;
const bodyXAxis = new THREE.Vector3(1, 0, 0).applyQuaternion(calibration.quaternion);
const bodyNorth = new THREE.Vector3(0, 1, 0).applyQuaternion(calibration.quaternion);
const bodyEast = new THREE.Vector3(0, 0, -1).applyQuaternion(calibration.quaternion);
near(bodyXAxis.x, 1, 1e-12, "fixed UV calibration keeps longitude zero on body +X");
near(bodyNorth.z, 1, 1e-12, "fixed UV calibration maps image north to lunar +Z");
near(bodyEast.y, 1, 1e-12, "fixed UV calibration maps increasing U to east-positive lunar +Y");
const calibrationBefore = calibration.quaternion.clone();

const rotatedMoon = {
  ...body("moon", [0, 0.5, 1]),
  orientation: lunarOrientation([0, 0, Math.SQRT1_2, Math.SQRT1_2]),
};
texturedRenderer.updateSnapshot(
  { ...snapshot(2, "2024-01-01T00:00:01Z", 2), moon: rotatedMoon },
  1600,
  2_000,
);
assert(calibration.quaternion.equals(calibrationBefore), "dataset calibration never changes with date or observer");
assert(texturedRenderer.metrics().moon.albedoTextureLoadCount === 1, "timeline does not reload lunar albedo");
assert(texturedRenderer.metrics().moon.normalTextureLoadCount === 1, "timeline does not reload lunar normals");
assert(texturedRenderer.metrics().moon.textureUploadBytes === uploadBytes, "timeline does not re-upload lunar textures");
assert(texturedRenderer.metrics().moon.bridgeTextureBytes === 0, "texture bytes never cross the bridge");

const unavailableOrientationMoon = { ...body("moon", [0, 0.5, 1]), orientation: null };
texturedRenderer.updateSnapshot(
  { ...snapshot(3, "2024-01-01T00:00:02Z", 3), moon: unavailableOrientationMoon },
  1600,
  3_000,
);
assert(!texturedRenderer.metrics().moon.surfaceApplied, "missing orientation retains the honest Step 8 fallback");
assert(
  texturedRenderer.getBodyObject("moon")?.visible === true,
  "missing orientation still leaves the persistent Moon fallback visible",
);

const preciseLightMoon = {
  ...body("moon", [0, 0.5, 1]),
  orientation: { ...lunarOrientation(), moonToSunDirectionENU: [0, 1, 0] as const },
};
near(
  moonLightDirectionThree(preciseLightMoon, new THREE.Vector3(1, 0, 0)).y,
  1,
  1e-12,
  "precise lunar phase uses the Moon-to-Sun ephemeris direction",
);
const crescentGeometryMoon = {
  ...body("moon", [0, 0, 1]),
  orientation: {
    ...lunarOrientation(),
    moonToSunDirectionENU: [Math.sqrt(3) / 2, 0, 0.5] as const,
  },
};
near(
  moonIlluminationFractionFromGeometry(crescentGeometryMoon)!,
  0.25,
  1e-12,
  "geometric Moon terminator preserves the ephemeris illumination fraction",
);
let completePhaseSweepIsCorrect = true;
for (let phaseAngleDeg = 0; phaseAngleDeg <= 180; phaseAngleDeg++) {
  const phaseAngleRad = THREE.MathUtils.degToRad(phaseAngleDeg);
  const expectedIllumination = (1 + Math.cos(phaseAngleRad)) / 2;
  for (const limbDirection of [-1, 1] as const) {
    const phaseMoon = {
      ...body("moon", [0, 0, 1]),
      orientation: {
        ...lunarOrientation(),
        moonToSunDirectionENU: [
          limbDirection * Math.sin(phaseAngleRad),
          0,
          -Math.cos(phaseAngleRad),
        ] as const,
      },
    };
    const actualIllumination = moonIlluminationFractionFromGeometry(phaseMoon);
    const actualLightDirection = moonLightDirectionThree(
      phaseMoon,
      new THREE.Vector3(7, 8, 9),
    );
    const expectedLightDirection = new THREE.Vector3(
      limbDirection * Math.sin(phaseAngleRad),
      0,
      Math.cos(phaseAngleRad),
    );
    if (
      actualIllumination === null
      || Math.abs(actualIllumination - expectedIllumination) > 1e-12
      || actualLightDirection.distanceTo(expectedLightDirection) > 1e-12
    ) completePhaseSweepIsCorrect = false;
  }
}
assert(
  completePhaseSweepIsCorrect,
  "all lunar phases from 0° to 180° preserve illumination for both limb directions",
);
texturedRenderer.dispose();
assert(disposedTextures === loadedTextures.length, "shutdown disposes every loaded Moon texture");

const highResolutionUrls: string[] = [];
const highResolutionRenderer = new SolarSystemRenderer(
  new THREE.Group(),
  (url, onLoad) => {
    highResolutionUrls.push(url);
    onLoad(new THREE.Texture());
  },
);
highResolutionRenderer.configureMoonSurface(moonResource(), 8192);
assert(highResolutionUrls[0]?.endsWith("albedo_8k.png") === true, "8K albedo is selected only when GPU capability permits it");
highResolutionRenderer.dispose();

const unsupportedUrls: string[] = [];
const unsupportedRenderer = new SolarSystemRenderer(
  new THREE.Group(),
  (url) => { unsupportedUrls.push(url); },
);
unsupportedRenderer.configureMoonSurface(moonResource(), 2048);
assert(unsupportedUrls.length === 0, "no oversized texture is loaded when even 4K is unsupported");
assert(unsupportedRenderer.metrics().moon.surfaceStatus === "unavailable", "unsupported texture size has an explicit fallback status");
unsupportedRenderer.dispose();

const pickRoot = new THREE.Group();
const pickRenderer = new SolarSystemRenderer(pickRoot);
const pickedSun = body("sun", [0, 0, 1]);
const pickedMoon = body("moon", [1, 0, 0]);
const pickedVenus = body("venus", [-1, 0, 0]);
pickRenderer.updateSnapshot({
  ...snapshot(1, "2024-01-01T00:00:00Z"),
  sun: pickedSun,
  moon: pickedMoon,
  planets: [pickedVenus],
}, 1200, 1_000);
const pickableIds = pickRenderer.getPickableBodies().map((candidate) => candidate.id);
assert(pickableIds.includes("sun"), "Sun is exposed to the interaction layer when visible");
assert(pickableIds.includes("moon"), "Moon fallback is exposed to the interaction layer when visible");
assert(pickableIds.includes("venus"), "visible planets are exposed to the interaction layer");

const pickCamera = new THREE.PerspectiveCamera(60, 1000 / 600, 0.01, 2_000_000);
pickCamera.position.set(0, 0, 0);
pickCamera.lookAt(0, 0, -1);
pickCamera.updateProjectionMatrix();
pickCamera.updateMatrixWorld(true);
pickRoot.updateMatrixWorld(true);
const solarPicker = new SolarSystemPickProvider({
  camera: pickCamera,
  getViewportRect: () => ({ left: 0, top: 0, width: 1000, height: 600 }),
  getPickableBodies: () => pickRenderer.getPickableBodies(),
});
const sunPick = solarPicker.pick(500, 300);
assert(sunPick?.kind === "solar_system_body" && sunPick.bodyId === "sun", "screen-space picking selects the Sun at its rendered centre");
assert(solarPicker.reproject("sun")?.x === 500, "selected Solar body reprojects for the persistent marker");
const wideFovProjection = solarPicker.reproject("sun")!;
pickCamera.fov = 10;
pickCamera.updateProjectionMatrix();
pickCamera.updateMatrixWorld(true);
const narrowFovProjection = solarPicker.reproject("sun")!;
assert(
  narrowFovProjection.visualRadiusCssPx > wideFovProjection.visualRadiusCssPx * 5,
  "Solar selection radius follows the apparent disc when the FOV narrows",
);
pickRenderer.dispose();

const starTransform = new CelestialTransformState();
starTransform.update(1, [1, 0, 0, 0, 1, 0, 0, 0, 1]);
const starCamera = new THREE.PerspectiveCamera(60, 1000 / 600, 0.01, 2_000_000);
const starDirection = new THREE.Vector3(0, 0.5, -Math.sqrt(0.75));
starCamera.lookAt(starDirection);
starCamera.updateProjectionMatrix();
starCamera.updateMatrixWorld(true);
const starGeometry = new THREE.BufferGeometry();
const starMaterial = new THREE.ShaderMaterial();
const starEntry: StarResourceEntry = {
  resourceId: "test-stars",
  version: "1",
  role: "general",
  starCount: 1,
  points: new THREE.Points(starGeometry, starMaterial),
  geometry: starGeometry,
  material: starMaterial,
  catalogIndices: new Uint32Array([0]),
  magnitudesArray: new Float32Array([0]),
  equatorialPositions: new Float32Array(starDirection.toArray()),
};
const starResources = new Map([[starEntry.resourceId, starEntry]]);
const starPicker = new StarPickProvider({
  camera: starCamera,
  transformState: starTransform,
  renderer: {
    domElement: { getBoundingClientRect: () => ({ left: 0, top: 0, width: 1000, height: 600 }) },
    getPixelRatio: () => 1,
  } as unknown as THREE.WebGLRenderer,
  worldRoot: new THREE.Group(),
  getStarResources: () => starResources,
  getMagnitudeLimit: () => 8,
  getSkyVisibilityState: () => null,
  getPointScale: () => 1,
  isStarLayerVisible: () => true,
});
const restoredStarPick = starPicker.pick(500, 300);
assert(
  restoredStarPick?.kind === "star" && restoredStarPick.ref.catalogIndex === 0,
  "star picking self-heals a missing spatial index and uses the render visibility baseline",
);
starPicker.dispose();
starGeometry.dispose();
starMaterial.dispose();

console.log(`Solar system tests: ${passed} passed, ${failed} failed`);
if (failed > 0) (globalThis as { process?: { exit(code: number): void } }).process?.exit(1);
