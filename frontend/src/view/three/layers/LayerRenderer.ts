import type { SceneDelta } from "../../../contracts/scene";

export interface LayerRenderer {
  readonly layerId: string;
  setVisible(visible: boolean): void;
  /** Aplica només les operacions de escena propietat de la capa. */
  applyDelta(delta: SceneDelta): void;
  dispose(): void;
}
