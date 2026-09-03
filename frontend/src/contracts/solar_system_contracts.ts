export type KnownSolarSystemBodyId =
  | "sun"
  | "moon"
  | "mercury"
  | "venus"
  | "mars"
  | "jupiter"
  | "saturn"
  | "uranus"
  | "neptune"
  | "pluto";

export type SatelliteBodyId = `naif-${number}` | `provisional-${string}`;
export type SolarSystemBodyId = KnownSolarSystemBodyId | SatelliteBodyId;

export type PhysicalModelQuality =
  | "HIGH_PRECISION"
  | "IAU_MODEL"
  | "MEASURED"
  | "ESTIMATED"
  | "VISUAL_REFERENCE"
  | "UNAVAILABLE"
  | "OUT_OF_RANGE";

export type CoverageStatus =
  | "IN_RANGE"
  | "OUT_OF_RANGE"
  | "NO_KERNEL"
  | "AMBIGUOUS_KERNEL"
  | "ERROR";

export type LunarOrientationQuality = "precise" | "unavailable" | "out_of_range";

export interface LunarOrientationState {
  readonly frame: "MOON_ME_DE421" | string;
  readonly source: string;
  readonly quality: LunarOrientationQuality;
  /** Lunar body axes -> right-handed East/North/Up, quaternion order x/y/z/w. */
  readonly bodyToENUQuaternion: readonly [number, number, number, number] | null;
  readonly librationLongitudeDeg: number | null;
  readonly librationLatitudeDeg: number | null;
  readonly subEarthLongitudeDeg: number | null;
  readonly subEarthLatitudeDeg: number | null;
  readonly subObserverLongitudeDeg: number | null;
  readonly subObserverLatitudeDeg: number | null;
  readonly northPolePositionAngleDeg: number | null;
  readonly brightLimbPositionAngleDeg: number | null;
  /** Established TerraLab3D wire order: East, Up, North. */
  readonly moonToSunDirectionENU: readonly [number, number, number] | null;
  readonly computeMs: number;
  readonly detail: string | null;
}

export interface BodyOrientationState {
  readonly frame: string;
  readonly source: string;
  readonly quality: PhysicalModelQuality;
  /** Body-fixed axes -> right-handed East/North/Up, quaternion x/y/z/w. */
  readonly bodyToENUQuaternion: readonly [number, number, number, number] | null;
  /** Equatorial basis -> East/North/Up; excludes prime-meridian spin. */
  readonly equatorialToENUQuaternion: readonly [number, number, number, number] | null;
  readonly bodyToSunDirectionENU: readonly [number, number, number] | null;
  readonly northPoleICRF: readonly [number, number, number] | null;
  readonly computeMs: number;
  readonly detail: string | null;
}

export interface RingPlaneDiagnostics {
  readonly ringOpeningGeocentricDeg: number;
  readonly ringOpeningTopocentricDeg: number;
  readonly sunElevationAboveRingDeg: number;
}

export interface SolarSystemBodyState {
  readonly id: SolarSystemBodyId;
  readonly displayName?: string;
  readonly type: "sun" | "moon" | "planet" | "dwarf_planet" | "natural_satellite";
  readonly rightAscensionDeg: number;
  readonly declinationDeg: number;
  readonly altitudeDeg: number;
  readonly azimuthDeg: number;
  readonly directionENU: readonly [number, number, number];
  readonly distanceKm: number;
  readonly angularRadiusDeg: number;
  readonly angularDiameterDeg: number;
  readonly illuminationFraction: number;
  readonly phaseAngleDeg: number;
  readonly apparentMagnitude: number | null;
  readonly brightLimbPositionAngleDeg: number | null;
  readonly orientation: LunarOrientationState | BodyOrientationState | null;
  readonly naifId?: number;
  readonly parentNaifId?: number | null;
  readonly parentBodyId?: string | null;
  readonly positionICRFKm?: readonly [number, number, number] | null;
  readonly velocityICRFKmS?: readonly [number, number, number] | null;
  readonly radiiKm?: readonly [number, number, number] | null;
  readonly meanRadiusKm?: number | null;
  /** Established TerraLab3D wire order: East, Up, North. */
  readonly bodyToSunDirectionENU?: readonly [number, number, number] | null;
  readonly ephemerisKernelId?: string | null;
  readonly coverageStatus?: CoverageStatus;
  readonly orientationQuality?: PhysicalModelQuality;
  readonly shapeQuality?: PhysicalModelQuality;
  readonly textureQuality?: PhysicalModelQuality;
  readonly geometricElevationDeg?: number;
  readonly horizonElevationDeg?: number;
  readonly horizonVisible?: boolean;
  readonly refractionApplied?: false;
  readonly ringDiagnostics?: RingPlaneDiagnostics | null;
  readonly source: string;
  readonly quality: "precise" | "fallback";
}

export interface MoonSurfaceAsset {
  readonly role: "albedo_8k" | "albedo_4k" | "normal_4k" | string;
  readonly name: string;
  readonly url: string;
  readonly widthPx: number;
  readonly heightPx: number;
  readonly sha256: string;
  readonly byteSize: number;
}

export interface MoonSurfaceResourceDescriptor {
  readonly status: "ready" | "unavailable" | "invalid";
  readonly label: string;
  readonly datasetId: string;
  readonly version: string | null;
  readonly projection: string | null;
  readonly centralLongitudeDeg: number | null;
  readonly colorSpace: string | null;
  readonly albedo8k: MoonSurfaceAsset | null;
  readonly albedo4k: MoonSurfaceAsset | null;
  readonly normalMap: MoonSurfaceAsset | null;
  readonly credits: readonly string[];
  readonly detail: string | null;
}

export interface SolarSystemSnapshot {
  readonly generation: number;
  readonly timestampUtc: string;
  readonly observerGeneration: number;
  readonly source: "DE421" | "fallback" | string;
  readonly quality: "precise" | "fallback";
  readonly detail: string | null;
  readonly computeMs: number;
  readonly sun: SolarSystemBodyState;
  readonly moon: SolarSystemBodyState | null;
  readonly planets: readonly SolarSystemBodyState[];
  readonly satellites?: readonly SolarSystemBodyState[];
  readonly catalogCount?: number;
  readonly satelliteEphemerisCount?: number;
  readonly satelliteVisibleCount?: number;
  readonly kernelGeneration?: string | null;
  readonly kernelStatus?: string;
  readonly icrfToENUQuaternion?: readonly [number, number, number, number] | null;
}

export interface SolarSystemPreviewBodyState {
  readonly id: SolarSystemBodyId;
  /** Established TerraLab3D wire order: East, Up, North. */
  readonly directionENU: readonly [number, number, number];
  readonly altitudeDeg: number;
  readonly azimuthDeg: number;
  readonly distanceKm: number;
  readonly angularRadiusDeg: number;
  readonly illuminationFraction: number;
  readonly phaseAngleDeg: number;
  readonly apparentMagnitude: number | null;
}

export interface SolarSystemPreviewSnapshot {
  readonly generation: number;
  readonly observerGeneration: number;
  readonly bodies: readonly SolarSystemPreviewBodyState[];
}

export interface PlanetTextureAsset {
  readonly bodyId: string;
  readonly naifId: number;
  readonly role: string;
  readonly name: string;
  readonly url: string;
  readonly sha256: string;
  readonly byteSize: number;
  readonly widthPx: number;
  readonly heightPx: number;
  readonly format: string;
  readonly colorSpace: string;
  readonly projection: string;
  readonly centralMeridianDeg: number | null;
  readonly uvFlipX: boolean;
  readonly uvFlipY: boolean;
  readonly uvRotationDeg: number;
  readonly textureQuality: PhysicalModelQuality;
  readonly credits: string;
  readonly license: string;
}

export interface PlanetTextureManifest {
  readonly status: "ready" | "partial" | "unavailable" | "invalid";
  readonly manifestVersion: string | null;
  readonly textures: readonly PlanetTextureAsset[];
  readonly detail: string | null;
}

export interface SatelliteDefinition {
  readonly id: SatelliteBodyId;
  readonly naifId: number | null;
  readonly name: string | null;
  readonly displayName: string;
  readonly provisionalDesignation: string | null;
  readonly parentNaifId: number;
  readonly parentId: string;
  readonly spkKernelIds: readonly string[];
  readonly spkCoverageStartET: number | null;
  readonly spkCoverageEndET: number | null;
  readonly bodyFixedFrame: string | null;
  readonly hasOrientationModel: boolean;
  readonly radiiKm: readonly [number, number, number] | null;
  readonly meanRadiusKm: number | null;
  readonly ephemerisQuality: PhysicalModelQuality;
  readonly orientationQuality: PhysicalModelQuality;
  readonly shapeQuality: PhysicalModelQuality;
  readonly textureQuality: PhysicalModelQuality;
}

export interface SatelliteCatalogManifest {
  readonly status: "ready" | "partial" | "unavailable" | "invalid";
  readonly catalogVersion: string;
  readonly catalogDate: string;
  readonly counts: {
    readonly total: number;
    readonly byParent: Readonly<Record<string, number>>;
  };
  readonly coverage: {
    readonly withSpk: number;
    readonly withOrientation: number;
    readonly withRadius: number;
    readonly withTexture: number;
    readonly withoutSpk: readonly string[];
  };
  readonly satellites: readonly SatelliteDefinition[];
  readonly detail?: string;
}
