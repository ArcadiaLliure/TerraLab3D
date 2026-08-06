import type { SceneDelta } from "../../../contracts/scene";

export interface MeasurementLayerRenderer {
  /** Aplica només els canvis rellevants per a aquesta capa retinguda. */
  applyDelta(delta: SceneDelta): void;
  /** Actualitza uniforms o transformacions locals sense reconstruir recursos. */
  update(timestampMs: number): void;
  /** Allibera materials, geometries i textures propietat de la capa. */
  dispose(): void;
}
