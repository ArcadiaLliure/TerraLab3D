import type {
  TemporalAuthority,
  TemporalSceneState,
} from "../contracts/temporal_scene_contracts";

/** Latest-wins ordering for atomic temporal scene transactions. */
export class TemporalSceneCoordinator {
  private generationId = 0;
  private authority: TemporalAuthority | null = null;
  private observerGeneration = 0;

  accept(state: TemporalSceneState): boolean {
    if (!validStateIdentity(state)) return false;
    const authorityAdvances = state.generationId === this.generationId
      && authorityRank(state.authority) > authorityRank(this.authority);
    const generationAdvances = state.generationId > this.generationId;
    if (!generationAdvances && !authorityAdvances) return false;
    if (
      state.generationId === this.generationId
      && state.observerGeneration !== this.observerGeneration
    ) {
      return false;
    }
    this.generationId = state.generationId;
    this.authority = state.authority;
    this.observerGeneration = state.observerGeneration;
    return true;
  }
}

function authorityRank(authority: TemporalAuthority | null): number {
  if (authority === "authoritative") return 2;
  if (authority === "preview") return 1;
  return 0;
}

function validStateIdentity(state: TemporalSceneState): boolean {
  return Number.isInteger(state.generationId)
    && state.generationId > 0
    && Number.isInteger(state.observerGeneration)
    && state.observerGeneration > 0
    && Number.isFinite(Date.parse(state.simulationTime));
}
