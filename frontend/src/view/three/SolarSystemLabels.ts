import * as THREE from "three";

import type { SolarSystemBodyState } from "../../contracts/solar_system_contracts";
import {
  PLANET_IDS,
  PLANET_PRESENTATIONS,
  type PlanetBodyId,
  SolarSystemRenderer,
} from "./SolarSystemRenderer";

interface PlanetLabel {
  readonly element: HTMLDivElement;
  readonly text: HTMLSpanElement;
  readonly width: number;
  readonly height: number;
  visible: boolean;
  screenX: number;
  screenY: number;
}

interface ProjectedLabel {
  readonly label: PlanetLabel;
  readonly magnitude: number;
}

const LABEL_MARGIN_PX = 8;
const LABEL_HEIGHT_PX = 22;

export type LabelableBodyId = PlanetBodyId | "moon";

export function formatPlanetLabel(id: LabelableBodyId, apparentMagnitude: number): string {
  if (id === "moon") return `Moon ${apparentMagnitude.toFixed(1)}`;
  return `${PLANET_PRESENTATIONS[id].label} ${apparentMagnitude.toFixed(1)}`;
}

/**
 * Persistent DOM projection of the scientific planet states.
 *
 * Planet geometry remains the visual authority for horizon, master-toggle and
 * photometric visibility; this overlay only presents its name, colour and
 * apparent magnitude next to the projected planet position.
 */
export class SolarSystemLabels {
  private readonly container: HTMLDivElement;
  private readonly labels = new Map<LabelableBodyId, PlanetLabel>();
  private readonly projectedPosition = new THREE.Vector3();

  constructor(private readonly solarSystemRenderer: SolarSystemRenderer) {
    this.container = document.createElement("div");
    this.container.className = "solar-system-labels-container";
    this.container.style.cssText =
      "position:absolute;top:0;left:0;width:100%;height:100%;pointer-events:none;overflow:hidden;z-index:6;";

    const bodies: LabelableBodyId[] = ["moon", ...PLANET_IDS];
    for (const id of bodies) {
      const label = this.createLabel(id);
      this.container.appendChild(label.element);
      this.labels.set(id, label);
    }
  }

  mount(parent: HTMLElement): void {
    parent.appendChild(this.container);
  }

  update(camera: THREE.PerspectiveCamera): void {
    const rect = this.container.getBoundingClientRect();
    if (rect.width === 0 || rect.height === 0) return;

    const halfWidth = rect.width / 2;
    const halfHeight = rect.height / 2;
    const visible: ProjectedLabel[] = [];

    const bodies: LabelableBodyId[] = ["moon", ...PLANET_IDS];
    for (const id of bodies) {
      const label = this.labels.get(id)!;
      const object = this.solarSystemRenderer.getBodyObject(id);
      const state = object?.userData.apparentState as SolarSystemBodyState | undefined;
      const isVisible = id === "moon" 
        ? (object !== undefined && object.visible && state !== undefined)
        : this.solarSystemRenderer.isPlanetLabelVisible(id);
        
      if (!isVisible) {
        this.hide(label);
        continue;
      }

      object.getWorldPosition(this.projectedPosition).project(camera);
      if (this.projectedPosition.z < -1 || this.projectedPosition.z > 1) {
        this.hide(label);
        continue;
      }

      // Base screen coordinates (exact center of the celestial body)
      const screenX = this.projectedPosition.x * halfWidth + halfWidth;
      const screenY = -this.projectedPosition.y * halfHeight + halfHeight;

      if (
        screenX < -100
        || screenX > rect.width + 100
        || screenY < -100
        || screenY > rect.height + 100
      ) {
        this.hide(label);
        continue;
      }

      // Calculate apparent radius in pixels to keep text outside the body
      const fovRad = THREE.MathUtils.degToRad(camera.fov);
      const pixelsPerRad = rect.height / (2 * Math.tan(fovRad / 2));
      const radiusRad = THREE.MathUtils.degToRad(state.angularRadiusDeg);
      const radiusPx = radiusRad * pixelsPerRad;
      const textOffset = Math.max(LABEL_MARGIN_PX, radiusPx + 4);

      label.text.textContent = formatPlanetLabel(id, state.apparentMagnitude);
      label.text.style.left = `${textOffset}px`;
      label.screenX = screenX;
      label.screenY = screenY;
      label.visible = true;
      visible.push({ label, magnitude: state.apparentMagnitude });
    }

    // Keep the brighter tag when planets are visually close together.
    visible.sort((first, second) => first.magnitude - second.magnitude);
    const occupied: PlanetLabel[] = [];
    for (const projected of visible) {
      const label = projected.label;
      const overlaps = occupied.some((placed) => (
        Math.abs(label.screenX - placed.screenX) < 20
        && Math.abs(label.screenY - placed.screenY) < 20
      ));
      if (overlaps) this.hide(label);
      else occupied.push(label);
    }

    for (const label of this.labels.values()) {
      if (!label.visible) continue;
      label.element.style.display = "block";
      label.element.style.left = `${label.screenX}px`;
      label.element.style.top = `${label.screenY}px`;
    }
  }

  dispose(): void {
    this.labels.clear();
    this.container.remove();
  }

  private createLabel(id: LabelableBodyId): PlanetLabel {
    const cssColor = id === "moon" ? "#d8d8d2" : PLANET_PRESENTATIONS[id].cssColor;
    const element = document.createElement("div");
    element.style.cssText = "position:absolute;display:none;pointer-events:none;";
    
    if (id !== "moon") {
      const dot = document.createElement("span");
      dot.style.cssText = `position:absolute;left:0;top:0;transform:translate(-50%,-50%);width:6px;height:6px;border-radius:50%;background:${cssColor};box-shadow:0 0 6px ${cssColor};`;
      element.appendChild(dot);
    }
    
    const text = document.createElement("span");
    text.style.cssText = "position:absolute;top:0;transform:translateY(-50%);color:#f5f8ff;font-family:system-ui,-apple-system,sans-serif;font-size:12px;font-weight:600;line-height:14px;text-shadow:0 0 4px rgba(0,0,0,0.95), 0 0 8px rgba(0,0,0,0.95);white-space:nowrap;user-select:none;";
    element.appendChild(text);

    const name = id === "moon" ? "Moon" : PLANET_PRESENTATIONS[id].label;
    return {
      element,
      text,
      width: `${name} -99.9`.length * 7.2 + 22,
      height: LABEL_HEIGHT_PX,
      visible: false,
      screenX: 0,
      screenY: 0,
    };
  }

  private hide(label: PlanetLabel): void {
    label.visible = false;
    label.element.style.display = "none";
  }
}
