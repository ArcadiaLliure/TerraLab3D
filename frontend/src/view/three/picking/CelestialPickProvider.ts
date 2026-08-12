import type { DeepSkyPickHit } from "../../../contracts/deep_sky_picking_contracts";
import type { StarPickHit } from "../../../contracts/star_picking_contracts";
import { StarPickProvider } from "./StarPickProvider";
import { DeepSkyPickProvider } from "./DeepSkyPickProvider";
import {
  SolarSystemPickProvider,
  type SolarSystemPickHit,
} from "./SolarSystemPickProvider";

export type CelestialPickHit = StarPickHit | SolarSystemPickHit | DeepSkyPickHit;

export interface CelestialScreenProjection {
  readonly x: number;
  readonly y: number;
  readonly visualRadiusCssPx: number;
}

export interface CelestialPickProviderDeps {
  readonly starPicker: StarPickProvider;
  readonly solarSystemPicker: SolarSystemPickProvider;
  readonly deepSkyPicker: DeepSkyPickProvider;
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
    const deepSky = this.deps.deepSkyPicker.pick(clientX, clientY);
    
    // Sort all non-null hits by normalized distance
    const hits = [solarBody, star, deepSky].filter((h): h is CelestialPickHit => h !== null);
    if (hits.length === 0) return null;
    
    hits.sort((a, b) => {
      const distDiff = normalizedDistance(a) - normalizedDistance(b);
      if (Math.abs(distDiff) > 1e-4) return distDiff;
      // Tie-break estable per tipus: planeta > estrella > NGC
      return getPriority(a) - getPriority(b);
    });
    return hits[0]!;
  }

  reproject(hit: CelestialPickHit): CelestialScreenProjection | null {
    if (hit.kind === "star") {
      const position = this.deps.starPicker.reprojectRef(hit.ref);
      return position === null ? null : {
        ...position,
        visualRadiusCssPx: hit.visualRadiusCssPx,
      };
    } else if (hit.kind === "deep_sky") {
      const position = this.deps.deepSkyPicker.reprojectRef(hit.ref);
      return position === null ? null : {
        ...position,
        visualRadiusCssPx: position.visualRadiusCssPx,
      };
    }
    return this.deps.solarSystemPicker.reproject(hit.bodyId);
  }
}

function normalizedDistance(hit: CelestialPickHit): number {
  return hit.screenDistanceCssPx / hit.hitRadiusCssPx;
}

function getPriority(hit: CelestialPickHit): number {
  switch (hit.kind) {
    case "solar_system_body": return 0;
    case "star": return 1;
    case "deep_sky": return 2;
    default: return 3;
  }
}
