import type { LayerRenderer } from "./LayerRenderer";
export interface SkyLayerRenderer extends LayerRenderer {
  setSiderealRotation(rotationRad: number): void;
  setSunDirection(direction: readonly [number, number, number]): void;
}
