export type PickPurpose = "select" | "hover" | "surface";

export interface PickRequest {
  readonly requestId: string;
  readonly sceneGeneration: number;
  readonly purpose: PickPurpose;
  readonly xPx: number;
  readonly yPx: number;
}

export interface PickResult {
  readonly requestId: string;
  readonly sceneGeneration: number;
  readonly hit: boolean;
  readonly targetId?: string;
  readonly targetKind?: string;
  readonly distance?: number;
  readonly worldPosition?: readonly [number, number, number];
}
