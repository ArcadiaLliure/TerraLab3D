/**
 * CelestialTransformState — font única de la transformació equatorial ↔ Three.js.
 *
 * Compartida entre StarFieldRenderer (qui aplica la matriu al shader)
 * i StarPickProvider (qui necessita la inversa per al picking).
 *
 * Garanties:
 * - Generació monotònica creixent (rebutja regressions)
 * - Interpola suaument la rotació via SLERP per evitar "trompicones" a salts de 100ms
 * - Inversa calculada dinàmicament a cada frame per al picking
 */

import * as THREE from "three";

const LOG_PREFIX = "MGP: [CelestialTransformState]";
const INTERPOLATION_MS = 1000;

export class CelestialTransformState {
  private _generation = 0;
  private readonly _equatorialToThree = new THREE.Matrix3();
  private readonly _threeToEquatorial = new THREE.Matrix3();
  private _valid = false;

  private _fromQuat = new THREE.Quaternion();
  private _toQuat = new THREE.Quaternion();
  private _visualQuat = new THREE.Quaternion();
  private _interpolationStartedMs = 0;

  get generation(): number {
    return this._generation;
  }

  get equatorialToThree(): THREE.Matrix3 {
    return this._equatorialToThree;
  }

  get threeToEquatorial(): THREE.Matrix3 {
    return this._threeToEquatorial;
  }

  get isValid(): boolean {
    return this._valid;
  }

  update(generation: number, matrix3x3: number[]): boolean {
    if (!matrix3x3 || matrix3x3.length !== 9) {
      return false;
    }

    if (generation <= this._generation && this._valid) {
      return false;
    }

    this._generation = generation;

    // Converteix la matriu 3x3 rebuda (row-major) a Quaternion
    const m = matrix3x3 as [number, number, number, number, number, number, number, number, number];
    const mat4 = new THREE.Matrix4().set(
      m[0], m[1], m[2], 0,
      m[3], m[4], m[5], 0,
      m[6], m[7], m[8], 0,
       0,    0,    0,   1
    );
    const newQuat = new THREE.Quaternion().setFromRotationMatrix(mat4);

    if (!this._valid) {
      this._fromQuat.copy(newQuat);
      this._toQuat.copy(newQuat);
      this._visualQuat.copy(newQuat);
      this._updateMatrices(this._visualQuat);
      this._valid = true;
    } else {
      // Inicia una nova interpolació des de l'estat *actual visualitzat* cap al nou objectiu
      this._fromQuat.copy(this._visualQuat);
      this._toQuat.copy(newQuat);
      this._interpolationStartedMs = performance.now();
    }

    return true;
  }

  interpolate(timestampMs: number): void {
    if (!this._valid) return;

    if (this._visualQuat.equals(this._toQuat)) return;

    const elapsed = timestampMs - this._interpolationStartedMs;
    const t = Math.min(1.0, Math.max(0.0, elapsed / INTERPOLATION_MS));

    // SLERP des de l'estat d'inici cap a l'objectiu
    this._visualQuat.copy(this._fromQuat).slerp(this._toQuat, t);
    
    this._updateMatrices(this._visualQuat);
  }

  private _updateMatrices(q: THREE.Quaternion): void {
    const mat4 = new THREE.Matrix4().makeRotationFromQuaternion(q);
    const e = mat4.elements;
    // THREE.Matrix4.elements és column-major, igual que Matrix3
    this._equatorialToThree.set(
      e[0], e[4], e[8],
      e[1], e[5], e[9],
      e[2], e[6], e[10]
    );
    this._threeToEquatorial.copy(this._equatorialToThree).invert();
  }

  getMatrix3x3Array(): number[] {
    const e = this._equatorialToThree.elements;
    return [
      e[0], e[3], e[6],
      e[1], e[4], e[7],
      e[2], e[5], e[8],
    ];
  }
}
