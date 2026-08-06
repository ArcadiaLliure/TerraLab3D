import type { SceneDelta } from "../../contracts/scene";

export interface SceneDeltaApplier {
  currentGeneration(): number;
  apply(delta: SceneDelta): Promise<void>;
  requireFullResync(reason: string): Promise<void>;
}
