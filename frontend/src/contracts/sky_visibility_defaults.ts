import type { SkyVisibilityState } from "./sky_environment_contracts";

/**
 * Same photometric baseline used before the first environment snapshot.
 * Rendering and picking must agree during connection/reconnection windows.
 */
export const DEFAULT_SKY_VISIBILITY: SkyVisibilityState = {
  zenithMagnitudeLimit: 7.6,
  extinctionCoefficient: 0.25,
  twilightSuppression: 0,
  fadeWidthMag: 0.75,
  skyBrightnessNormalized: 0,
};
