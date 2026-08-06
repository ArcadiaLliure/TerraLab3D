import type { LayerRenderer } from "./LayerRenderer";
export interface GalacticLayerRenderer extends LayerRenderer {
  bindMilkyWayTexture(resourceId: string, version: number): void;
  bindDustTexture(resourceId: string, version: number): void;
}
