import * as THREE from "three";

import type {
  SolarSystemBodyId,
  SolarSystemBodyState,
} from "../../../contracts/solar_system_contracts";
import type { PickableSolarSystemBody } from "../SolarSystemRenderer";

const MINIMUM_BODY_HIT_RADIUS_CSS_PX = 10;
const BODY_HIT_TOLERANCE_CSS_PX = 5;

const worldPosition = new THREE.Vector3();
const projectedPosition = new THREE.Vector3();

export interface PickViewportRect {
  readonly left: number;
  readonly top: number;
  readonly width: number;
  readonly height: number;
}

export interface SolarSystemPickHit {
  readonly kind: "solar_system_body";
  readonly bodyId: SolarSystemBodyId;
  readonly state: SolarSystemBodyState;
  readonly screenXCssPx: number;
  readonly screenYCssPx: number;
  readonly screenDistanceCssPx: number;
  /** Apparent body radius, excluding the interaction tolerance. */
  readonly visualRadiusCssPx: number;
  readonly hitRadiusCssPx: number;
}

export interface SolarSystemPickProviderDeps {
  readonly camera: THREE.PerspectiveCamera;
  readonly getViewportRect: () => PickViewportRect;
  readonly getPickableBodies: () => readonly PickableSolarSystemBody[];
}

/**
 * Local interaction adapter for the visible Solar System meshes.
 *
 * Planet discs can be sub-pixel while still carrying a useful label, so this
 * intentionally uses their rendered centre plus a small CSS-pixel tolerance
 * instead of requiring an exact mesh-ray intersection.
 */
export class SolarSystemPickProvider {
  constructor(private readonly deps: SolarSystemPickProviderDeps) {}

  pick(clientX: number, clientY: number): SolarSystemPickHit | null {
    const viewport = this.deps.getViewportRect();
    if (viewport.width <= 0 || viewport.height <= 0) return null;

    const localX = clientX - viewport.left;
    const localY = clientY - viewport.top;
    let bestHit: SolarSystemPickHit | null = null;

    for (const body of this.deps.getPickableBodies()) {
      const projected = this.project(body, viewport);
      if (projected === null) continue;

      const dx = localX - projected.screenXCssPx;
      const dy = localY - projected.screenYCssPx;
      const distance = Math.hypot(dx, dy);
      if (distance > projected.hitRadiusCssPx) continue;

      const candidate: SolarSystemPickHit = {
        kind: "solar_system_body",
        bodyId: body.id,
        state: body.state,
        screenXCssPx: projected.screenXCssPx,
        screenYCssPx: projected.screenYCssPx,
        screenDistanceCssPx: distance,
        visualRadiusCssPx: projected.visualRadiusCssPx,
        hitRadiusCssPx: projected.hitRadiusCssPx,
      };
      if (
        bestHit === null
        || normalizedDistance(candidate) < normalizedDistance(bestHit)
      ) {
        bestHit = candidate;
      }
    }

    return bestHit;
  }

  reproject(bodyId: SolarSystemBodyId): {
    x: number;
    y: number;
    visualRadiusCssPx: number;
  } | null {
    const viewport = this.deps.getViewportRect();
    const body = this.deps.getPickableBodies().find((candidate) => candidate.id === bodyId);
    if (body === undefined) return null;
    const projected = this.project(body, viewport);
    return projected === null ? null : {
      x: projected.screenXCssPx,
      y: projected.screenYCssPx,
      visualRadiusCssPx: projected.visualRadiusCssPx,
    };
  }

  private project(
    body: PickableSolarSystemBody,
    viewport: PickViewportRect,
  ): {
    screenXCssPx: number;
    screenYCssPx: number;
    visualRadiusCssPx: number;
    hitRadiusCssPx: number;
  } | null {
    body.object.getWorldPosition(worldPosition);
    projectedPosition.copy(worldPosition).project(this.deps.camera);
    if (projectedPosition.z < -1 || projectedPosition.z > 1) return null;

    const screenXCssPx = (projectedPosition.x + 1) * viewport.width / 2;
    const screenYCssPx = (1 - projectedPosition.y) * viewport.height / 2;
    if (
      screenXCssPx < -MINIMUM_BODY_HIT_RADIUS_CSS_PX
      || screenXCssPx > viewport.width + MINIMUM_BODY_HIT_RADIUS_CSS_PX
      || screenYCssPx < -MINIMUM_BODY_HIT_RADIUS_CSS_PX
      || screenYCssPx > viewport.height + MINIMUM_BODY_HIT_RADIUS_CSS_PX
    ) return null;

    const pixelsPerRad = viewport.height / (2 * Math.tan(this.deps.camera.fov * Math.PI / 360));
    const visualRadiusCssPx = Math.PI * body.state.angularRadiusDeg / 180 * pixelsPerRad;
    return {
      screenXCssPx,
      screenYCssPx,
      visualRadiusCssPx,
      hitRadiusCssPx: Math.max(
        MINIMUM_BODY_HIT_RADIUS_CSS_PX,
        visualRadiusCssPx + BODY_HIT_TOLERANCE_CSS_PX,
      ),
    };
  }
}

function normalizedDistance(hit: SolarSystemPickHit): number {
  return hit.screenDistanceCssPx / hit.hitRadiusCssPx;
}
