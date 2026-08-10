import * as THREE from "three";

export type TextureUv = readonly [u: number, v: number];

const EQUATORIAL_TO_GALACTIC = new THREE.Matrix3().set(
  -0.0548755604, -0.8734370902, -0.4838350155,
   0.4941094279, -0.4448296300,  0.7469822445,
  -0.8676661490, -0.1980763734,  0.4559837762,
);

/**
 * NASA SVS 4851 after Three.js EXR decoding.
 *
 * The source image stores north on its top row, but EXRLoader reverses scanlines
 * into WebGL texture order. Consequently GPU v increases with declination.
 * RA=0 remains at the horizontal centre and RA grows to the left.
 */
export function milkyWayUvFromRaDec(raDeg: number, decDeg: number): TextureUv {
  const raTurns = raDeg / 360;
  const u = wrap01(0.5 - raTurns);
  const v = 0.5 + clamp(decDeg, -90, 90) / 180;
  return [u, v];
}

export function equatorialDirectionFromRaDec(raDeg: number, decDeg: number): THREE.Vector3 {
  const ra = THREE.MathUtils.degToRad(raDeg);
  const dec = THREE.MathUtils.degToRad(clamp(decDeg, -90, 90));
  const cosDec = Math.cos(dec);
  return new THREE.Vector3(
    cosDec * Math.cos(ra),
    cosDec * Math.sin(ra),
    Math.sin(dec),
  );
}

/** UV of the locally-derived Planck texture (Galactic l/b, top row b=+90°). */
export function planckUvFromEquatorialDirection(direction: THREE.Vector3): TextureUv {
  const galactic = direction.clone().normalize().applyMatrix3(EQUATORIAL_TO_GALACTIC);
  const longitude = Math.atan2(galactic.y, galactic.x);
  const latitude = Math.asin(clamp(galactic.z, -1, 1));
  return [wrap01(longitude / (Math.PI * 2)), 0.5 - latitude / Math.PI];
}

function wrap01(value: number): number {
  const wrapped = value - Math.floor(value);
  return wrapped === 1 ? 0 : wrapped;
}

function clamp(value: number, minimum: number, maximum: number): number {
  return Math.max(minimum, Math.min(maximum, value));
}
