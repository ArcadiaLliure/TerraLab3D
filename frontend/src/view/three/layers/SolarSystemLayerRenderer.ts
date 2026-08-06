import type { LayerRenderer } from "./LayerRenderer";
export interface SolarSystemLayerRenderer extends LayerRenderer {
  updateBodyTransforms(sceneGeneration: number): void;
}
