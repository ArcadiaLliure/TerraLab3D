import { WebSocketBridge } from "../../../bridge/WebSocketBridge";
import { formatLocalAndUtcTime } from "../timeFormatting";

export class TimeBar {
  private container: HTMLDivElement;
  private playPauseBtn: HTMLButtonElement;
  private element: HTMLDivElement;
  private canvas: HTMLCanvasElement;
  private ctx: CanvasRenderingContext2D;
  private timeLabel: HTMLDivElement;
  
  private currentTime = new Date();
  private sunAltitudes: number[] = [];
  private isRealtime = true;
  private isTimePlaying = true;
  
  private isDragging = false;
  private bridge: WebSocketBridge;
  
  constructor(bridge: WebSocketBridge) {
    this.bridge = bridge;
    
    this.container = document.createElement("div");
    this.container.style.cssText = `
      width: 100%;
      height: 100%;
      display: flex;
      flex-direction: row;
      align-items: stretch;
    `;
    
    this.playPauseBtn = document.createElement("button");
    this.playPauseBtn.style.cssText = `
      flex: 0 0 40px;
      background: var(--color-surface);
      border: none;
      border-right: 1px solid var(--color-border);
      color: var(--color-text);
      cursor: pointer;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 16px;
    `;
    this.playPauseBtn.innerHTML = "⏸";
    this.playPauseBtn.addEventListener("click", () => {
      this.isTimePlaying = !this.isTimePlaying;
      this.bridge.sendSetTimePlaying(this.isTimePlaying);
      this.updatePlayPauseIcon();
    });
    
    this.element = document.createElement("div");
    this.element.style.cssText = `
      flex: 1 1 auto;
      position: relative;
      height: 100%;
      background: var(--color-chrome);
      user-select: none;
      cursor: ew-resize;
    `;
    
    this.canvas = document.createElement("canvas");
    this.canvas.style.cssText = `
      position: absolute;
      top: 0; left: 0;
      width: 100%; height: 100%;
    `;
    
    this.ctx = this.canvas.getContext("2d")!;
    
    this.timeLabel = document.createElement("div");
    this.timeLabel.style.cssText = `
      position: absolute;
      top: 50%;
      left: 50%;
      transform: translate(-50%, -50%);
      color: var(--color-text);
      font-weight: 600;
      font-size: 14px;
      pointer-events: none;
      text-shadow: 0 1px 3px rgba(0,0,0,0.8);
    `;
    
    this.element.appendChild(this.canvas);
    this.element.appendChild(this.timeLabel);
    
    this.container.appendChild(this.playPauseBtn);
    this.container.appendChild(this.element);
    
    // Bind events
    this.element.addEventListener("mousedown", this.onMouseDown.bind(this));
    window.addEventListener("mousemove", this.onMouseMove.bind(this));
    window.addEventListener("mouseup", this.onMouseUp.bind(this));
    
    // Resize observer
    const ro = new ResizeObserver(() => this.draw());
    ro.observe(this.element);
  }
  
  private updatePlayPauseIcon() {
    this.playPauseBtn.innerHTML = this.isTimePlaying ? "⏸" : "▶";
    this.playPauseBtn.title = this.isTimePlaying ? "Pausar temps (quan simulat)" : "Avançar temps (quan simulat)";
  }
  
  public updateState(isoStr: string, sunAltitudes: number[], isRealtime: boolean) {
    if (this.isDragging) return; // Prevent jitter from backend updates while dragging
    this.currentTime = new Date(isoStr);
    this.sunAltitudes = sunAltitudes;
    if (this.isRealtime !== isRealtime) {
      this.isRealtime = isRealtime;
      if (isRealtime) {
         this.isTimePlaying = true;
         this.updatePlayPauseIcon();
      }
    }
    this.draw();
  }
  
  private onMouseDown(e: MouseEvent) {
    this.isDragging = true;
    this.bridge.sendTimelineDragStarted();
    this.updateTimeFromMouse(e);
  }
  
  private onMouseMove(e: MouseEvent) {
    if (!this.isDragging) return;
    this.updateTimeFromMouse(e);
  }
  
  private onMouseUp(e: MouseEvent) {
    if (!this.isDragging) return;
    this.isDragging = false;
    this.updateTimeFromMouse(e);
    this.bridge.sendTimelineDragFinished(this.currentTime.toISOString());
  }
  
  private lastSentTimeMs = 0;

  private updateTimeFromMouse(e: MouseEvent) {
    const rect = this.canvas.getBoundingClientRect();
    const x = Math.max(0, Math.min(e.clientX - rect.left, rect.width));
    const fraction = x / rect.width;
    
    // Fraction represents hour of day 0..24
    const totalMs = fraction * 24 * 3600 * 1000;
    
    // Set current time (UTC) for this fraction
    const d = new Date(this.currentTime);
    d.setUTCHours(0, 0, 0, 0);
    this.currentTime = new Date(d.getTime() + totalMs);
    this.isRealtime = false;
    
    this.draw();
    
    // Throttle WebSocket updates during drag to max 20Hz (50ms)
    const nowMs = performance.now();
    if (!this.isDragging || nowMs - this.lastSentTimeMs > 50) {
      this.lastSentTimeMs = nowMs;
      this.bridge.sendSetSimulationTime(this.currentTime.toISOString());
    }
  }
  
  private draw() {
    const w = this.element.clientWidth;
    const h = this.element.clientHeight;
    if (w === 0 || h === 0) return;
    
    this.canvas.width = w;
    this.canvas.height = h;
    
    this.ctx.clearRect(0, 0, w, h);
    
    // Draw background gradient based on sunAltitudes
    if (this.sunAltitudes.length > 0) {
      const stepWidth = w / (this.sunAltitudes.length - 1);
      
      for (let i = 0; i < this.sunAltitudes.length - 1; i++) {
        const alt1 = this.sunAltitudes[i] ?? 0;
        const alt2 = this.sunAltitudes[i + 1] ?? 0;
        
        // Simple lerp: -18 to +18 mapped to 0..1 for color
        const mapAlt = (alt: number) => {
            const clamp = Math.max(-18, Math.min(18, alt));
            return (clamp + 18) / 36; 
        };
        
        const c1 = mapAlt(alt1);
        const c2 = mapAlt(alt2);
        
        const grad = this.ctx.createLinearGradient(i * stepWidth, 0, (i + 1) * stepWidth, 0);
        grad.addColorStop(0, this.getColor(c1));
        grad.addColorStop(1, this.getColor(c2));
        
        this.ctx.fillStyle = grad;
        this.ctx.fillRect(i * stepWidth, 0, Math.ceil(stepWidth), h);
      }
    }
    
    // Draw hours marks
    this.ctx.fillStyle = "rgba(255, 255, 255, 0.2)";
    for (let h_mark = 0; h_mark <= 24; h_mark++) {
      const x = (h_mark / 24) * w;
      if (h_mark % 6 === 0) {
        this.ctx.fillRect(x, 0, 1, h); // Major tick
      } else {
        this.ctx.fillRect(x, h - 8, 1, 8); // Minor tick
      }
    }
    
    // Draw golden marker
    const msSinceMidnight = this.currentTime.getTime() - new Date(this.currentTime).setUTCHours(0, 0, 0, 0);
    const fraction = msSinceMidnight / (24 * 3600 * 1000);
    const markerX = fraction * w;
    
    this.ctx.fillStyle = "#d8b26a"; // --color-gold
    this.ctx.fillRect(markerX - 1, 0, 3, h);
    
    this.timeLabel.textContent = `${formatLocalAndUtcTime(this.currentTime)} ${this.isRealtime ? '(Real)' : '(Simulat)'}`;
  }
  
  private getColor(val: number): string {
    // val 0 = deep night, 1 = day
    // Night: #050811, Twilight: #252c3b, Day: #4fd8c4 (or a sky blue)
    if (val < 0.2) return "#050811";
    if (val < 0.5) return "#252c3b";
    return "#3b5569";
  }
  
  public mount(container: HTMLElement) {
    container.appendChild(this.container);
    this.draw();
  }
}
