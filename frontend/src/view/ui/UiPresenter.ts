export interface StatusMessage {
  readonly code: string;
  readonly severity: "info" | "warning" | "error";
  readonly text: string;
  readonly progressFraction?: number;
}

export interface UiPresenter {
  showStatus(message: StatusMessage): void;
  clearStatus(code: string): void;
  setLayerVisibility(layerId: string, visible: boolean): void;
  setSelection(targetId: string | null, targetKind: string | null): void;
}
