import type { SkyVisibilityState } from "../../../contracts/sky_environment_contracts";

const DEG_TO_RAD = Math.PI / 180.0;

export interface StarVisibilityEvaluation {
  readonly visible: boolean;
  readonly alpha: number;
  readonly effectiveLimit: number;
}

/**
 * Càlculs de visibilitat d'estrelles en CPU, reproduint
 * exactament la mateixa lògica fotomètrica i atmosfèrica que el shader GPU
 * per mantenir la coherència entre allò que es renderitza i allò que es pot clicar.
 */
export class StarVisibilityEvaluator {
  /** Llindar mínim d'alpha per considerar una estrella interactuable. */
  public static readonly MINIMUM_PICKABLE_ALPHA = 0.05;

  /**
   * Avalua si una estrella amb una magnitud i altitud donades
   * és prou visible per ser interactuable segons l'estat atmosfèric actual.
   *
   * @param magnitude Magnitud absoluta (catàleg).
   * @param altitudeDeg Altitud local sobre l'horitzó en graus [-90, +90].
   * @param state Estat actual de visibilitat (extinció, LP, crepuscle).
   */
  public static evaluate(
    magnitude: number,
    altitudeDeg: number,
    state: SkyVisibilityState,
  ): StarVisibilityEvaluation {
    const hClamp = Math.max(0.0, altitudeDeg);

    // Kasten-Young Airmass (mateixa fórmula que shader)
    const hRad = hClamp * DEG_TO_RAD;
    const denominator = Math.sin(hRad) + 0.50572 * Math.pow(hClamp + 6.07995, -1.6364);
    const airmass = denominator < 1e-5 ? 40.0 : 1.0 / denominator;

    // Límits efectius
    const effectiveLimit =
      state.zenithMagnitudeLimit -
      state.extinctionCoefficient * (airmass - 1.0) -
      state.twilightSuppression;

    // Fade suau: smoothstep(min, max, x) on x és la magnitud.
    // Com més brillant (magnitud més baixa), l'alpha s'acosta a 1.
    // min = effectiveLimit
    // max = effectiveLimit - fadeWidth
    let alpha = 0.0;
    if (magnitude < effectiveLimit - state.fadeWidthMag) {
      alpha = 1.0;
    } else if (magnitude > effectiveLimit) {
      alpha = 0.0;
    } else {
      // Interpolació smoothstep
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
