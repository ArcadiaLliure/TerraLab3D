export type GeometryQuality = "scientific" | "fallback" | "unavailable";
export type SolarEclipseClassification = "none" | "partial" | "annular" | "total";
export type LunarEclipseClassification = "none" | "penumbral" | "partial" | "total";
export type SolarAppearancePhase =
  | "partial"
  | "baily_ingress"
  | "diamond_ingress"
  | "totality"
  | "diamond_egress"
  | "baily_egress";

export interface SolarEclipseState {
  readonly classification: SolarEclipseClassification;
  readonly sunAngularRadius: number;
  readonly moonAngularRadius: number;
  readonly moonToSunRadiusRatio: number;
  readonly centerSeparation: number;
  readonly moonPositionAngleDeg: number;
  readonly eclipseMagnitude: number;
  readonly obscuration: number;
  readonly solarDiscTransmission: number;
  readonly sourceAltitudeDeg: number;
  readonly locallyVisible: boolean;
  readonly separationRateDegS: number | null;
  readonly geometryQuality: GeometryQuality;
}

export interface LunarEclipseState {
  readonly classification: LunarEclipseClassification;
  readonly penumbraRadiusKm: number;
  readonly umbraRadiusKm: number;
  readonly moonRadiusKm: number;
  readonly shadowAxisOffsetKm: number;
  readonly penumbralMagnitude: number;
  readonly umbralMagnitude: number;
  readonly penumbraRadiusMoonRadii: number;
  readonly umbraRadiusMoonRadii: number;
  readonly shadowOffsetMoonRadii: number;
  readonly shadowOffsetPositionAngleDeg: number;
  readonly meanLunarLightTransmission: number;
  readonly sourceAltitudeDeg: number;
  readonly locallyVisible: boolean;
  readonly atmosphereEnlargementFactor: number;
  readonly geometryQuality: GeometryQuality;
}

export interface BailyBead {
  readonly lunarPositionAngle: number;
  readonly angularWidth: number;
  readonly exposedPhotosphereArea: number;
  readonly brightness: number;
}

export interface CoronaStructure {
  readonly kind:
    | "polar_plume"
    | "helmet_streamer"
    | "equatorial_streamer"
    | "mid_latitude_streamer"
    | string;
  readonly positionAngleDeg: number;
  readonly angularWidthDeg: number;
  readonly radialExtentSolarRadii: number;
  readonly brightness: number;
}

export interface SolarCoronaState {
  readonly mode: "data_driven" | "magnetic_procedural_fallback";
  readonly quality: "data_driven" | "approximate" | "unavailable";
  readonly solarNorthPositionAngleDeg: number;
  readonly visibility: number;
  readonly structures: readonly CoronaStructure[];
  readonly assetTimestampUtc: string | null;
  readonly assetSha256: string | null;
}

export interface EclipseSceneAppearance {
  readonly quality: "visual";
  readonly strength: number;
  readonly saturation: number;
  readonly colorTemperatureShift: number;
  readonly contrast: number;
  readonly midtoneExposure: number;
  readonly directToDiffuseRatio: number;
}

export interface TerrainCorrectedLimbState {
  readonly datasetId: string;
  readonly assetSha256: string | null;
  readonly sampleCount: number;
  readonly radiusScaleSamples: readonly number[];
  readonly maximumRadiusScale: number;
}

export interface SolarTotalityAppearance {
  readonly phase: SolarAppearancePhase;
  readonly limbQuality: "lro_lola" | "unavailable" | string;
  readonly beads: readonly BailyBead[];
  readonly dominantPhotosphereRegionCount: number;
  readonly exposedPhotosphereArea: number;
  readonly corona: SolarCoronaState;
  readonly chromosphereVisibility: number;
  readonly prominenceQuality: string;
  readonly terrainCorrectedLimb: TerrainCorrectedLimbState | null;
}

export interface AstronomicalEventSnapshot {
  readonly generation: number;
  readonly timestampUtc: string;
  readonly observerGeneration: number;
  readonly sourceSolarSystemGeneration: number;
  readonly kernelGeneration: string;
  readonly solar: SolarEclipseState;
  readonly lunar: LunarEclipseState;
  readonly skyEclipseDimmingFactor: number;
  readonly sceneAppearance: EclipseSceneAppearance;
  readonly totalityAppearance: SolarTotalityAppearance;
  readonly geometryQuality: GeometryQuality;
  readonly limbQuality: string;
  readonly coronaQuality: string;
  readonly appearanceQuality: "visual";
  readonly computeMs: number;
}

export interface EclipseContact {
  readonly name: "C1" | "C2" | "C3" | "C4" | "P1" | "U1" | "U2" | "U3" | "U4" | "P4" | string;
  readonly instantUtc: string;
  readonly locallyVisible: boolean;
  readonly sourceAltitudeDeg: number;
}

export interface AstronomicalEventSearchResult {
  readonly requestId: string;
  readonly eventType: "solar" | "lunar";
  readonly classification: SolarEclipseClassification | LunarEclipseClassification;
  readonly intervalStartUtc: string;
  readonly intervalEndUtc: string;
  readonly greatestUtc: string | null;
  readonly contacts: readonly EclipseContact[];
  readonly eventExists: boolean;
  readonly locallyVisible: boolean;
  readonly maximumMagnitude: number;
  readonly maximumObscuration: number | null;
  readonly observerGeneration: number;
  readonly kernelGeneration: string;
  readonly quality: GeometryQuality;
  readonly ephemerisQueryCount: number;
  readonly durationMs: number;
  readonly temporalToleranceSeconds: number;
  readonly angularToleranceDeg: number;
}

export interface ApparentTrajectoryMetadata {
  readonly resourceId: string;
  readonly version: string;
  readonly role: "apparent_trajectory";
  readonly bodyId: string;
  readonly sampleCount: number;
  readonly startUtc: string;
  readonly endUtc: string;
  readonly frame: "topocentric ENU East/Up/North";
  readonly generation: number;
  readonly observerGeneration: number;
  readonly kernelGeneration: string;
  readonly quality: GeometryQuality;
  readonly directionComponentType: "float32";
  readonly directionComponents: 3;
  readonly timeOffsetComponentType: "float32";
  readonly validityComponentType: "uint8";
  readonly directionByteOffset: number;
  readonly timeOffsetByteOffset: number;
  readonly validityByteOffset: number;
}

export interface AngularSeparationResult {
  readonly requestId: string;
  readonly bodyA: string;
  readonly bodyB: string;
  readonly timestampUtc: string;
  readonly separationDeg: number;
  readonly limbSeparationDeg: number;
  readonly quality: GeometryQuality;
  readonly kernelGeneration: string;
  readonly occultation: {
    readonly foreground: string;
    readonly background: string;
    readonly classification: "none" | "partial" | "total" | "transit";
    readonly separationDeg: number;
    readonly foregroundRadiusDeg: number;
    readonly backgroundRadiusDeg: number;
    readonly foregroundDistanceKm: number;
    readonly backgroundDistanceKm: number;
  };
}
