import type { BinaryResourceHandle } from "../../bridge/ScienceBridge";
import type { SceneResourceDescriptor, SceneResourceId } from "../../contracts/scene";

export interface GpuResourceRegistry {
  register(descriptor: SceneResourceDescriptor, handle: BinaryResourceHandle): Promise<void>;
  update(descriptor: SceneResourceDescriptor, handle: BinaryResourceHandle): Promise<void>;
  has(resourceId: SceneResourceId, version: number): boolean;
  dispose(resourceId: SceneResourceId, expectedVersion: number): Promise<void>;
  disposeAll(): Promise<void>;
}
