import type * as THREE from "three";
import type { ConstellationLayerRendererImpl } from "../layers/ConstellationLayerRenderer";

export interface ConstellationPickHit {
  readonly kind: "constellation";
  readonly constellationId: string;
  readonly displayName: string;
  readonly raDeg: number;
  readonly decDeg: number;
  readonly angularRadiusDeg: number;
  readonly frame: "ICRS";
  readonly screenXCssPx: number;
  readonly screenYCssPx: number;
  readonly screenDistanceCssPx: number;
  readonly hitRadiusCssPx: number;
  readonly visualRadiusCssPx: number;
}

export class ConstellationPickProvider {
  constructor(private readonly options: {
    readonly camera: THREE.PerspectiveCamera;
    readonly renderer: ConstellationLayerRendererImpl;
    readonly getViewportRect: () => DOMRect;
  }) {}

  pick(clientX: number, clientY: number): ConstellationPickHit | null {
    const hit = this.options.renderer.pickCatalog(
      clientX,
      clientY,
      this.options.camera,
      this.options.getViewportRect(),
    );
    if (!hit) return null;
    return {
      kind: "constellation",
      constellationId: hit.entry.id,
      displayName: hit.entry.name,
      raDeg: hit.entry.center[0],
      decDeg: hit.entry.center[1],
      angularRadiusDeg: hit.entry.angularRadiusDeg,
      frame: "ICRS",
      screenXCssPx: hit.screenXCssPx,
      screenYCssPx: hit.screenYCssPx,
      screenDistanceCssPx: hit.screenDistanceCssPx,
      hitRadiusCssPx: hit.hitRadiusCssPx,
      visualRadiusCssPx: 14,
    };
  }

  reproject(constellationId: string): { x: number; y: number; visualRadiusCssPx: number } | null {
    const projected = this.options.renderer.reprojectCatalog(
      constellationId,
      this.options.camera,
      this.options.getViewportRect(),
    );
    return projected ? { ...projected, visualRadiusCssPx: 14 } : null;
  }
}
