import type { PickRequest, PickResult } from "../../contracts/interaction";
import type { SceneDelta } from "../../contracts/scene";

export interface ViewportSize {
  readonly widthPx: number;
  readonly heightPx: number;
  readonly devicePixelRatio: number;
}

export interface ThreeSceneHost {
  mount(container: HTMLElement, viewport: ViewportSize): Promise<void>;
  resize(viewport: ViewportSize): void;
  applyDelta(delta: SceneDelta): Promise<void>;
  render(timestampMs: number): void;
  pick(request: PickRequest): Promise<PickResult>;
  dispose(): Promise<void>;
}
