import type { LayerRenderer } from "./LayerRenderer";
export interface StarLayerRenderer extends LayerRenderer {
  bindCatalog(resourceId: string, version: number): void;
  setMagnitudeLimit(magnitude: number): void;
  setPointScale(scale: number): void;
}
