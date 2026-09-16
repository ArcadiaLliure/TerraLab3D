export interface Direction3 {
  readonly x: number;
  readonly y: number;
  readonly z: number;
}

const SINGULAR_EPSILON = 1e-12;

/**
 * Angle de rotació que alinea la part superior del sensor amb el nord celeste.
 *
 * El pol nord celeste ja ha d'estar transformat al marc topocèntric vigent.
 * Això incorpora latitud i temps sideral sense acoblar el càlcul a la UI.
 */
export function trackedFieldRotationDeg(
  pointing: Direction3,
  celestialNorthPole: Direction3,
): number {
  const direction = normalized(pointing);
  if (!direction) return 0;

  const localUp = projectOnTangent({ x: 0, y: 1, z: 0 }, direction);
  const celestialNorth = projectOnTangent(celestialNorthPole, direction);
  const up = normalized(localUp);
  const north = normalized(celestialNorth);
  if (!up || !north) return 0;

  const right = {
    x: direction.y * up.z - direction.z * up.y,
    y: direction.z * up.x - direction.x * up.z,
    z: direction.x * up.y - direction.y * up.x,
  };
  const angleRad = Math.atan2(dot(north, right), dot(north, up));
  return normalizeSignedDegrees(angleRad * 180 / Math.PI);
}

function projectOnTangent(vector: Direction3, normal: Direction3): Direction3 {
  const parallel = dot(vector, normal);
  return {
    x: vector.x - parallel * normal.x,
    y: vector.y - parallel * normal.y,
    z: vector.z - parallel * normal.z,
  };
}

function normalized(vector: Direction3): Direction3 | null {
  const length = Math.hypot(vector.x, vector.y, vector.z);
  if (!Number.isFinite(length) || length <= SINGULAR_EPSILON) return null;
  return { x: vector.x / length, y: vector.y / length, z: vector.z / length };
}

function dot(a: Direction3, b: Direction3): number {
  return a.x * b.x + a.y * b.y + a.z * b.z;
}

function normalizeSignedDegrees(value: number): number {
  return ((value + 180) % 360 + 360) % 360 - 180;
}
