import * as THREE from "three";

import type { LightingEnvironmentSnapshot } from "../contracts/lighting_environment_contracts";
import type { SolarSystemBodyState } from "../contracts/solar_system_contracts";
import {
  LUNAR_INDEPENDENT_LIGHTING_CACHE_KEY,
  LUNAR_NIGHT_SIDE_VISIBILITY,
  MoonSurfaceRenderer,
  lunarAtmosphericOpacity,
} from "../view/three/MoonSurfaceRenderer";
import { threeFromEnu } from "../view/three/celestialCoordinates";
import { SceneLightingController } from "../view/three/lighting/SceneLightingController";
import { pbrDiffuseResponse } from "../view/three/materials/PBRMaterialPolicy";
import { markColorTexture, markDataTexture } from "../view/three/materials/PBRMaterialPolicy";
import { NavigationWorld } from "../view/three/terrain/NavigationWorld";
import { applyRendererColorPolicy } from "../view/three/rendererColorPolicy";
import {
  skyFragmentShader,
  solarAtmosphericHaloStrength,
} from "../view/three/shaders/skyShader";
import { STAR_FRAGMENT_SHADER } from "../view/three/shaders/starShader";
import { srgbChannelToLinear } from "../view/three/StarFieldRenderer";

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

function lightingSnapshot(
  generation: number,
  moonIntensity = 0.045,
  timestampUtc = `2026-08-09T22:00:${String(generation % 60).padStart(2, "0")}Z`,
): LightingEnvironmentSnapshot {
  return {
    generation,
    timestampUtc,
    sourceSkyGeneration: generation,
    sourceSolarSystemGeneration: generation,
    directSolarVisibilityFactor: 1,
    lunarDirectVisibilityFactor: 1,
    sun: {
      enabled: true,
      directionToSourceENU: [1, 1, 0],
      altitudeDeg: 45,
      colorLinear: [1, 0.95, 0.8],
      intensity: 2.4,
      intensityKind: "visual",
      quality: "scientific",
    },
    moon: {
      enabled: moonIntensity > 0,
      directionToSourceENU: [-1, 0.5, 0],
      altitudeDeg: 30,
      colorLinear: [0.62, 0.72, 1],
      intensity: moonIntensity,
      intensityKind: "relative",
      quality: "scientific",
    },
    skyDiffuse: {
      enabled: true,
      zenithColorLinear: [0.02, 0.1, 0.4],
      horizonColorLinear: [0.25, 0.35, 0.5],
      groundColorLinear: [0.001, 0.001, 0.001],
      intensity: 0.55,
      quality: "approximate",
    },
  };
}

function moonState(lightDirection: readonly [number, number, number]): SolarSystemBodyState {
  return {
    id: "moon",
    type: "moon",
    rightAscensionDeg: 0,
    declinationDeg: 0,
    altitudeDeg: 45,
    azimuthDeg: 180,
    directionENU: [0, 1, 0],
    distanceKm: 384_400,
    angularRadiusDeg: 0.25,
    angularDiameterDeg: 0.5,
    illuminationFraction: 0.5,
    phaseAngleDeg: 90,
    apparentMagnitude: -10,
    brightLimbPositionAngleDeg: 90,
    orientation: {
      frame: "MOON_ME_DE421",
      source: "test",
      quality: "precise",
      bodyToENUQuaternion: [0, 0, 0, 1],
      librationLongitudeDeg: 0,
      librationLatitudeDeg: 0,
      subEarthLongitudeDeg: 0,
      subEarthLatitudeDeg: 0,
      subObserverLongitudeDeg: 0,
      subObserverLatitudeDeg: 0,
      northPolePositionAngleDeg: 0,
      brightLimbPositionAngleDeg: 90,
      moonToSunDirectionENU: lightDirection,
      computeMs: 0,
      detail: null,
    },
    source: "DE421",
    quality: "precise",
  };
}

function fakeRenderer(): THREE.WebGLRenderer {
  return {
    shadowMap: {
      enabled: false,
      autoUpdate: true,
      needsUpdate: false,
      type: THREE.PCFShadowMap,
    },
  } as unknown as THREE.WebGLRenderer;
}

const colorRenderer = {
  outputColorSpace: THREE.NoColorSpace,
  toneMapping: THREE.ACESFilmicToneMapping,
  toneMappingExposure: 99,
} as unknown as THREE.WebGLRenderer;
applyRendererColorPolicy(colorRenderer);
assert(colorRenderer.outputColorSpace === THREE.SRGBColorSpace, "renderer output colour space is explicit sRGB");
assert(colorRenderer.toneMapping === THREE.NoToneMapping, "tone mapping policy is explicit and conservative");
assert(colorRenderer.toneMappingExposure === 1, "tone mapping exposure is explicit and static");
assert(
  skyFragmentShader.includes("<colorspace_fragment>")
    && STAR_FRAGMENT_SHADER.includes("<colorspace_fragment>"),
  "custom sky and star shaders perform one explicit output encoding",
);
const haloCentre = solarAtmosphericHaloStrength(0, 35, 2.5);
const haloTwoDegrees = solarAtmosphericHaloStrength(2, 35, 2.5);
const haloEightDegrees = solarAtmosphericHaloStrength(8, 35, 2.5);
assert(
  haloCentre > haloTwoDegrees && haloTwoDegrees > haloEightDegrees,
  "solar atmospheric halo falls off smoothly with angular separation",
);
assert(
  solarAtmosphericHaloStrength(0, -2, 2.5) === 0,
  "solar halo is absent while the Sun is physically below the horizon",
);
assert(
  solarAtmosphericHaloStrength(5, 35, 8) > solarAtmosphericHaloStrength(5, 35, 2),
  "turbidity broadens the solar aureole",
);
assert(
  skyFragmentShader.includes("AURÈOLA SOLAR ATMOSFÈRICA")
    && !skyFragmentShader.includes("u_moonDirection"),
  "the new atmospheric aureole is solar-only",
);
near(srgbChannelToLinear(0.5), 0.21404114048223255, 1e-12, "catalogue sRGB is decoded once before GPU upload");
const albedoProbe = markColorTexture(new THREE.Texture());
const normalProbe = markDataTexture(new THREE.Texture());
assert(albedoProbe?.colorSpace === THREE.SRGBColorSpace, "albedo textures are tagged sRGB");
assert(normalProbe?.colorSpace === THREE.NoColorSpace, "normal/data textures remain non-colour");
albedoProbe?.dispose();
normalProbe?.dispose();

const scene = new THREE.Scene();
const webgl = fakeRenderer();
const lighting = new SceneLightingController(scene, webgl);
assert(scene.children.includes(lighting.root), "lightingRoot is attached once");
assert(lighting.root.getObjectByName("sunDirectionalLight") instanceof THREE.DirectionalLight, "one persistent Sun light exists");
assert(lighting.root.getObjectByName("moonDirectionalLight") instanceof THREE.DirectionalLight, "one persistent Moon light exists");
assert(lighting.root.getObjectByName("diffuseSkyLight") instanceof THREE.HemisphereLight, "one persistent diffuse sky light exists");

assert(lighting.applySnapshot(lightingSnapshot(1), 900, 1_000), "first lighting snapshot is accepted");
lighting.update(1_000, new THREE.Vector3(10, 2, -20));
const sunTarget = lighting.root.getObjectByName("sunDirectionalLightTarget")!;
const sunDirection = lighting.sunLight.position.clone().sub(sunTarget.position).normalize();
near(
  sunDirection.distanceTo(threeFromEnu([1, 1, 0]).normalize()),
  0,
  1e-12,
  "DirectionalLight position-target preserves authoritative ENU direction",
);
assert(lighting.sunLight.intensity === 2.4, "Sun visual intensity is applied without relabelling it as lux");
assert(lighting.moonLight.intensity === 0.045, "Moon relative intensity is applied independently");
assert(!lighting.applySnapshot(lightingSnapshot(1), 900, 1_100), "stale lighting generation is discarded");
assert(lighting.metrics().staleSnapshotCount === 1, "stale lighting is measured");

for (let generation = 2; generation <= 101; generation++) {
  lighting.applySnapshot(lightingSnapshot(generation), 900, generation * 1_000);
  lighting.update(generation * 1_000 + 1_000, new THREE.Vector3(10, 2, -20));
}
const stableMetrics = lighting.metrics();
assert(stableMetrics.sunLightBuildCount === 1, "timeline never rebuilds the Sun light");
assert(stableMetrics.moonLightBuildCount === 1, "timeline never rebuilds the Moon light");
assert(stableMetrics.diffuseLightBuildCount === 1, "timeline never rebuilds diffuse light");

const scienceCountBeforeCameraMotion = lighting.metrics().snapshotApplyCount;
for (let frame = 0; frame < 120; frame++) {
  lighting.update(103_000 + frame * 16.67, new THREE.Vector3(frame * 0.1, 20, -frame * 0.2));
}
assert(
  lighting.metrics().snapshotApplyCount === scienceCountBeforeCameraMotion,
  "walk/flight/yaw/pitch/roll rendering causes zero scientific lighting snapshots",
);

lighting.setShadowQuality("off");
assert(!webgl.shadowMap.enabled && !lighting.sunLight.castShadow, "shadow quality off removes shadow rendering cost");
lighting.setShadowQuality("medium");
assert(
  webgl.shadowMap.enabled && lighting.sunLight.shadow.mapSize.x === 1024,
  "medium shadows use the documented local 1024 map",
);
lighting.setShadowQuality("high");
assert(lighting.sunLight.shadow.mapSize.x === 2048, "high shadows use the documented 2048 map");
assert(!lighting.moonLight.castShadow, "Moon shadows stay optional/off without disabling Moon light");

const worldRoot = new THREE.Group();
const navigation = new NavigationWorld();
navigation.prepare(worldRoot);
const terrain = worldRoot.getObjectByName("technical_terrain_mesh") as THREE.Mesh;
assert(terrain.material instanceof THREE.MeshStandardMaterial, "technical terrain uses MeshStandardMaterial");
const terrainMaterial = terrain.material as THREE.MeshStandardMaterial;
assert(terrainMaterial.metalness === 0 && terrainMaterial.roughness === 0.92, "terrain PBR defaults are explicit");
const referenceMeshes: THREE.Mesh[] = [];
worldRoot.traverse((object) => {
  if (object instanceof THREE.Mesh && object.name.startsWith("localReference")) referenceMeshes.push(object);
});
assert(
  referenceMeshes.length > 0 && referenceMeshes.every((mesh) => mesh.material instanceof THREE.MeshStandardMaterial),
  "only explicit local reference meshes are converted to PBR",
);
assert(navigation.metrics().pbrMaterialBuildCount === 3, "PBR materials are persistent and counted once");

const obliqueSun: readonly [number, number, number] = [0.3, 0.7, 0.65];
const flat = pbrDiffuseResponse([0, 1, 0], obliqueSun);
const northSlope = pbrDiffuseResponse([0, Math.SQRT1_2, Math.SQRT1_2], obliqueSun);
const southSlope = pbrDiffuseResponse([0, Math.SQRT1_2, -Math.SQRT1_2], obliqueSun);
const vertical = pbrDiffuseResponse([1, 0, 0], obliqueSun);
assert(
  northSlope > flat && flat > southSlope && southSlope !== vertical,
  "flat, north slope, south slope and vertical surfaces respond differently",
);

const lunarParent = new THREE.Group();
const moon = new MoonSurfaceRenderer(lunarParent);
moon.updateState(moonState([1, 0, 0]), threeFromEnu([1, 0, 0]), true);
assert(moon.root.getObjectByProperty("isLight", true) === undefined, "Moon subtree contains no scene light");
const lunarMaterial = moon.mesh.material;
assert(
  lunarMaterial.customProgramCacheKey() === LUNAR_INDEPENDENT_LIGHTING_CACHE_KEY,
  "Moon uses the independent-lighting shader variant",
);
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
lunarMaterial.onBeforeCompile(
  shaderProbe as Parameters<typeof lunarMaterial.onBeforeCompile>[0],
  {} as THREE.WebGLRenderer,
);
const lunarUniforms = shaderProbe.uniforms as Record<string, THREE.IUniform<unknown>>;
const bodySunBefore = (lunarUniforms.uMoonLightDirectionThree?.value as THREE.Vector3).clone();
const globalSun = new THREE.DirectionalLight(0xffffff, 10);
const globalMoon = new THREE.DirectionalLight(0xffffff, 5);
lunarParent.add(globalSun, globalMoon);
globalSun.intensity = 0;
globalMoon.intensity = 100;
assert(
  (lunarUniforms.uMoonLightDirectionThree?.value as THREE.Vector3).equals(bodySunBefore),
  "global Sun/Moon light changes leave the lunar phase direction unchanged",
);
assert(
  shaderProbe.fragmentShader.includes("Independent Moon -> Sun lighting")
    && !shaderProbe.fragmentShader.includes("<lights_fragment_begin>"),
  "lunar shader consumes no global light accumulation",
);
near(
  lunarAtmosphericOpacity(0),
  LUNAR_NIGHT_SIDE_VISIBILITY,
  1e-12,
  "non-illuminated lunar terrain remains atmosphere-integrated, never an opaque black ball",
);

const terrainColorBefore = terrainMaterial.color.clone();
const worldSunIntensityBefore = lighting.sunLight.intensity;
moon.updateState(moonState([-1, 0, 0]), threeFromEnu([-1, 0, 0]), true);
assert(
  terrainMaterial.color.equals(terrainColorBefore)
    && lighting.sunLight.intensity === worldSunIntensityBefore,
  "Moon Body→Sun changes cannot illuminate or mutate local terrain",
);

moon.dispose();
navigation.dispose();
lighting.dispose();
lighting.dispose();
assert(!scene.children.includes(lighting.root), "lighting dispose is idempotent and detaches its root");

console.log(`Lighting Step 8.7 tests: ${passed} passed, ${failed} failed`);
if (failed > 0) (globalThis as { process?: { exit(code: number): void } }).process?.exit(1);
