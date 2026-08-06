/**
 * requestAnimationFrame render loop with FPS measurement.
 */

import type { RenderLoop } from "./RenderLoop";

export class RenderLoopImpl implements RenderLoop {
  private rafId: number | null = null;
  private continuous = true;
  private renderFn: ((timestampMs: number) => void) | null = null;
  private frameRequested = false;

  // FPS measurement
  private frameCount = 0;
  private lastFpsTimestamp = 0;
  private _fps = 0;

  get fps(): number {
    return this._fps;
  }

  start(render: (timestampMs: number) => void): void {
    this.renderFn = render;
    this.lastFpsTimestamp = performance.now();
    this.tick(performance.now());
  }

  requestFrame(): void {
    this.frameRequested = true;
    if (this.rafId === null && this.renderFn) {
      this.tick(performance.now());
    }
  }

  setContinuous(enabled: boolean): void {
    this.continuous = enabled;
    if (enabled && this.rafId === null && this.renderFn) {
      this.tick(performance.now());
    }
  }

  stop(): void {
    if (this.rafId !== null) {
      cancelAnimationFrame(this.rafId);
      this.rafId = null;
    }
    this.renderFn = null;
  }

  // ─── Private ───────────────────────────────────────────────────────

  private tick(timestamp: number): void {
    this.rafId = null;

    if (!this.renderFn) return;

    this.renderFn(timestamp);
    this.measureFps(timestamp);

    if (this.continuous || this.frameRequested) {
      this.frameRequested = false;
      this.rafId = requestAnimationFrame((t) => this.tick(t));
    }
  }

  private measureFps(timestamp: number): void {
    this.frameCount++;
    const elapsed = timestamp - this.lastFpsTimestamp;
    if (elapsed >= 1000) {
      this._fps = Math.round((this.frameCount * 1000) / elapsed);
      this.frameCount = 0;
      this.lastFpsTimestamp = timestamp;
    }
  }
}
