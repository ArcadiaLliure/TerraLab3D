import * as THREE from "three";
import type { EclipseSceneAppearance } from "../../../contracts/astronomical_event_contracts";
import type { TemporalAuthority } from "../../../contracts/temporal_scene_contracts";

import type {
  DiffuseSkyLightState,
  DirectLightState,
  LightingEnvironmentSnapshot,
} from "../../../contracts/lighting_environment_contracts";
import { threeFromEnu } from "../celestialCoordinates";
import {
  ShadowController,
  type ShadowMetrics,
  type ShadowQuality,
} from "./ShadowController";

const INTERPOLATION_MS = 1_000;
const LARGE_TIME_JUMP_MS = 120_000;

interface LightingTransition {
  readonly startedMs: number;
  readonly from: LightingEnvironmentSnapshot;
  readonly to: LightingEnvironmentSnapshot;
}

export interface SceneLightingMetrics {
  readonly sunLightBuildCount: 1;
  readonly moonLightBuildCount: 1;
  readonly diffuseLightBuildCount: 1;
  readonly snapshotApplyCount: number;
  readonly staleSnapshotCount: number;
  readonly lastBridgeBytes: number;
  readonly shadow: ShadowMetrics;
}

/** Persistent Three.js adapter for renderer-neutral local-scene lighting. */
export class SceneLightingController {
  readonly root = new THREE.Group();
  readonly sunLight = new THREE.DirectionalLight(0xffffff, 0);
  readonly moonLight = new THREE.DirectionalLight(0xffffff, 0);
  readonly diffuseSkyLight = new THREE.HemisphereLight(0x000000, 0x000000, 0);
  private readonly sunTarget = new THREE.Object3D();
  private readonly moonTarget = new THREE.Object3D();
  private readonly shadowController: ShadowController;
  private latestGeneration = 0;
  private latestAuthority: TemporalAuthority | null = null;
  private latestTimestampMs = 0;
  private displayed: LightingEnvironmentSnapshot | null = null;
  private transition: LightingTransition | null = null;
  private previousFrameTimestampMs = 0;
  private disposed = false;
  private _snapshotApplyCount = 0;
  private _staleSnapshotCount = 0;
  private _lastBridgeBytes = 0;
  private eclipseAppearance: EclipseSceneAppearance | null = null;

  constructor(scene: THREE.Scene, renderer: THREE.WebGLRenderer) {
    this.root.name = "lightingRoot";
    this.sunLight.name = "sunDirectionalLight";
    this.sunTarget.name = "sunDirectionalLightTarget";
    this.moonLight.name = "moonDirectionalLight";
    this.moonTarget.name = "moonDirectionalLightTarget";
    this.diffuseSkyLight.name = "diffuseSkyLight";
    this.sunLight.target = this.sunTarget;
    this.moonLight.target = this.moonTarget;
    this.root.add(
      this.sunLight,
      this.sunTarget,
      this.moonLight,
      this.moonTarget,
      this.diffuseSkyLight,
    );
    scene.add(this.root);
    this.shadowController = new ShadowController(
      renderer,
      this.sunLight,
      this.sunTarget,
      this.moonLight,
      this.moonTarget,
    );
    console.debug("MGP: [SceneLightingController.ts] [constructor] [Llums persistents creades]");
  }

  applySnapshot(
    snapshot: LightingEnvironmentSnapshot,
    bridgeBytes = 0,
    nowMs = performance.now(),
    authority: TemporalAuthority = "authoritative",
  ): boolean {
    if (this.disposed) return false;
    const authorityAdvances = snapshot.generation === this.latestGeneration
      && authorityRank(authority) > authorityRank(this.latestAuthority);
    if (
      snapshot.generation < this.latestGeneration
      || (snapshot.generation === this.latestGeneration && !authorityAdvances)
      || !validSnapshot(snapshot)
    ) {
      this._staleSnapshotCount++;
      return false;
    }
    const previousAuthority = this.latestAuthority;
    const timestampMs = Date.parse(snapshot.timestampUtc);
    const mustSnap = this.displayed === null
      || authority === "preview"
      || previousAuthority === "preview"
      || !Number.isFinite(timestampMs)
      || Math.abs(timestampMs - this.latestTimestampMs) > LARGE_TIME_JUMP_MS
      || this.displayed.sun.enabled !== snapshot.sun.enabled
      || this.displayed.moon.enabled !== snapshot.moon.enabled
      || this.displayed.skyDiffuse.enabled !== snapshot.skyDiffuse.enabled;
    this.latestGeneration = snapshot.generation;
    this.latestAuthority = authority;
    this.latestTimestampMs = timestampMs;
    this._snapshotApplyCount++;
    if (authority === "authoritative") this._lastBridgeBytes = bridgeBytes;
    if (mustSnap || this.displayed === null) {
      this.displayed = snapshot;
      this.transition = null;
      this.applyState(snapshot);
    } else {
      this.transition = { startedMs: nowMs, from: this.displayed, to: snapshot };
    }
    if (this._snapshotApplyCount === 1) {
      console.info(
        `MGP: [SceneLightingController.ts] [applySnapshot] [Primer snapshot generation=${snapshot.generation}]`,
      );
    }
    return true;
  }

  update(timestampMs: number, cameraPosition: THREE.Vector3): void {
    if (this.disposed) return;
    if (this.previousFrameTimestampMs > 0) {
      this.shadowController.recordFrame(timestampMs - this.previousFrameTimestampMs);
    }
    this.previousFrameTimestampMs = timestampMs;
    if (this.transition !== null) {
      const fraction = clamp01((timestampMs - this.transition.startedMs) / INTERPOLATION_MS);
      this.displayed = interpolateSnapshot(this.transition.from, this.transition.to, fraction);
      this.applyState(this.displayed);
      if (fraction >= 1) this.transition = null;
    }
    this.shadowController.updateCamera(cameraPosition, timestampMs);
  }

  setShadowQuality(quality: ShadowQuality): void {
    this.shadowController.setQuality(quality);
  }

  setEclipseAppearance(appearance: EclipseSceneAppearance): void {
    this.eclipseAppearance = appearance;
    if (this.displayed !== null) this.applyState(this.displayed);
  }

  getShadowQuality(): ShadowQuality {
    return this.shadowController.getQuality();
  }

  invalidateShadowGeometry(): void {
    this.shadowController.invalidateGeometry();
  }

  metrics(): SceneLightingMetrics {
    return {
      sunLightBuildCount: 1,
      moonLightBuildCount: 1,
      diffuseLightBuildCount: 1,
      snapshotApplyCount: this._snapshotApplyCount,
      staleSnapshotCount: this._staleSnapshotCount,
      lastBridgeBytes: this._lastBridgeBytes,
      shadow: this.shadowController.metrics(),
    };
  }

  dispose(): void {
    if (this.disposed) return;
    this.disposed = true;
    this.shadowController.dispose();
    this.root.removeFromParent();
    console.debug("MGP: [SceneLightingController.ts] [dispose] [Llums persistents retirades]");
  }

  private applyState(snapshot: LightingEnvironmentSnapshot): void {
    applyDirectLight(this.sunLight, snapshot.sun);
    applyDirectLight(this.moonLight, snapshot.moon);
    const sunDirection = threeFromEnu(snapshot.sun.directionToSourceENU).normalize();
    const moonDirection = threeFromEnu(snapshot.moon.directionToSourceENU).normalize();
    this.shadowController.applySunDirection(
      sunDirection,
      snapshot.sun.enabled && snapshot.sun.intensity > 0,
      snapshot.sun.intensity,
    );
    this.shadowController.applyMoonDirection(
      moonDirection,
      snapshot.moon.enabled && snapshot.moon.intensity > 0,
      snapshot.moon.intensity,
    );
    applyDiffuseLight(this.diffuseSkyLight, snapshot.skyDiffuse);
    if (this.eclipseAppearance !== null) {
      applyVisualEclipseAppearance(
        this.sunLight,
        this.moonLight,
        this.diffuseSkyLight,
        this.eclipseAppearance,
      );
    }
  }
}

function applyVisualEclipseAppearance(
  sun: THREE.DirectionalLight,
  moon: THREE.DirectionalLight,
  diffuse: THREE.HemisphereLight,
  appearance: EclipseSceneAppearance,
): void {
  if (appearance.strength <= 0) return;
  const saturation = Math.max(0, appearance.saturation);
  const coolShift = THREE.MathUtils.clamp(-appearance.colorTemperatureShift, 0, 1);
  for (const color of [sun.color, moon.color, diffuse.color, diffuse.groundColor]) {
    const luminance = color.r * 0.2126 + color.g * 0.7152 + color.b * 0.0722;
    color.lerp(new THREE.Color(luminance, luminance, luminance), 1 - saturation);
    color.multiply(new THREE.Color(1 - coolShift * 0.035, 1, 1 + coolShift * 0.055));
  }
  const exposure = Math.max(0, appearance.midtoneExposure);
  const ratio = Math.max(0, appearance.directToDiffuseRatio);
  const contrast = Math.max(0.1, appearance.contrast);
  sun.intensity *= exposure * ratio * contrast;
  moon.intensity *= exposure;
  diffuse.intensity *= exposure / contrast;
}

function applyDirectLight(light: THREE.DirectionalLight, state: DirectLightState): void {
  light.color.setRGB(...state.colorLinear);
  light.intensity = state.enabled ? state.intensity : 0;
}

function applyDiffuseLight(light: THREE.HemisphereLight, state: DiffuseSkyLightState): void {
  const horizon = new THREE.Color().setRGB(...state.horizonColorLinear);
  const zenith = new THREE.Color().setRGB(...state.zenithColorLinear);
  // HemisphereLight has no explicit horizon colour. Keep it an encapsulated
  // approximation by blending the shared horizon/zenith source once here.
  light.color.copy(horizon).lerp(zenith, 0.65);
  light.groundColor.setRGB(...state.groundColorLinear);
  light.intensity = state.enabled ? state.intensity : 0;
}

function interpolateSnapshot(
  start: LightingEnvironmentSnapshot,
  target: LightingEnvironmentSnapshot,
  fraction: number,
): LightingEnvironmentSnapshot {
  return {
    ...target,
    sun: interpolateDirect(start.sun, target.sun, fraction),
    moon: interpolateDirect(start.moon, target.moon, fraction),
    skyDiffuse: interpolateDiffuse(start.skyDiffuse, target.skyDiffuse, fraction),
  };
}

function interpolateDirect(
  start: DirectLightState,
  target: DirectLightState,
  fraction: number,
): DirectLightState {
  return {
    ...target,
    altitudeDeg: THREE.MathUtils.lerp(start.altitudeDeg, target.altitudeDeg, fraction),
    directionToSourceENU: interpolateDirection(
      start.directionToSourceENU,
      target.directionToSourceENU,
      fraction,
    ),
    colorLinear: interpolateColor(start.colorLinear, target.colorLinear, fraction),
    intensity: THREE.MathUtils.lerp(start.intensity, target.intensity, fraction),
  };
}

function interpolateDiffuse(
  start: DiffuseSkyLightState,
  target: DiffuseSkyLightState,
  fraction: number,
): DiffuseSkyLightState {
  return {
    ...target,
    zenithColorLinear: interpolateColor(
      start.zenithColorLinear,
      target.zenithColorLinear,
      fraction,
    ),
    horizonColorLinear: interpolateColor(
      start.horizonColorLinear,
      target.horizonColorLinear,
      fraction,
    ),
    groundColorLinear: interpolateColor(
      start.groundColorLinear,
      target.groundColorLinear,
      fraction,
    ),
    intensity: THREE.MathUtils.lerp(start.intensity, target.intensity, fraction),
  };
}

function interpolateDirection(
  start: readonly [number, number, number],
  target: readonly [number, number, number],
  fraction: number,
): readonly [number, number, number] {
  const value = new THREE.Vector3(...start).lerp(new THREE.Vector3(...target), fraction);
  if (value.lengthSq() <= 1e-12) return target;
  value.normalize();
  return [value.x, value.y, value.z];
}

function interpolateColor(
  start: readonly [number, number, number],
  target: readonly [number, number, number],
  fraction: number,
): readonly [number, number, number] {
  return [
    THREE.MathUtils.lerp(start[0], target[0], fraction),
    THREE.MathUtils.lerp(start[1], target[1], fraction),
    THREE.MathUtils.lerp(start[2], target[2], fraction),
  ];
}

function validSnapshot(snapshot: LightingEnvironmentSnapshot): boolean {
  return Number.isFinite(snapshot.generation)
    && snapshot.generation > 0
    && validDirect(snapshot.sun)
    && validDirect(snapshot.moon)
    && Number.isFinite(snapshot.skyDiffuse.intensity)
    && snapshot.skyDiffuse.intensity >= 0
    && validColor(snapshot.skyDiffuse.zenithColorLinear)
    && validColor(snapshot.skyDiffuse.horizonColorLinear)
    && validColor(snapshot.skyDiffuse.groundColorLinear);
}

function validDirect(state: DirectLightState): boolean {
  return Number.isFinite(state.altitudeDeg)
    && Number.isFinite(state.intensity)
    && state.intensity >= 0
    && validDirection(state.directionToSourceENU)
    && validColor(state.colorLinear);
}

function validDirection(value: readonly [number, number, number]): boolean {
  return value.every(Number.isFinite) && Math.hypot(...value) > 1e-12;
}

function validColor(value: readonly [number, number, number]): boolean {
  return value.every((component) => Number.isFinite(component) && component >= 0);
}

function clamp01(value: number): number {
  return Math.max(0, Math.min(1, value));
}

function authorityRank(authority: TemporalAuthority | null): number {
  if (authority === "authoritative") return 2;
  if (authority === "preview") return 1;
  return 0;
}
