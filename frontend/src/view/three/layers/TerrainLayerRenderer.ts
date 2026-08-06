import type { LayerRenderer } from "./LayerRenderer";
export interface TerrainLayerRenderer extends LayerRenderer {
  attachTile(tileId: string, meshResourceId: string, materialResourceId: string): void;
  detachTile(tileId: string): void;
}
