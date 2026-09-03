import type { SolarSystemBodyState } from "../../contracts/solar_system_contracts";

/**
 * Presentation-only depth policy for topocentric apparent bodies.
 *
 * Scientific distances decide ordering, while small radial layers keep the
 * scene numerically compact.  Scale is recomputed from the chosen radius, so
 * changing layers cannot change angular size.
 */
export class CelestialOcclusionPolicy {
  private readonly orderedStates: Pick<SolarSystemBodyState, "id" | "distanceKm">[] = [];
  private readonly preparedPresentationRadii = new Map<string, number>();
  private readonly preparedRenderOrders = new Map<string, number>();

  constructor(
    readonly baseRadius = 900_000,
    readonly maximumRadialSpan = 24_000,
  ) {}

  /** Prepare the shared depth ordering once for the current visual frame. */
  prepare(
    states: Iterable<Pick<SolarSystemBodyState, "id" | "distanceKm">>,
  ): void {
    this.orderedStates.length = 0;
    this.preparedPresentationRadii.clear();
    this.preparedRenderOrders.clear();
    for (const state of states) {
      if (Number.isFinite(state.distanceKm)) this.orderedStates.push(state);
    }
    this.orderedStates.sort((a, b) => a.distanceKm - b.distanceKm);
    const count = this.orderedStates.length;
    for (let index = 0; index < count; index++) {
      const state = this.orderedStates[index]!;
      const layersInFront = count - 1 - index;
      const normalizedDepth = count <= 1 ? 0 : layersInFront / (count - 1);
      this.preparedPresentationRadii.set(
        state.id,
        this.baseRadius - normalizedDepth * this.maximumRadialSpan,
      );
      this.preparedRenderOrders.set(state.id, -200 + layersInFront);
    }
  }

  preparedPresentationRadius(
    state: Pick<SolarSystemBodyState, "id" | "distanceKm">,
  ): number {
    return this.preparedPresentationRadii.get(state.id) ?? this.baseRadius;
  }

  preparedRenderOrder(
    state: Pick<SolarSystemBodyState, "id" | "distanceKm">,
  ): number {
    return this.preparedRenderOrders.get(state.id) ?? -200;
  }

  apparentRadius(presentationRadius: number, angularRadiusDeg: number): number {
    return presentationRadius * Math.sin(angularRadiusDeg * Math.PI / 180);
  }
}
