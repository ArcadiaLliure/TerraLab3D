import * as THREE from "three";

export type ScientificEnu = readonly [east: number, up: number, north: number];

/** The only scientific ENU -> Three.js celestial-axis conversion. */
export function setThreeFromEnu(target: THREE.Vector3, enu: ScientificEnu): THREE.Vector3 {
  return target.set(enu[0], enu[1], -enu[2]);
}

export function threeFromEnu(enu: ScientificEnu): THREE.Vector3 {
  return setThreeFromEnu(new THREE.Vector3(), enu);
}

/** Shared azimuth convention: 0=N, 90=E; Three axes +X East, +Y Up, -Z North. */
export function setThreeFromAzimuthAltitude(
  target: THREE.Vector3,
  azimuthDeg: number,
  altitudeDeg: number,
  radius = 1,
): THREE.Vector3 {
  const azimuthRad = THREE.MathUtils.degToRad(azimuthDeg);
  const altitudeRad = THREE.MathUtils.degToRad(altitudeDeg);
  const horizontal = Math.cos(altitudeRad) * radius;
  return target.set(
    Math.sin(azimuthRad) * horizontal,
    Math.sin(altitudeRad) * radius,
    -Math.cos(azimuthRad) * horizontal,
  );
}

export function azimuthAltitudeFromThreeDirection(
  direction: { x: number; y: number; z: number },
): { azimuthDeg: number; altitudeDeg: number } | null {
  const length = Math.hypot(direction.x, direction.y, direction.z);
  if (length <= 0) return null;
  return {
    azimuthDeg: (Math.atan2(direction.x, -direction.z) * 180 / Math.PI + 360) % 360,
    altitudeDeg: Math.asin(Math.max(-1, Math.min(1, direction.y / length))) * 180 / Math.PI,
  };
}

const ENU_AXES_TO_THREE = new THREE.Quaternion().setFromAxisAngle(
  new THREE.Vector3(1, 0, 0),
  -Math.PI / 2,
);

/** Convert body -> right-handed East/North/Up into the one Three.js axis convention. */
export function threeQuaternionFromBodyToEnu(
  quaternion: readonly [number, number, number, number],
): THREE.Quaternion {
  const bodyToEnu = new THREE.Quaternion(...quaternion).normalize();
  return ENU_AXES_TO_THREE.clone().multiply(bodyToEnu).normalize();
}
