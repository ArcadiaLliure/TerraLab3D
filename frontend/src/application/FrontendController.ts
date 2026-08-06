import type { PickResult } from "../contracts/interaction";
import type { SceneDelta } from "../contracts/scene";

export interface FrontendController {
  start(): Promise<void>;
  acceptSceneDelta(delta: SceneDelta): Promise<void>;
  publishCameraIntent(azimuthDeg: number, altitudeDeg: number, horizontalFovDeg: number): Promise<void>;
  publishPickResult(result: PickResult): Promise<void>;
  close(): Promise<void>;
}
