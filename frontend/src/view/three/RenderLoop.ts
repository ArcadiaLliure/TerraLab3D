export interface RenderLoop {
  start(render: (timestampMs: number) => void): void;
  requestFrame(): void;
  setContinuous(enabled: boolean): void;
  stop(): void;
}
