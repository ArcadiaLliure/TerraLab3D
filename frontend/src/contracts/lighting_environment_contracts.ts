export type LightingIntensityKind = "physical" | "relative" | "visual";
export type DirectLightQuality = "scientific" | "approximate" | "fallback" | "unavailable";
export type DiffuseLightQuality = "scientific" | "approximate" | "fallback";

export interface DirectLightState {
  readonly enabled: boolean;
  /** Established TerraLab3D wire order: East, Up, North. */
  readonly directionToSourceENU: readonly [number, number, number];
  readonly altitudeDeg: number;
  /** Linear sRGB in the Three.js working colour space. */
  readonly colorLinear: readonly [number, number, number];
  readonly intensity: number;
  readonly intensityKind: LightingIntensityKind;
  readonly quality: DirectLightQuality;
}

export interface DiffuseSkyLightState {
  readonly enabled: boolean;
  readonly zenithColorLinear: readonly [number, number, number];
  readonly horizonColorLinear: readonly [number, number, number];
  readonly groundColorLinear: readonly [number, number, number];
  readonly intensity: number;
  readonly quality: DiffuseLightQuality;
}

export interface LightingEnvironmentSnapshot {
  readonly generation: number;
  readonly timestampUtc: string;
  readonly sourceSkyGeneration: number;
  readonly sourceSolarSystemGeneration: number;
  /** The single composable Pas 9 hook; Pas 8.7 always publishes 1.0. */
  readonly directSolarVisibilityFactor: number;
  readonly sun: DirectLightState;
  readonly moon: DirectLightState;
  readonly skyDiffuse: DiffuseSkyLightState;
  readonly exposureHint?: number;
}
