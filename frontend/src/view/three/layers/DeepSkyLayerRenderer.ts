import type { LayerRenderer } from "./LayerRenderer";
export interface DeepSkyLayerRenderer extends LayerRenderer {
  bindObjectCatalog(resourceId: string, version: number): void;
}
