import type { StarPickHit } from "../../../contracts/star_picking_contracts";
import { StarPickProvider } from "./StarPickProvider";
import {
  SolarSystemPickProvider,
  type SolarSystemPickHit,
} from "./SolarSystemPickProvider";

export type CelestialPickHit = StarPickHit | SolarSystemPickHit;

export interface CelestialScreenProjection {
  readonly x: number;
  readonly y: number;
  readonly visualRadiusCssPx: number;
}

export interface CelestialPickProviderDeps {
  readonly starPicker: StarPickProvider;
  readonly solarSystemPicker: SolarSystemPickProvider;
}

/**
 * Chooses one deterministic target across the independent star and Solar
 * System hit-testers. Both return CSS-pixel distances, so composition stays
 * outside their rendering responsibilities.
 */
export class CelestialPickProvider {
  constructor(private readonly deps: CelestialPickProviderDeps) {}

  pick(clientX: number, clientY: number): CelestialPickHit | null {
    const solarBody = this.deps.solarSystemPicker.pick(clientX, clientY);
    const star = this.deps.starPicker.pick(clientX, clientY);
    if (solarBody === null) return star;
    if (star === null) return solarBody;

    // A body wins exact ties: it is the visible foreground object and avoids
    // accidentally selecting a background star through the lunar disc.
    return normalizedDistance(solarBody) <= normalizedDistance(star)
      ? solarBody
      : star;
  }

  reproject(hit: CelestialPickHit): CelestialScreenProjection | null {
    if (hit.kind === "star") {
      const position = this.deps.starPicker.reprojectRef(hit.ref);
      return position === null ? null : {
        ...position,
        visualRadiusCssPx: hit.visualRadiusCssPx,
      };
    }
    return this.deps.solarSystemPicker.reproject(hit.bodyId);
  }
}

function normalizedDistance(hit: CelestialPickHit): number {
  return hit.screenDistanceCssPx / hit.hitRadiusCssPx;
}
