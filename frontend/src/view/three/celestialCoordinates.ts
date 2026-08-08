import * as THREE from "three";

export type ScientificEnu = readonly [east: number, up: number, north: number];

/** The only scientific ENU -> Three.js celestial-axis conversion. */
export function setThreeFromEnu(target: THREE.Vector3, enu: ScientificEnu): THREE.Vector3 {
  return target.set(enu[0], enu[1], -enu[2]);
}

export function threeFromEnu(enu: ScientificEnu): THREE.Vector3 {
  return setThreeFromEnu(new THREE.Vector3(), enu);
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
