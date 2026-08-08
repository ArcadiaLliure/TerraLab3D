export type SolarSystemBodyId =
  | "sun"
  | "moon"
  | "mercury"
  | "venus"
  | "mars"
  | "jupiter"
  | "saturn"
  | "uranus"
  | "neptune";

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

export interface SolarSystemBodyState {
  readonly id: SolarSystemBodyId;
  readonly type: "sun" | "moon" | "planet";
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
  readonly apparentMagnitude: number;
  readonly brightLimbPositionAngleDeg: number | null;
  readonly orientation: LunarOrientationState | null;
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
}
