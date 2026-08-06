import type { ApplicationCommand } from "../contracts/commands";
import type { ApplicationEvent } from "../contracts/events";
import type { PickResult } from "../contracts/interaction";
import type { SceneDelta, SceneResourceId } from "../contracts/scene";

export interface BinaryResourceHandle {
  readonly resourceId: SceneResourceId;
  readonly version: number;
  readonly buffer: ArrayBuffer;
}

export interface ScienceBridge {
  connect(): Promise<void>;
  disconnect(): Promise<void>;
  onSceneDelta(listener: (delta: SceneDelta) => Promise<void> | void): () => void;
  onApplicationEvent(listener: (event: ApplicationEvent) => Promise<void> | void): () => void;
  acquireResource(resourceId: SceneResourceId, version: number): Promise<BinaryResourceHandle>;
  releaseResource(resourceId: SceneResourceId, version: number): Promise<void>;
  sendCommand(command: ApplicationCommand): Promise<void>;
  sendPickResult(result: PickResult): Promise<void>;
}
