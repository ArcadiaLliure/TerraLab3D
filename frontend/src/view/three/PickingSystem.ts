import type { PickRequest, PickResult } from "../../contracts/interaction";

export interface PickingSystem {
  pick(request: PickRequest): Promise<PickResult>;
  invalidateIndex(sceneGeneration: number): void;
  dispose(): void;
}
