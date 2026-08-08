/**
 * Contractes tipats per a l'estat complet de l'entorn del cel,
 * atmosfera, contaminació lumínica i visibilitat.
 * 
 * Rebut via WebSocket des del backend (SkyEnvironmentSnapshot).
 */

export interface SkyVisibilityState {
  readonly zenithMagnitudeLimit: number;
  readonly extinctionCoefficient: number;
  readonly twilightSuppression: number;
  readonly fadeWidthMag: number;
  readonly skyBrightnessNormalized: number;
}

export interface SkyEnvironmentSnapshot {
  readonly generation: number;
  readonly solarSystemGeneration: number;
  
  // Solar / Twilight
  readonly sunAltitudeDeg: number;
  readonly sunAzimuthDeg: number;
  readonly sunDirectionENU: readonly [number, number, number];
  readonly twilightPhase: "day" | "civil" | "nautical" | "astronomical" | "night";
  readonly twilightFactor: number;
  
  // Atmosphere
  readonly atmosphereEnabled: boolean;
  readonly turbidity: number;
  readonly horizonHaze: number;
  
  // Light Pollution
  readonly lightPollutionEnabled: boolean;
  readonly lightPollutionMode: "automatic" | "bortle" | "magnitude";
  readonly lightPollutionSource: "dataset" | "manual_bortle" | "manual_magnitude" | "fallback" | "unavailable";
  readonly bortleClass: number | null;
  readonly sqmZenith: number | null;
  readonly configuredMagnitudeLimit: number | null;
  
  // Computed visibility parameters
  readonly visibility: SkyVisibilityState;
}
