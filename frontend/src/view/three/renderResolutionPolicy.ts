const MAX_RENDER_PIXELS = 2_100_000;
const MIN_RENDER_PIXEL_RATIO = 0.75;

/**
 * Keep the WebGL backing store within a predictable fill-rate budget.
 * UI/label canvases retain their native CSS resolution; only the 3D surface
 * is scaled when a large viewport and device DPR would multiply GPU work.
 */
export function computeRenderPixelRatio(
  devicePixelRatio: number,
  widthCssPx: number,
  heightCssPx: number,
): number {
  const requested = Number.isFinite(devicePixelRatio) && devicePixelRatio > 0
    ? devicePixelRatio
    : 1;
  const cssPixels = Math.max(1, widthCssPx) * Math.max(1, heightCssPx);
  const budgetRatio = Math.sqrt(MAX_RENDER_PIXELS / cssPixels);
  return Math.min(requested, Math.max(MIN_RENDER_PIXEL_RATIO, budgetRatio));
}
