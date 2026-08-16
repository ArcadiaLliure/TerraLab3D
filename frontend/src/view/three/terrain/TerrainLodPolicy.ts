/**
 * Screen-space LOD policy for DEM terrain streaming chunks and surface details.
 */

export interface TerrainLodInputs {
  readonly distanceM: number;
  readonly fovDeg: number;
  readonly viewportHeightPx: number;
  readonly nativeResolutionM?: number;
}

export class TerrainLodPolicy {
  private currentTier = 0;

  /**
   * Determine the target LOD tier (0 = highest detail, 4 = coarsest).
   * Incorporates hysteresis factor to avoid flickering across boundaries.
   */
  evaluate(inputs: TerrainLodInputs): number {
    const { distanceM, fovDeg, viewportHeightPx } = inputs;
    const nativeRes = Math.max(1, inputs.nativeResolutionM ?? 10);
    if (distanceM <= 0 || viewportHeightPx <= 0) return 0;

    const fovRad = (Math.max(1, Math.min(179, fovDeg)) * Math.PI) / 180;
    const pixelSizeAtDistance = (2 * distanceM * Math.tan(fovRad / 2)) / viewportHeightPx;
    const ratio = pixelSizeAtDistance / nativeRes;

    let targetTier = 0;
    if (ratio > 16) targetTier = 4;
    else if (ratio > 8) targetTier = 3;
    else if (ratio > 4) targetTier = 2;
    else if (ratio > 2) targetTier = 1;
    else targetTier = 0;

    // Hysteresis: require 30% margin to switch
    if (targetTier > this.currentTier && ratio < Math.pow(2, targetTier) * 1.3) {
      return this.currentTier;
    }
    if (targetTier < this.currentTier && ratio > Math.pow(2, targetTier + 1) * 0.7) {
      return this.currentTier;
    }

    this.currentTier = targetTier;
    return targetTier;
  }

  reset(): void {
    this.currentTier = 0;
  }
}
