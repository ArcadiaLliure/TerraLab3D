import * as THREE from "three";

export type ScientificEnu = readonly [east: number, up: number, north: number];

/** The only scientific ENU -> Three.js celestial-axis conversion. */
export function setThreeFromEnu(target: THREE.Vector3, enu: ScientificEnu): THREE.Vector3 {
  return target.set(enu[0], enu[1], -enu[2]);
}

export function threeFromEnu(enu: ScientificEnu): THREE.Vector3 {
  return setThreeFromEnu(new THREE.Vector3(), enu);
}

