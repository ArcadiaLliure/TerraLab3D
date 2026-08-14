import type { WebSocketBridge } from "../../../bridge/WebSocketBridge";
import type { StarTrailsSnapshotMessage } from "../../../contracts/bridge_messages";

export class StarTrailsPanel {
  private element: HTMLDivElement;
  private stateLabel: HTMLSpanElement;
  private metricsLabel: HTMLDivElement;
  
  private btnStart: HTMLButtonElement;
  private btnPauseResume: HTMLButtonElement;
  private btnStop: HTMLButtonElement;
  private btnClear: HTMLButtonElement;

  private currentState: string = "idle";
  private currentReason?: string;

  constructor(private bridge: WebSocketBridge) {
    this.element = document.createElement("div");
    this.element.style.cssText = `
      background: var(--color-surface-raised);
      border: 1px solid var(--color-border);
      border-radius: var(--border-radius-md);
      padding: 10px;
      display: flex;
      flex-direction: column;
      gap: 8px;
      margin-top: 12px;
    `;

    const headerRow = document.createElement("div");
    headerRow.style.cssText = "display: flex; justify-content: space-between; align-items: center;";
    
    const title = document.createElement("div");
    title.style.cssText = "font-weight: 600; color: var(--color-gold); font-size: 11px;";
    title.textContent = "Traces Circumpolars (Star Trails)";
    headerRow.appendChild(title);

    this.stateLabel = document.createElement("span");
    this.stateLabel.style.cssText = "font-size: 10px; padding: 2px 6px; border-radius: 4px; background: #333; color: #ccc;";
    this.stateLabel.textContent = "IDLE";
    headerRow.appendChild(this.stateLabel);
    
    this.element.appendChild(headerRow);

    const infoText = document.createElement("div");
    infoText.style.cssText = "font-size: 11px; color: var(--color-text-dim); margin-bottom: 8px;";
    infoText.textContent = "Les traces s'esbossaran en funció del temps de simulació, permetent anar endavant i enrere per previsualitzar l'exposició.";
    this.element.appendChild(infoText);

    // Controls Row
    const controlsRow = document.createElement("div");
    controlsRow.style.cssText = "display: flex; gap: 6px; margin-top: 4px;";
    
    const buttonStyle = `
      padding: 4px 8px;
      background: var(--color-surface, #1a1a1a);
      color: var(--color-text);
      border: 1px solid var(--color-border);
      border-radius: 4px;
      cursor: pointer;
      font-size: 10px;
      flex: 1;
      position: relative;
      z-index: 10;
      pointer-events: auto;
    `;
    
    this.btnStart = document.createElement("button");
    this.btnStart.textContent = "Inicia";
    this.btnStart.style.cssText = buttonStyle;
    this.btnStart.onmouseenter = () => { if(!this.btnStart.disabled) this.btnStart.style.background = "#444"; };
    this.btnStart.onmouseleave = () => { this.btnStart.style.background = "var(--color-surface, #1a1a1a)"; };
    this.btnStart.addEventListener("click", (e) => {
      e.stopPropagation();
      console.log("[StarTrails] Botó INICIA premut.");
      // 24 hours (86400), 60 sec intervals, mag 6.0 (naked-eye visual limit) + planets, 1.0x playback speed
      this.bridge.startStarTrails(86400, 60, 6.0, 1.0);
    });
    controlsRow.appendChild(this.btnStart);
    
    this.btnPauseResume = document.createElement("button");
    this.btnPauseResume.textContent = "Pausa";
    this.btnPauseResume.style.cssText = buttonStyle;
    this.btnPauseResume.disabled = true;
    this.btnPauseResume.onmouseenter = () => { if(!this.btnPauseResume.disabled) this.btnPauseResume.style.background = "#444"; };
    this.btnPauseResume.onmouseleave = () => { this.btnPauseResume.style.background = "var(--color-surface, #1a1a1a)"; };
    this.btnPauseResume.addEventListener("click", (e) => {
      e.stopPropagation();
      if (this.currentState === "running") this.bridge.pauseStarTrails();
      else if (this.currentState === "paused") this.bridge.resumeStarTrails();
    });
    controlsRow.appendChild(this.btnPauseResume);
    
    this.btnStop = document.createElement("button");
    this.btnStop.textContent = "Atura";
    this.btnStop.style.cssText = buttonStyle;
    this.btnStop.disabled = true;
    this.btnStop.onmouseenter = () => { if(!this.btnStop.disabled) this.btnStop.style.background = "#444"; };
    this.btnStop.onmouseleave = () => { this.btnStop.style.background = "var(--color-surface, #1a1a1a)"; };
    this.btnStop.addEventListener("click", (e) => {
      e.stopPropagation();
      this.bridge.stopStarTrails();
    });
    controlsRow.appendChild(this.btnStop);
    
    this.btnClear = document.createElement("button");
    this.btnClear.textContent = "Neteja";
    this.btnClear.style.cssText = buttonStyle;
    this.btnClear.disabled = true;
    this.btnClear.onmouseenter = () => { if(!this.btnClear.disabled) this.btnClear.style.background = "#444"; };
    this.btnClear.onmouseleave = () => { this.btnClear.style.background = "var(--color-surface, #1a1a1a)"; };
    this.btnClear.addEventListener("click", (e) => {
      e.stopPropagation();
      this.bridge.clearStarTrails();
    });
    controlsRow.appendChild(this.btnClear);
    
    this.element.appendChild(controlsRow);
    
    // Metrics
    this.metricsLabel = document.createElement("div");
    this.metricsLabel.style.cssText = "font-size: 10px; color: var(--color-text-dim); margin-top: 4px; white-space: pre-wrap;";
    this.element.appendChild(this.metricsLabel);
    
    this.updateUI("idle");
  }
  
  public getElement(): HTMLElement {
    return this.element;
  }
  
  public updateSnapshot(snapshot: StarTrailsSnapshotMessage): void {
    this.currentState = snapshot.state;
    this.currentReason = snapshot.reason;
    this.updateUI(snapshot.state);
    
    if (snapshot.state !== "idle") {
      const mb = (snapshot.gpuBytes / (1024 * 1024)).toFixed(1);
      const time = this.formatDuration(snapshot.accumulatedExposureSeconds);
      
      let text = `Estrelles: ${snapshot.starCount.toLocaleString()}\n`;
      text += `Segments: ${snapshot.segmentCount.toLocaleString()} (${mb} MB VRAM)\n`;
      text += `Exposició: ${time}`;
      
      if (this.currentReason) {
        text += `\nNota: ${this.currentReason}`;
      }
      this.metricsLabel.textContent = text;
    } else {
      this.metricsLabel.textContent = "";
    }
  }
  
  private formatDuration(sec: number): string {
    const h = Math.floor(sec / 3600);
    const m = Math.floor((sec % 3600) / 60);
    const s = Math.floor(sec % 60);
    if (h > 0) return `${h}h ${m}m ${s}s`;
    if (m > 0) return `${m}m ${s}s`;
    return `${s}s`;
  }
  
  private updateUI(state: string) {
    this.stateLabel.textContent = state.toUpperCase();
    
    switch (state) {
      case "idle":
        this.stateLabel.style.backgroundColor = "#333";
        this.btnStart.disabled = false;
        this.btnPauseResume.disabled = true;
        this.btnStop.disabled = true;
        this.btnClear.disabled = true;
        this.btnPauseResume.textContent = "Pausa";
        break;
      case "preparing":
      case "running":
        this.stateLabel.style.backgroundColor = "#065f46"; // Green
        this.btnStart.disabled = true;
        this.btnPauseResume.disabled = false;
        this.btnPauseResume.textContent = "Pausa";
        this.btnStop.disabled = false;
        this.btnClear.disabled = false;
        break;
      case "paused":
        this.stateLabel.style.backgroundColor = "#9a3412"; // Orange
        this.btnStart.disabled = true;
        this.btnPauseResume.disabled = false;
        this.btnPauseResume.textContent = "Reprèn";
        this.btnStop.disabled = false;
        this.btnClear.disabled = false;
        break;
      case "stopped":
      case "completed":
        this.stateLabel.style.backgroundColor = "#1e3a8a"; // Blue
        this.btnStart.disabled = false;
        this.btnPauseResume.disabled = true;
        this.btnStop.disabled = true;
        this.btnClear.disabled = false;
        break;
      case "invalidated":
      case "error":
        this.stateLabel.style.backgroundColor = "#7f1d1d"; // Red
        this.btnStart.disabled = false;
        this.btnPauseResume.disabled = true;
        this.btnStop.disabled = true;
        this.btnClear.disabled = false;
        break;
    }
  }
}
