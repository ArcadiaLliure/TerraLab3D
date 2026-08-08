/**
 * requestAnimationFrame render loop with FPS measurement.
 */

import type { RenderLoop } from "./RenderLoop";

export interface FrameTimingMetrics {
  readonly p50Ms: number;
  readonly p95Ms: number;
  readonly sampleCount: number;
}

export class RenderLoopImpl implements RenderLoop {
  private rafId: number | null = null;
  private continuous = true;
  private renderFn: ((timestampMs: number) => void) | null = null;
  private frameRequested = false;

  // FPS measurement
  private frameCount = 0;
  private lastFpsTimestamp = 0;
  private _fps = 0;
  private previousFrameTimestamp = 0;
  private readonly frameTimesMs: number[] = [];

  get fps(): number {
    return this._fps;
  }

  get frameMetrics(): FrameTimingMetrics {
    return {
      p50Ms: percentile(this.frameTimesMs, 50),
      p95Ms: percentile(this.frameTimesMs, 95),
      sampleCount: this.frameTimesMs.length,
    };
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
    if (this.previousFrameTimestamp > 0) {
      this.frameTimesMs.push(timestamp - this.previousFrameTimestamp);
      if (this.frameTimesMs.length > 600) this.frameTimesMs.shift();
    }
    this.previousFrameTimestamp = timestamp;
    this.frameCount++;
    const elapsed = timestamp - this.lastFpsTimestamp;
    if (elapsed >= 1000) {
      this._fps = Math.round((this.frameCount * 1000) / elapsed);
      this.frameCount = 0;
      this.lastFpsTimestamp = timestamp;
    }
  }
}

function percentile(samples: readonly number[], percent: number): number {
  if (samples.length === 0) return 0;
  const sorted = [...samples].sort((a, b) => a - b);
  const index = Math.min(Math.floor((percent / 100) * sorted.length), sorted.length - 1);
  return sorted[index]!;
}
