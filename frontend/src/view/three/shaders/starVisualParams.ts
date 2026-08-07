/**
 * Paràmetres visuals compartits entre shader GLSL i TypeScript per al picking.
 *
 * La fórmula de mida de punt s'ha d'aplicar idènticament al shader
 * (starShader.ts) i al picker TypeScript (StarPickProvider.ts).
 *
 * Canviar aquí → canviar al shader → canviar als tests.
 */

// ─── Constants compartides ───────────────────────────────────────────

export const STAR_VISUAL_PARAMS = {
  /** Mida mínima del punt base (device px / DPR) */
  minBaseSize: 1.8,
  /** Factor d'escala per magnitud */
  scaleFactor: 1.8,
  /** Magnitud de referència on la mida base seria zero */
  baseMagRef: 7.0,
  /** Llindar de magnitud per al boost de brillantor extra */
  brightBoostThreshold: 1.0,
  /** Factor de boost per estrelles super-brillants */
  brightBoostFactor: 4.0,
  /** Mida màxima de punt en device px */
  maxPointSize: 64.0,
  /** Mida mínima de punt en device px */
  minPointSize: 1.0,
} as const;

// ─── Paràmetres de hit radius ────────────────────────────────────────

export const STAR_HIT_PARAMS = {
  /** Radi mínim de hit en CSS px (per estrelles febles) */
  minimumHitRadiusCssPx: 6.0,
  /** Tolerància addicional al nucli visual en CSS px */
  toleranceCssPx: 3.0,
} as const;

// ─── Càlcul de mida de punt ──────────────────────────────────────────

/**
 * Calcula la mida de punt en device pixels.
 * Idèntica a la fórmula del vertex shader.
 */
export function computeStarPointSizeDevicePx(
  magnitude: number,
  pointScale: number,
  dpr: number,
): number {
  const p = STAR_VISUAL_PARAMS;
  let baseSize = Math.max(
    p.minBaseSize,
    (p.baseMagRef - magnitude) * p.scaleFactor * pointScale,
  );
  if (magnitude < p.brightBoostThreshold) {
    baseSize += (p.brightBoostThreshold - magnitude) * p.brightBoostFactor;
  }
  const devicePx = baseSize * dpr;
  return Math.max(p.minPointSize, Math.min(p.maxPointSize, devicePx));
}

/**
 * Calcula el radi visual del nucli de l'estrella en CSS px.
 */
export function computeStarVisualRadiusCssPx(
  magnitude: number,
  pointScale: number,
  dpr: number,
): number {
  const pointSizeDevicePx = computeStarPointSizeDevicePx(magnitude, pointScale, dpr);
  return pointSizeDevicePx / dpr / 2;
}

/**
 * Calcula el radi de hit en CSS px.
 * Garanteix un mínim per estrelles febles i afegeix tolerància.
 */
export function computeStarHitRadiusCssPx(
  magnitude: number,
  pointScale: number,
  dpr: number,
  minimumHitRadiusCssPx: number = STAR_HIT_PARAMS.minimumHitRadiusCssPx,
  toleranceCssPx: number = STAR_HIT_PARAMS.toleranceCssPx,
): number {
  const visualRadiusCssPx = computeStarVisualRadiusCssPx(magnitude, pointScale, dpr);
  return Math.max(minimumHitRadiusCssPx, visualRadiusCssPx + toleranceCssPx);
}
