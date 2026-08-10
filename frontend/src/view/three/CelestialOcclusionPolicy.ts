import type { SolarSystemBodyState } from "../../contracts/solar_system_contracts";

/**
 * Presentation-only depth policy for topocentric apparent bodies.
 *
 * Scientific distances decide ordering, while small radial layers keep the
 * scene numerically compact.  Scale is recomputed from the chosen radius, so
 * changing layers cannot change angular size.
 */
export class CelestialOcclusionPolicy {
  constructor(
    readonly baseRadius = 900_000,
    readonly maximumRadialSpan = 24_000,
  ) {}

  presentationRadius(
    state: Pick<SolarSystemBodyState, "id" | "distanceKm">,
    states: Iterable<Pick<SolarSystemBodyState, "id" | "distanceKm">>,
  ): number {
    const ordered = [...states]
      .filter((candidate) => Number.isFinite(candidate.distanceKm))
      .sort((a, b) => a.distanceKm - b.distanceKm);
    const rank = Math.max(0, ordered.findIndex((candidate) => candidate.id === state.id));
    const layersInFront = Math.max(0, ordered.length - 1 - rank);
    const normalizedDepth = ordered.length <= 1
      ? 0
      : layersInFront / (ordered.length - 1);
    return this.baseRadius - normalizedDepth * this.maximumRadialSpan;
  }

  renderOrder(
    state: Pick<SolarSystemBodyState, "id" | "distanceKm">,
    states: Iterable<Pick<SolarSystemBodyState, "id" | "distanceKm">>,
  ): number {
    const ordered = [...states].sort((a, b) => b.distanceKm - a.distanceKm);
    return -200 + Math.max(0, ordered.findIndex((candidate) => candidate.id === state.id));
  }

  apparentRadius(presentationRadius: number, angularRadiusDeg: number): number {
    return presentationRadius * Math.sin(angularRadiusDeg * Math.PI / 180);
  }
}
