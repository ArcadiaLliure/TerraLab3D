import type { SkyVisibilityState } from "../../../contracts/sky_environment_contracts";

const DEG_TO_RAD = Math.PI / 180.0;

export interface StarVisibilityEvaluation {
  readonly visible: boolean;
  readonly alpha: number;
  readonly effectiveLimit: number;
}

/** CPU parity for atmospheric visibility; terrain occlusion is a separate policy. */
export class StarVisibilityEvaluator {
  public static readonly MINIMUM_PICKABLE_ALPHA = 0.05;

  public static evaluate(
    magnitude: number,
    altitudeDeg: number,
    state: SkyVisibilityState,
  ): StarVisibilityEvaluation {
    const hAtmosphere = Math.max(-5.0, altitudeDeg);
    const denominator = Math.sin(hAtmosphere * DEG_TO_RAD)
      + 0.50572 * Math.pow(hAtmosphere + 6.07995, -1.6364);
    const airmass = denominator < 1e-5 ? 40.0 : 1.0 / denominator;
    const effectiveLimit = state.zenithMagnitudeLimit
      - state.extinctionCoefficient * (airmass - 1.0)
      - state.twilightSuppression;

    let alpha = 0.0;
    if (magnitude < effectiveLimit - state.fadeWidthMag) {
      alpha = 1.0;
    } else if (magnitude <= effectiveLimit) {
      const t = (magnitude - effectiveLimit) / -state.fadeWidthMag;
      alpha = t * t * (3.0 - 2.0 * t);
    }
    return {
      visible: alpha >= this.MINIMUM_PICKABLE_ALPHA,
      alpha,
      effectiveLimit,
    };
  }
}
