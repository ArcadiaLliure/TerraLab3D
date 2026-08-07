/**
 * CelestialTransformState — font única de la transformació equatorial ↔ Three.js.
 *
 * Compartida entre StarFieldRenderer (qui aplica la matriu al shader)
 * i StarPickProvider (qui necessita la inversa per al picking).
 *
 * Garanties:
 * - Generació monotònica creixent (rebutja regressions)
 * - Inversa calculada una vegada quan canvia la transformació
 * - Thread-safe pel single-thread de JS
 */

import * as THREE from "three";

const LOG_PREFIX = "MGP: [CelestialTransformState]";

export class CelestialTransformState {
  private _generation = 0;
  private readonly _equatorialToThree = new THREE.Matrix3();
  private readonly _threeToEquatorial = new THREE.Matrix3();
  private _valid = false;

  /** Generació actual de la transformació. */
  get generation(): number {
    return this._generation;
  }

  /** Matriu 3×3 equatorial→Three.js (lectura directa, no copiar). */
  get equatorialToThree(): THREE.Matrix3 {
    return this._equatorialToThree;
  }

  /** Matriu 3×3 Three.js→equatorial (inversa). */
  get threeToEquatorial(): THREE.Matrix3 {
    return this._threeToEquatorial;
  }

  /** Si la transformació ha estat inicialitzada almenys una vegada. */
  get isValid(): boolean {
    return this._valid;
  }

  /**
   * Actualitza la transformació. Rebutja generacions <= a la current.
   *
   * @returns true si s'ha acceptat, false si stale/regressió.
   */
  update(generation: number, matrix3x3: number[]): boolean {
    if (!matrix3x3 || matrix3x3.length !== 9) {
      return false;
    }

    if (generation <= this._generation && this._valid) {
      return false;
    }

    this._generation = generation;

    // Aplicar la matriu (row-major)
    this._equatorialToThree.set(
      matrix3x3[0], matrix3x3[1], matrix3x3[2],
      matrix3x3[3], matrix3x3[4], matrix3x3[5],
      matrix3x3[6], matrix3x3[7], matrix3x3[8],
    );

    // Calcular la inversa
    this._threeToEquatorial.copy(this._equatorialToThree).invert();

    this._valid = true;
    return true;
  }

  /**
   * Retorna els 9 elements row-major de la matriu equatorial→Three.js
   * com a array pur per passar al shader uniforms.
   */
  getMatrix3x3Array(): number[] {
    const e = this._equatorialToThree.elements;
    // THREE.Matrix3.elements és column-major, convertir a row-major
    return [
      e[0], e[3], e[6],
      e[1], e[4], e[7],
      e[2], e[5], e[8],
    ];
  }
}
