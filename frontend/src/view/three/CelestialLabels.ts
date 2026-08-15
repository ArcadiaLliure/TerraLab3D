/**
 * CelestialLabels — Sistema d'etiquetes projectades per al grid astronòmic.
 *
 * Gestiona totes les etiquetes de text projectades des de coordenades angulars
 * (azimut, altitud) a l'espai de pantalla. Inclou punts cardinals, ticks
 * angulars i el zenit.
 *
 * Característiques:
 *   - Text sempre upright (no hereta roll de la càmera)
 *   - Culling fora del viewport
 *   - Anti-solapament basat en prioritats
 *   - DPR-aware
 *   - Pool HTML persistent (no crea/destrueix per frame)
 *   - Actualització a ~4 Hz, no cada frame
 */

import * as THREE from "three";
import { CELESTIAL_SCENE_RADIUS } from "./celestialScenePolicy";

const LOG_PREFIX = "MGP: [CelestialLabels]";

// ─── Types ───────────────────────────────────────────────────────────

type SemanticKind =
  | "cardinal"
  | "intercardinal"
  | "azimuth_tick"
  | "altitude_tick"
  | "zenith"
  | "diagnostic";

interface LabelDefinition {
  id: string;
  text: string;
  azDeg: number;
  altDeg: number;
  priority: number;
  kind: SemanticKind;
  color: string;
  fontSize: number;
  bold: boolean;
}

interface LabelState {
  def: LabelDefinition;
  element: HTMLDivElement;
  screenX: number;
  screenY: number;
  visible: boolean;
  halfWidth: number;
  halfHeight: number;
}

// Priority values (lower number = higher priority)
const PRIORITY_CARDINAL = 0;
const PRIORITY_ZENITH = 1;
const PRIORITY_INTERCARDINAL = 2;
const PRIORITY_AZ_TICK_30 = 3;
const PRIORITY_ALT_TICK_30 = 4;
const PRIORITY_AZ_TICK_15 = 5;
const PRIORITY_ALT_TICK_15 = 6;
const PRIORITY_AZ_TICK_5 = 7;
const PRIORITY_ALT_TICK_5 = 8;

// Colors
const COLOR_CARDINAL = "#f1cd88";
const COLOR_INTERCARDINAL = "#aabbcc";
const COLOR_TICK = "#778899";
const COLOR_ZENITH = "#f1cd88";

// Sphere radius must match HorizontalGrid
const LABEL_SPHERE_RADIUS = CELESTIAL_SCENE_RADIUS.distantSky;
const DEG = Math.PI / 180;

// ─── Label Definitions ───────────────────────────────────────────────

function buildLabelDefinitions(): LabelDefinition[] {
  const labels: LabelDefinition[] = [];

  // Cardinals
  const cardinals: [number, string][] = [
    [0, "N"], [90, "E"], [180, "S"], [270, "O"],
  ];
  for (const [az, text] of cardinals) {
    labels.push({
      id: `cardinal_${text}`,
      text,
      azDeg: az,
      altDeg: 0,
      priority: PRIORITY_CARDINAL,
      kind: "cardinal",
      color: COLOR_CARDINAL,
      fontSize: 16,
      bold: true,
    });
  }

  // Intercardinals
  const intercardinals: [number, string][] = [
    [45, "NE"], [135, "SE"], [225, "SO"], [315, "NO"],
  ];
  for (const [az, text] of intercardinals) {
    labels.push({
      id: `intercardinal_${text}`,
      text,
      azDeg: az,
      altDeg: 0,
      priority: PRIORITY_INTERCARDINAL,
      kind: "intercardinal",
      color: COLOR_INTERCARDINAL,
      fontSize: 13,
      bold: true,
    });
  }

  // Zenith
  labels.push({
    id: "zenith",
    text: "Z",
    azDeg: 0,
    altDeg: 90,
    priority: PRIORITY_ZENITH,
    kind: "zenith",
    color: COLOR_ZENITH,
    fontSize: 14,
    bold: true,
  });

  // Azimuth ticks every 15° (skip 0, 45, 90, 135, 180, 225, 270, 315)
  for (let az = 0; az < 360; az += 15) {
    if (az % 45 === 0) continue; // Already have cardinal/intercardinal
    const isPrimary = az % 30 === 0;
    labels.push({
      id: `az_tick_${az}`,
      text: `${az}°`,
      azDeg: az,
      altDeg: 0,
      priority: isPrimary ? PRIORITY_AZ_TICK_30 : PRIORITY_AZ_TICK_15,
      kind: "azimuth_tick",
      color: COLOR_TICK,
      fontSize: 10,
      bold: false,
    });
  }

  // Altitude ticks every 15° (skip 0° — it's the horizon)
  for (let alt = 15; alt <= 75; alt += 15) {
    const isPrimary = alt % 30 === 0;
    // Place altitude labels at azimuth 0° (North) for reference
    labels.push({
      id: `alt_tick_${alt}`,
      text: `${alt}°`,
      azDeg: 0,
      altDeg: alt,
      priority: isPrimary ? PRIORITY_ALT_TICK_30 : PRIORITY_ALT_TICK_15,
      kind: "altitude_tick",
      color: COLOR_TICK,
      fontSize: 10,
      bold: false,
    });
  }

  return labels;
}

// ─── Main Class ──────────────────────────────────────────────────────

export class CelestialLabels {
  private readonly container: HTMLDivElement;
  private readonly labels: LabelState[] = [];
  private readonly _projVec = new THREE.Vector3();

  // Visibility toggles
  private showCardinals = true;
  private showTicks = true;

  constructor() {
    this.container = document.createElement("div");
    this.container.className = "celestial-labels-container";
    this.container.style.cssText =
      "position:absolute;top:0;left:0;width:100%;height:100%;pointer-events:none;overflow:hidden;z-index:5;";

    const defs = buildLabelDefinitions();
    for (const def of defs) {
      const el = this.createLabelElement(def);
      this.container.appendChild(el);
      this.labels.push({
        def,
        element: el,
        screenX: 0,
        screenY: 0,
        visible: false,
        halfWidth: 0,
        halfHeight: 0,
      });
    }

    console.info(
      `${LOG_PREFIX} [constructor] [${this.labels.length} etiquetes creades]`,
    );
  }

  // ─── Public API ──────────────────────────────────────────────

  mount(parent: HTMLElement): void {
    parent.appendChild(this.container);
  }

  /**
   * Update all label positions and visibility.
   * Call this at ~4 Hz from the render loop, not every frame.
   */
  update(camera: THREE.PerspectiveCamera, cameraPositionWorld: THREE.Vector3): void {
    const rect = this.container.getBoundingClientRect();
    if (rect.width === 0 || rect.height === 0) return;

    const halfW = rect.width / 2;
    const halfH = rect.height / 2;

    // Step 1: Project all labels to screen space
    for (const label of this.labels) {
      // Check toggle visibility
      const isCardinalLike = label.def.kind === "cardinal" || label.def.kind === "intercardinal";
      const isTick = label.def.kind === "azimuth_tick" || label.def.kind === "altitude_tick";
      if (isCardinalLike && !this.showCardinals) {
        label.visible = false;
        label.element.style.display = "none";
        continue;
      }
      if (isTick && !this.showTicks) {
        label.visible = false;
        label.element.style.display = "none";
        continue;
      }

      // Convert (az, alt) to world position on sphere centred at camera
      const azRad = label.def.azDeg * DEG;
      const altRad = label.def.altDeg * DEG;
      const cosAlt = Math.cos(altRad);
      // Calcular l'enfonsament de l'horitzó per esfèricitat
      const R_E = 6371000.0;
      const cameraH = Math.max(0.0, cameraPositionWorld.y);
      const dipAngleRad = Math.acos(R_E / (R_E + cameraH));
      
      const currentRadius = LABEL_SPHERE_RADIUS;
      const yOffset = -currentRadius * Math.tan(dipAngleRad);

      // World pos = camera position (X, Z) + offset Y + direction * radius
      const worldX = cameraPositionWorld.x + Math.sin(azRad) * cosAlt * currentRadius;
      const worldY = cameraPositionWorld.y + yOffset + Math.sin(altRad) * currentRadius;
      const worldZ = cameraPositionWorld.z + (-Math.cos(azRad) * cosAlt * currentRadius);

      this._projVec.set(worldX, worldY, worldZ);
      this._projVec.project(camera);

      // Behind camera check
      if (this._projVec.z > 1) {
        label.visible = false;
        label.element.style.display = "none";
        continue;
      }

      const sx = this._projVec.x * halfW + halfW;
      const sy = -this._projVec.y * halfH + halfH;

      // Out of viewport (generous margin)
      const margin = 50;
      if (sx < -margin || sx > rect.width + margin || sy < -margin || sy > rect.height + margin) {
        label.visible = false;
        label.element.style.display = "none";
        continue;
      }

      label.screenX = sx;
      label.screenY = sy;
      label.visible = true;

      // Estimate bounds
      const fontSize = label.def.fontSize;
      label.halfWidth = label.def.text.length * fontSize * 0.35;
      label.halfHeight = fontSize * 0.6;
    }

    // Step 2: Anti-overlap with priority-based culling
    // Sort by priority (lower = higher priority)
    const visibleLabels = this.labels.filter((l) => l.visible);
    visibleLabels.sort((a, b) => a.def.priority - b.def.priority);

    const occupied: Array<{ x: number; y: number; hw: number; hh: number }> = [];

    for (const label of visibleLabels) {
      // Check overlap with already placed labels
      let overlaps = false;
      for (const rect of occupied) {
        if (
          Math.abs(label.screenX - rect.x) < (label.halfWidth + rect.hw) &&
          Math.abs(label.screenY - rect.y) < (label.halfHeight + rect.hh)
        ) {
          overlaps = true;
          break;
        }
      }

      if (overlaps) {
        label.visible = false;
        label.element.style.display = "none";
      } else {
        occupied.push({
          x: label.screenX,
          y: label.screenY,
          hw: label.halfWidth,
          hh: label.halfHeight,
        });
      }
    }

    // Step 3: Apply positions to visible labels
    for (const label of this.labels) {
      if (label.visible) {
        label.element.style.display = "";
        label.element.style.left = `${label.screenX}px`;
        label.element.style.top = `${label.screenY}px`;
      }
    }
  }

  setCardinalVisible(visible: boolean): void {
    this.showCardinals = visible;
  }

  setTicksVisible(visible: boolean): void {
    this.showTicks = visible;
  }

  setVisible(visible: boolean): void {
    this.container.style.display = visible ? "" : "none";
  }

  getCounts(): { total: number; visible: number; culled: number } {
    let visible = 0;
    let culled = 0;
    for (const l of this.labels) {
      if (l.visible) visible++;
      else culled++;
    }
    return { total: this.labels.length, visible, culled };
  }

  dispose(): void {
    for (const l of this.labels) {
      l.element.remove();
    }
    this.labels.length = 0;
    this.container.remove();
    console.info(`${LOG_PREFIX} [dispose] [Etiquetes eliminades]`);
  }

  // ─── Private ──────────────────────────────────────────────────

  private createLabelElement(def: LabelDefinition): HTMLDivElement {
    const el = document.createElement("div");
    el.id = `celestial-label-${def.id}`;
    el.textContent = def.text;
    el.style.cssText = `
      position: absolute;
      color: ${def.color};
      font-family: 'Inter', 'Roboto', sans-serif;
      font-size: ${def.fontSize}px;
      font-weight: ${def.bold ? 700 : 400};
      text-shadow: 0 0 6px rgba(0,0,0,0.9), 0 0 2px rgba(0,0,0,0.7);
      pointer-events: none;
      user-select: none;
      transform: translate(-50%, -50%);
      white-space: nowrap;
      display: none;
    `;
    return el;
  }
}
