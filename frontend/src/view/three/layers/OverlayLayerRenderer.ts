import type { LayerRenderer } from "./LayerRenderer";
export interface OverlayLayerRenderer extends LayerRenderer {
  bindBatch(resourceId: string, version: number): void;
}
