/**
 * Diagnostics overlay showing bridge status, FPS, and session generation.
 *
 * Pure DOM — no canvas rendering.  Shows an error banner when the bridge
 * drops instead of a black screen.
 */

import type { BridgeState, BridgeStateListener } from "../../bridge/WebSocketBridge";
import type { SolarSystemSnapshot } from "../../contracts/solar_system_contracts";
import type { SolarSystemRenderMetrics } from "../three/SolarSystemRenderer";
import type { FrameTimingMetrics } from "../three/RenderLoopImpl";

const STATE_COLORS: Record<BridgeState, string> = {
  connecting: "#f5a623",
  connected: "#4caf50",
  disconnected: "#ff5722",
  error: "#f44336",
};

export class DiagnosticsOverlay implements BridgeStateListener {
  private readonly root: HTMLDivElement;
  private readonly statusDot: HTMLDivElement;
  private readonly statusText: HTMLSpanElement;
  private readonly fpsText: HTMLSpanElement;
  private readonly sessionText: HTMLSpanElement;
  private readonly solarSystemText: HTMLSpanElement;
  private readonly errorBanner: HTMLDivElement;

  constructor() {
    // ─── Diagnostics bar (top-right) ─────────────────────────────────
    this.root = document.createElement("div");
    this.root.id = "diagnostics-overlay";
    this.root.style.cssText = `
      position: fixed;
      top: 10px;
      right: 10px;
      display: flex;
      align-items: center;
      gap: 12px;
      padding: 6px 14px;
      background: rgba(2, 4, 10, 0.75);
      backdrop-filter: blur(8px);
      border: 1px solid rgba(255,255,255,0.08);
      border-radius: 8px;
      font-family: 'Inter', 'Roboto Mono', monospace;
      font-size: 12px;
      color: #aabbcc;
      z-index: 9999;
      pointer-events: none;
      user-select: none;
    `;

    // Status dot
    this.statusDot = document.createElement("div");
    this.statusDot.style.cssText = `
      width: 8px; height: 8px; border-radius: 50%;
      background: ${STATE_COLORS.connecting};
      box-shadow: 0 0 6px ${STATE_COLORS.connecting};
      transition: background 0.3s, box-shadow 0.3s;
    `;
    this.root.appendChild(this.statusDot);

    // Status text
    this.statusText = document.createElement("span");
    this.statusText.textContent = "connecting";
    this.root.appendChild(this.statusText);

    // Separator
    const sep1 = document.createElement("span");
    sep1.textContent = "│";
    sep1.style.opacity = "0.3";
    this.root.appendChild(sep1);

    // FPS
    this.fpsText = document.createElement("span");
    this.fpsText.textContent = "-- FPS";
    this.root.appendChild(this.fpsText);

    // Separator
    const sep2 = document.createElement("span");
    sep2.textContent = "│";
    sep2.style.opacity = "0.3";
    this.root.appendChild(sep2);

    // Session
    this.sessionText = document.createElement("span");
    this.sessionText.textContent = "session: --";
    this.root.appendChild(this.sessionText);

    const sep3 = document.createElement("span");
    sep3.textContent = "│";
    sep3.style.opacity = "0.3";
    this.root.appendChild(sep3);

    this.solarSystemText = document.createElement("span");
    this.solarSystemText.textContent = "ephemeris: --";
    this.root.appendChild(this.solarSystemText);

    // ─── Error banner (center, hidden by default) ────────────────────
    this.errorBanner = document.createElement("div");
    this.errorBanner.id = "bridge-error-banner";
    this.errorBanner.style.cssText = `
      position: fixed;
      top: 50%;
      left: 50%;
      transform: translate(-50%, -50%);
      padding: 24px 40px;
      background: rgba(20, 10, 10, 0.9);
      backdrop-filter: blur(12px);
      border: 1px solid rgba(244, 67, 54, 0.4);
      border-radius: 12px;
      font-family: 'Inter', 'Roboto', sans-serif;
      font-size: 16px;
      color: #ff8a80;
      text-align: center;
      z-index: 10000;
      pointer-events: none;
      user-select: none;
      display: none;
      max-width: 400px;
    `;
    this.errorBanner.innerHTML = `
      <div style="font-size:24px;margin-bottom:8px;">⚠</div>
      <div style="font-weight:600;margin-bottom:4px;">Bridge Disconnected</div>
      <div style="font-size:13px;color:#cc8080;">Reconnecting to Python backend…</div>
    `;
  }

  mount(container: HTMLElement): void {
    container.appendChild(this.root);
    container.appendChild(this.errorBanner);
  }

  updateFps(fps: number, timing?: FrameTimingMetrics): void {
    this.fpsText.textContent = timing && timing.sampleCount > 0
      ? `${fps} FPS (${timing.p50Ms.toFixed(1)}/${timing.p95Ms.toFixed(1)} ms)`
      : `${fps} FPS`;
  }

  updateSession(sessionId: string | null): void {
    this.sessionText.textContent = sessionId
      ? `session: ${sessionId.slice(0, 8)}`
      : "session: --";
  }

  updateSolarSystem(snapshot: SolarSystemSnapshot, metrics: SolarSystemRenderMetrics): void {
    const moon = snapshot.moon === null
      ? "moon unavailable"
      : `moon ${(snapshot.moon.illuminationFraction * 100).toFixed(0)}%`;
    this.solarSystemText.textContent = [
      snapshot.source,
      `g${snapshot.generation}`,
      `sun ${snapshot.sun.altitudeDeg.toFixed(1)}°`,
      moon,
      `${metrics.lastBridgeBytes} B`,
    ].join(" · ");
  }

  // ─── BridgeStateListener ───────────────────────────────────────────

  onBridgeStateChanged(state: BridgeState, _detail?: string): void {
    const color = STATE_COLORS[state];
    this.statusDot.style.background = color;
    this.statusDot.style.boxShadow = `0 0 6px ${color}`;
    this.statusText.textContent = state;

    this.errorBanner.style.display =
      state === "disconnected" || state === "error" ? "block" : "none";
  }

  dispose(): void {
    this.root.remove();
    this.errorBanner.remove();
  }
}
