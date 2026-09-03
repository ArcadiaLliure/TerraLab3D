import * as THREE from "three";
import type { SkyVisibilityState } from "../../contracts/sky_environment_contracts";
import type { HorizonOcclusionState } from "./HorizonOcclusionState";
import { CELESTIAL_SCENE_RADIUS } from "./celestialScenePolicy";

const LOG_PREFIX = "MGP: [DeepSkyLabels]";

function escapeHtml(str: string): string {
  if (!str) return "";
  return String(str).replace(/[&<>'"]/g, (c) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", "'": "&#39;", '"': "&quot;",
  })[c] ?? c);
}

interface LabelState {
  index: number;
  label: string;
  familyCode: number;
  magnitude: number;
  worldPos: THREE.Vector3;
  priority: number; // based on magnitude or size
  screenX: number;
  screenY: number;
  halfWidth: number;
  halfHeight: number;
}

const FAMILY_COLORS: Record<number, string> = {
  0: "#5c9dff", // Galaxy: Light Blue
  1: "#4db6ac", // Nebula: Teal/Emerald
  2: "#ffd54f", // Open Cluster: Bright Gold
  3: "#ffb74d", // Globular Cluster: Amber/Orange
  4: "#4dd0e1", // Cluster + Nebula: Light Cyan
  5: "#a1887f", // Association: Bronze
  6: "#ce93d8", // Other: Purple
};

export class DeepSkyLabels {
  private readonly container: HTMLDivElement;
  private readonly labels: LabelState[] = [];
  private readonly _projVec = new THREE.Vector3();

  private isVisible = true;
  private currentVisibilityState: SkyVisibilityState | null = null;
  private maxVisibleLabels = 100; // Limit DOM elements for clean view
  private readonly domPool: HTMLDivElement[] = [];
  private readonly horizonUnsubscribe: (() => void) | null;
  private _revision = 0;

  constructor(private readonly horizonState: HorizonOcclusionState | null = null) {
    this.container = document.createElement("div");
    this.container.className = "deepsky-labels-container";
    this.container.style.cssText =
      "position:absolute;top:0;left:0;width:100%;height:100%;pointer-events:none;overflow:hidden;z-index:4;";
    this.horizonUnsubscribe = horizonState?.subscribe(() => { this._revision++; }) ?? null;

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
    this._revision++;
  }

  setVisible(visible: boolean): void {
    if (this.isVisible === visible) return;
    this.isVisible = visible;
    this.container.style.display = visible ? "" : "none";
    this._revision++;
  }

  registerLabels(metadata: any, payloadBuffer: ArrayBuffer): void {
    this._revision++;
    this.labels.length = 0;
    for (const el of this.domPool) {
      el.style.display = "none";
    }

    const count = metadata.renderableCount ?? metadata.recordCount;
    const objectLabels = metadata.objectLabels as string[] | undefined;
    if (!objectLabels || objectLabels.length === 0) {
      console.debug(`${LOG_PREFIX} No labels provided in metadata`);
      return;
    }

    const layout = metadata.bufferLayout;
    const eqDirs = new Float32Array(payloadBuffer, layout.equatorialDirections.offset, count * 3);
    const mags = new Float32Array(payloadBuffer, layout.magnitude.offset, count);
    const majAx = new Float32Array(payloadBuffer, layout.majorAxisArcmin.offset, count);
    const familyCodes = layout.familyCode
      ? new Uint32Array(payloadBuffer, layout.familyCode.offset, count)
      : null;

    const radius = CELESTIAL_SCENE_RADIUS.distantSky;

    for (let i = 0; i < count; i++) {
      const label = objectLabels[i];
      if (!label || label === "NGC") continue;

      const mag = mags[i]! > -1 ? mags[i]! : 15.0;
      const maj = majAx[i]! > 0 ? majAx[i]! : 1.0;
      const familyCode = familyCodes ? familyCodes[i]! : 6;

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
        familyCode,
        magnitude: mag,
        worldPos,
        priority,
        screenX: 0,
        screenY: 0,
        halfWidth: 0,
        halfHeight: 0,
      });
    }

    this.labels.sort((a, b) => a.priority - b.priority);
  }

  update(camera: THREE.PerspectiveCamera, equatorialToENU: THREE.Matrix3): void {
    if (!this.isVisible) return;

    const rect = this.container.getBoundingClientRect();
    if (rect.width === 0 || rect.height === 0) return;

    const halfW = rect.width / 2;
    const halfH = rect.height / 2;

    const twilightFade = this.currentVisibilityState ? (1.0 - this.currentVisibilityState.twilightSuppression) : 1.0;
    if (twilightFade <= 0.01) {
      for (const el of this.domPool) {
        el.style.display = "none";
      }
      return;
    }

    // Dynamic FOV-based magnitude threshold (prevents clutter when zoomed out)
    const fov = camera.fov;
    const effectiveMagLimit = Math.max(7.0, 7.0 + (90.0 - fov) * 0.1);

    let visibleCount = 0;
    const occupied: Array<{ x: number; y: number; hw: number; hh: number }> = [];

    for (let i = 0; i < this.labels.length; i++) {
      if (visibleCount >= this.maxVisibleLabels) break;

      const label = this.labels[i]!;

      // Filter out faint objects when zoomed out unless it's a Messier / major object
      const labelStr = typeof label.label === "string" ? label.label : "";
      const isMessier = labelStr.startsWith("M") && !labelStr.startsWith("NGC");
      if (label.magnitude > effectiveMagLimit && !isMessier) {
        continue;
      }

      this._projVec.copy(label.worldPos);
      this._projVec.applyMatrix3(equatorialToENU);
      if (this.horizonState?.isOccludedDirection(this._projVec)) continue;
      this._projVec.project(camera);

      if (this._projVec.z > 1) continue;

      const sx = this._projVec.x * halfW + halfW;
      const sy = -this._projVec.y * halfH + halfH;

      const margin = 20;
      if (sx < -margin || sx > rect.width + margin || sy < -margin || sy > rect.height + margin) {
        continue;
      }

      const fontSize = 11;
      label.halfWidth = label.label.length * fontSize * 0.35 + 10;
      label.halfHeight = fontSize * 0.6;

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
        const color = FAMILY_COLORS[label.familyCode] ?? "#5c9dff";
        el.innerHTML = `<span style="display:inline-block;width:6px;height:6px;border-radius:50%;background:${color};margin-right:5px;box-shadow:0 0 5px ${color};vertical-align:middle;"></span><span style="vertical-align:middle;">${escapeHtml(label.label)}</span>`;
        el.style.display = "";
        el.style.transform = `translate(${sx + 10}px, ${sy - 7}px)`;
        el.style.opacity = (twilightFade * 0.85).toFixed(2);
        visibleCount++;
      }
    }

    for (let i = visibleCount; i < this.maxVisibleLabels; i++) {
      this.domPool[i]!.style.display = "none";
    }
  }

  dispose(): void {
    this.horizonUnsubscribe?.();
    for (const el of this.domPool) {
      el.remove();
    }
    this.labels.length = 0;
    this.container.remove();
  }

  get revision(): number {
    return this._revision;
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
