import * as THREE from "three";

export interface TerrainDistanceFogOptions {
  readonly enabled?: boolean;
  readonly color?: THREE.ColorRepresentation;
  readonly nearM?: number;
  readonly farM?: number;
}

/**
 * Terrain-only distance fog.
 *
 * Implemented directly on the terrain material via uniforms so that
 * celestial spheres (stars, Milky Way, planets, deep sky) remain
 * completely unhindered by atmospheric terrain fog.
 */
export class TerrainDistanceFog {
  private _enabled: boolean;
  private readonly _color: THREE.Color;
  private _nearM: number;
  private _farM: number;

  readonly uniforms: {
    uTerrainFogEnabled: { value: number };
    uTerrainFogColor: { value: THREE.Color };
    uTerrainFogNear: { value: number };
    uTerrainFogFar: { value: number };
  };

  constructor(options: TerrainDistanceFogOptions = {}) {
    this._enabled = options.enabled ?? true;
    this._color = new THREE.Color(options.color ?? 0x9db2c9);
    this._nearM = Math.max(0, options.nearM ?? 10_000);
    this._farM = Math.max(this._nearM + 1_000, options.farM ?? 150_000);

    this.uniforms = {
      uTerrainFogEnabled: { value: this._enabled ? 1 : 0 },
      uTerrainFogColor: { value: this._color },
      uTerrainFogNear: { value: this._nearM },
      uTerrainFogFar: { value: this._farM },
    };
  }

  get enabled(): boolean {
    return this._enabled;
  }

  set enabled(value: boolean) {
    this._enabled = value;
    this.uniforms.uTerrainFogEnabled.value = value ? 1 : 0;
  }

  get color(): THREE.Color {
    return this._color;
  }

  setColor(color: THREE.ColorRepresentation): void {
    this._color.set(color);
    this.uniforms.uTerrainFogColor.value.copy(this._color);
  }

  setRange(nearM: number, farM: number): void {
    this._nearM = Math.max(0, nearM);
    this._farM = Math.max(this._nearM + 1_000, farM);
    this.uniforms.uTerrainFogNear.value = this._nearM;
    this.uniforms.uTerrainFogFar.value = this._farM;
  }
}
