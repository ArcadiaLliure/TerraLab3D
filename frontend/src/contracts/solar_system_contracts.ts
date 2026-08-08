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
  readonly source: string;
  readonly quality: "precise" | "fallback";
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

