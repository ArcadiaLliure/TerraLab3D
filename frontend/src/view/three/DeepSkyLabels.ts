import * as THREE from "three";
import type { SkyVisibilityState } from "../../contracts/sky_environment_contracts";

const LOG_PREFIX = "MGP: [DeepSkyLabels]";

interface LabelState {
  index: number;
  label: string;
  worldPos: THREE.Vector3;
  priority: number; // based on magnitude or size
  screenX: number;
  screenY: number;
  halfWidth: number;
  halfHeight: number;
}

export class DeepSkyLabels {
  private readonly container: HTMLDivElement;
  private readonly labels: LabelState[] = [];
  private readonly _projVec = new THREE.Vector3();
  
  private isVisible = true;
  private currentVisibilityState: SkyVisibilityState | null = null;
  private maxVisibleLabels = 150; // Limit DOM elements
  private readonly domPool: HTMLDivElement[] = [];

  constructor() {
    this.container = document.createElement("div");
    this.container.className = "deepsky-labels-container";
    this.container.style.cssText =
      "position:absolute;top:0;left:0;width:100%;height:100%;pointer-events:none;overflow:hidden;z-index:4;";
      
    // Pre-create DOM pool
    for (let i = 0; i < this.maxVisibleLabels; i++) {
      const el = this.createLabelElement("");
      this.domPool.push(el);
      this.container.appendChild(el);
    }
  }

  mount(parent: HTMLElement): void {
    parent.appendChild(this.container);
  }

  updateVisibilityUniforms(state: SkyVisibilityState): void {
    this.currentVisibilityState = state;
  }

  setVisible(visible: boolean): void {
    this.isVisible = visible;
    this.container.style.display = visible ? "" : "none";
  }

  registerLabels(metadata: any, payloadBuffer: ArrayBuffer): void {
    // Clear array
    this.labels.length = 0;
    for (const el of this.domPool) {
      el.style.display = "none";
    }
    this.labels.length = 0;

    const count = metadata.renderableCount ?? metadata.recordCount;
    const objectLabels = metadata.objectLabels as string[] | undefined;
    if (!objectLabels || objectLabels.length === 0) {
      console.warn(`${LOG_PREFIX} No labels provided in metadata`);
      return;
    }

    const layout = metadata.bufferLayout;
    const eqDirs = new Float32Array(payloadBuffer, layout.equatorialDirections.offset, count * 3);
    const mags = new Float32Array(payloadBuffer, layout.magnitude.offset, count);
    const majAx = new Float32Array(payloadBuffer, layout.majorAxisArcmin.offset, count);

    const radius = 1000000;

    for (let i = 0; i < count; i++) {
      const label = objectLabels[i];
      if (!label || label === "NGC") continue;

      const mag = mags[i]! > -1 ? mags[i]! : 15.0;
      const maj = majAx[i]! > 0 ? majAx[i]! : 1.0;
      
      // Calculate a simple priority: brighter is better (lower priority value)
      // If magnitude is unknown (15), use size as tie-breaker
      const priority = mag - (maj * 0.01);

      const vx = eqDirs[i * 3]!;
      const vy = eqDirs[i * 3 + 1]!;
      const vz = eqDirs[i * 3 + 2]!;
      const worldPos = new THREE.Vector3(vx * radius, vy * radius, vz * radius);

      this.labels.push({
        index: i,
        label,
        worldPos,
        priority,
        screenX: 0,
        screenY: 0,
        halfWidth: 0,
        halfHeight: 0,
      });
    }

    // Pre-sort by priority so we only ever consider the most prominent ones
    this.labels.sort((a, b) => a.priority - b.priority);

    console.info(`${LOG_PREFIX} Loaded ${this.labels.length} labels, pooled ${this.maxVisibleLabels} DOM elements.`);
  }

  update(camera: THREE.PerspectiveCamera, equatorialToENU: THREE.Matrix3): void {
    if (!this.isVisible) return;
    
    const rect = this.container.getBoundingClientRect();
    if (rect.width === 0 || rect.height === 0) return;

    const halfW = rect.width / 2;
    const halfH = rect.height / 2;
    
    // Twilight suppression fade
    const twilightFade = this.currentVisibilityState ? (1.0 - this.currentVisibilityState.twilightSuppression) : 1.0;
    if (twilightFade <= 0.01) {
      for (const el of this.domPool) {
        el.style.display = "none";
      }
      return;
    }

    let visibleCount = 0;
    const occupied: Array<{ x: number; y: number; hw: number; hh: number }> = [];

    // Since this.labels is sorted by priority, we iterate until we fill the maxVisibleLabels
    for (let i = 0; i < this.labels.length; i++) {
      if (visibleCount >= this.maxVisibleLabels) break;
      
      const label = this.labels[i]!;
      
      // Transform world pos to ENU space using the matrix
      this._projVec.copy(label.worldPos);
      this._projVec.applyMatrix3(equatorialToENU);
      
      // Project to screen
      this._projVec.project(camera);

      // Behind camera
      if (this._projVec.z > 1) {
        continue;
      }

      const sx = this._projVec.x * halfW + halfW;
      const sy = -this._projVec.y * halfH + halfH;

      // Out of viewport margin
      const margin = 20;
      if (sx < -margin || sx > rect.width + margin || sy < -margin || sy > rect.height + margin) {
        continue;
      }

      // Estimate bounds
      const fontSize = 11;
      label.halfWidth = label.label.length * fontSize * 0.35 + 10; // offset padding
      label.halfHeight = fontSize * 0.6;
      
      // Anti-overlap
      let overlaps = false;
      for (const occ of occupied) {
        if (
          Math.abs(sx - occ.x) < (label.halfWidth + occ.hw) &&
          Math.abs(sy - occ.y) < (label.halfHeight + occ.hh)
        ) {
          overlaps = true;
          break;
        }
      }

      if (!overlaps) {
        label.screenX = sx;
        label.screenY = sy;
        occupied.push({ x: sx, y: sy, hw: label.halfWidth, hh: label.halfHeight });
        
        const el = this.domPool[visibleCount]!;
        el.textContent = label.label;
        el.style.display = "";
        el.style.transform = `translate(${sx + 15}px, ${sy - 8}px)`; // offset from center
        el.style.opacity = (twilightFade * 0.8).toFixed(2);
        visibleCount++;
      }
    }
    
    // Hide unused pool elements
    for (let i = visibleCount; i < this.maxVisibleLabels; i++) {
      this.domPool[i]!.style.display = "none";
    }
  }

  dispose(): void {
    for (const el of this.domPool) {
      el.remove();
    }
    this.labels.length = 0;
    this.container.remove();
  }

  private createLabelElement(text: string): HTMLDivElement {
    const el = document.createElement("div");
    el.textContent = text;
    el.style.cssText = `
      position: absolute;
      left: 0;
      top: 0;
      color: #9abce6;
      font-family: 'Inter', 'Roboto', sans-serif;
      font-size: 11px;
      font-weight: 500;
      text-shadow: 0 0 6px rgba(0,0,0,0.9), 0 0 2px rgba(0,0,0,0.7);
      pointer-events: none;
      user-select: none;
      white-space: nowrap;
      display: none;
      will-change: transform;
    `;
    return el;
  }
}
