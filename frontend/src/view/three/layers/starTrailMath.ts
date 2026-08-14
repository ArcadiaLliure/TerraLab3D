export const SIDEREAL_DAY_SECONDS = 86_164.0905;
export const TRAIL_REFERENCE_FOV_DEG = 100.0;
export const TRAIL_STABLE_ALPHA = 138.0 / 255.0;
export const TRAIL_LINE_WIDTH_CSS_PX = 1.0;
export const TRAIL_ANTIALIAS_RADIUS_PHYSICAL_PX = 0.5;
export const TRAIL_MAX_STARS = 20_000;
export const TRAIL_MIN_SEGMENTS = 12;
export const TRAIL_MAX_SEGMENTS = 96;

const STEREOGRAPHIC_SINGULARITY_EPSILON = 1e-6;

/** Convert elapsed UTC seconds to the matching mean sidereal rotation. */
export function exposureSecondsToSiderealRadians(
  exposureSeconds: number,
  durationSeconds = Number.POSITIVE_INFINITY,
): number {
  const safeDuration = Number.isFinite(durationSeconds)
    ? Math.max(0.0, durationSeconds)
    : Number.POSITIVE_INFINITY;
  const safeExposure = Number.isFinite(exposureSeconds)
    ? Math.max(0.0, Math.min(exposureSeconds, safeDuration))
    : 0.0;
  return safeExposure * Math.PI * 2.0 / SIDEREAL_DAY_SECONDS;
}

/**
 * Match TerraLab's stable sampling density while keeping one persistent GPU
 * resource for the complete requested exposure.
 */
export function trailSegmentCountForDuration(durationSeconds: number): number {
  const safeSeconds = Number.isFinite(durationSeconds)
    ? Math.max(0.0, durationSeconds)
    : 0.0;
  const siderealHours = safeSeconds * 24.0 / SIDEREAL_DAY_SECONDS;
  const requested = Math.floor(siderealHours * 8.0) + 4;
  return Math.max(TRAIL_MIN_SEGMENTS, Math.min(TRAIL_MAX_SEGMENTS, requested));
}

/** TerraLab's projection uses zoom=1 at its nominal 100-degree field. */
export function legacyStereographicZoom(horizontalFovDeg: number): number {
  const safeFov = Number.isFinite(horizontalFovDeg)
    ? Math.max(1e-4, horizontalFovDeg)
    : TRAIL_REFERENCE_FOV_DEG;
  return TRAIL_REFERENCE_FOV_DEG / safeFov;
}

/**
 * CPU equivalent of the trail vertex shader projection.
 *
 * Input axes are Three.js view axes: +X right, +Y up and -Z forward.
 * Output is normalized device coordinates, or null at the antipodal
 * stereographic singularity.
 */
export function projectStereographicViewDirectionToNdc(
  direction: readonly [x: number, y: number, z: number],
  horizontalFovDeg: number,
  aspect: number,
): readonly [x: number, y: number] | null {
  const length = Math.hypot(direction[0], direction[1], direction[2]);
  if (!Number.isFinite(length) || length <= 0.0) return null;

  const x = direction[0] / length;
  const y = direction[1] / length;
  const z = direction[2] / length;
  const denominator = 1.0 - z;
  if (denominator <= STEREOGRAPHIC_SINGULARITY_EPSILON) return null;

  const zoom = legacyStereographicZoom(horizontalFovDeg);
  const safeAspect = Number.isFinite(aspect) ? Math.max(1e-6, aspect) : 1.0;
  return [
    (2.0 * x / denominator) * zoom / safeAspect,
    (2.0 * y / denominator) * zoom,
  ];
}

/** Select the brightest catalog rows at or below the requested magnitude. */
export function selectTrailStarIndices(
  magnitudes: ArrayLike<number>,
  magnitudeLimit: number,
  maximumStars = TRAIL_MAX_STARS,
): Uint32Array {
  if (!Number.isFinite(magnitudeLimit) || maximumStars <= 0) {
    return new Uint32Array(0);
  }

  const selected: number[] = [];
  for (let index = 0; index < magnitudes.length; index++) {
    const magnitude = magnitudes[index]!;
    if (Number.isFinite(magnitude) && magnitude <= magnitudeLimit) {
      selected.push(index);
    }
  }

  selected.sort((left, right) => {
    const magnitudeDifference = magnitudes[left]! - magnitudes[right]!;
    return magnitudeDifference !== 0 ? magnitudeDifference : left - right;
  });
  if (selected.length > maximumStars) selected.length = maximumStars;
  return Uint32Array.from(selected);
}

export interface TrailRibbonGeometryData {
  readonly parameters: Float32Array;
  readonly indices: Uint16Array;
}

/** Build one continuous indexed ribbon shared by every star instance. */
export function buildTrailRibbonGeometryData(
  segmentCount: number,
): TrailRibbonGeometryData {
  const safeSegmentCount = Math.max(1, Math.floor(segmentCount));
  const parameters = new Float32Array((safeSegmentCount + 1) * 2 * 3);
  const indices = new Uint16Array(safeSegmentCount * 6);
  for (let point = 0; point <= safeSegmentCount; point++) {
    const trailT = point / safeSegmentCount;
    const parameterOffset = point * 6;
    parameters[parameterOffset] = trailT;
    parameters[parameterOffset + 1] = -1.0;
    parameters[parameterOffset + 2] = 0.0;
    parameters[parameterOffset + 3] = trailT;
    parameters[parameterOffset + 4] = 1.0;
    parameters[parameterOffset + 5] = 0.0;
  }

  for (let segment = 0; segment < safeSegmentCount; segment++) {
    const startLeft = segment * 2;
    const startRight = startLeft + 1;
    const endLeft = startLeft + 2;
    const endRight = startLeft + 3;
    const indexOffset = segment * 6;
    indices[indexOffset] = startLeft;
    indices[indexOffset + 1] = endLeft;
    indices[indexOffset + 2] = startRight;
    indices[indexOffset + 3] = endLeft;
    indices[indexOffset + 4] = endRight;
    indices[indexOffset + 5] = startRight;
  }
  return { parameters, indices };
}

/** Approximate resident bytes owned by the instanced trail geometry. */
export function estimateTrailGpuBytes(starCount: number, segmentCount: number): number {
  const safeSegmentCount = Math.max(0, segmentCount);
  const baseVertexBytes = safeSegmentCount > 0
    ? (safeSegmentCount + 1) * 2 * 3 * Float32Array.BYTES_PER_ELEMENT
    : 0;
  const indexBytes = safeSegmentCount * 6 * Uint16Array.BYTES_PER_ELEMENT;
  const instanceBytes = Math.max(0, starCount) * 2 * 3 * Float32Array.BYTES_PER_ELEMENT;
  return baseVertexBytes + indexBytes + instanceBytes;
}

/** Reproduce TerraLab's 24-value sRGB color buckets, returning linear-sRGB. */
export function quantizeTrailLinearChannel(linearChannel: number): number {
  const srgb = linearChannelToSrgb(Math.max(0.0, Math.min(1.0, linearChannel)));
  const sourceByte = Math.max(0, Math.min(255, Math.round(srgb * 255.0)));
  const bucketByte = Math.min(255, Math.floor(sourceByte / 24) * 24 + 15);
  return srgbChannelToLinear(bucketByte / 255.0);
}

function linearChannelToSrgb(value: number): number {
  return value <= 0.0031308
    ? value * 12.92
    : 1.055 * Math.pow(value, 1.0 / 2.4) - 0.055;
}

function srgbChannelToLinear(value: number): number {
  return value <= 0.04045
    ? value / 12.92
    : Math.pow((value + 0.055) / 1.055, 2.4);
}
