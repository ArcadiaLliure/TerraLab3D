import * as THREE from "three";

import type {
  SatelliteCatalogManifest,
  SolarSystemBodyId,
  SolarSystemBodyState,
} from "../../contracts/solar_system_contracts";
import {
  PLANET_IDS,
  PLANET_PRESENTATIONS,
  type PlanetBodyId,
  SolarSystemRenderer,
} from "./SolarSystemRenderer";

interface PlanetLabel {
  readonly element: HTMLDivElement;
  readonly text: HTMLSpanElement;
  readonly dot?: HTMLSpanElement;
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

export function formatPlanetLabel(id: LabelableBodyId, apparentMagnitude: number | null): string {
  const name = id === "moon" ? "Moon" : PLANET_PRESENTATIONS[id].label;
  return apparentMagnitude === null ? name : `${name} ${apparentMagnitude.toFixed(1)}`;
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
  private readonly labels = new Map<SolarSystemBodyId, PlanetLabel>();
  private readonly satelliteNames = new Map<SolarSystemBodyId, string>();
  private readonly satelliteRadii = new Map<SolarSystemBodyId, number>();
  private readonly projectedPosition = new THREE.Vector3();
  private satelliteLabelsEnabled = true;

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

  configureSatelliteCatalog(catalog: SatelliteCatalogManifest): void {
    this.satelliteNames.clear();
    this.satelliteRadii.clear();
    for (const definition of catalog.satellites) {
      this.satelliteNames.set(definition.id, definition.displayName);
      this.satelliteRadii.set(definition.id, definition.meanRadiusKm ?? 0);
    }
  }

  setSatelliteLabelsEnabled(enabled: boolean): void {
    this.satelliteLabelsEnabled = enabled;
    if (!enabled) {
      for (const [id, label] of this.labels) {
        if (id.startsWith("naif-") || id.startsWith("provisional-")) this.hide(label);
      }
    }
  }

  update(camera: THREE.PerspectiveCamera): void {
    const rect = this.container.getBoundingClientRect();
    if (rect.width === 0 || rect.height === 0) return;

    const halfWidth = rect.width / 2;
    const halfHeight = rect.height / 2;
    const visible: ProjectedLabel[] = [];
    for (const [id, label] of this.labels) {
      if (id.startsWith("naif-") || id.startsWith("provisional-")) this.hide(label);
    }

    const satelliteIds = this.satelliteLabelsEnabled
      ? this.solarSystemRenderer.getPickableBodies()
        .filter((item) => item.id.startsWith("naif-") || item.id.startsWith("provisional-"))
        .map((item) => item.id)
      : [];
    const bodies: SolarSystemBodyId[] = ["moon", ...PLANET_IDS, ...satelliteIds];
    for (const id of bodies) {
      let label = this.labels.get(id);
      if (label === undefined) {
        label = this.createLabel(id, this.satelliteNames.get(id) ?? id);
        this.container.appendChild(label.element);
        this.labels.set(id, label);
      }
      const object = this.solarSystemRenderer.getLabelAnchor(id);
      const state = object?.userData.apparentState as SolarSystemBodyState | undefined;
      let isVisible = false;
      if (id === "moon") {
        isVisible = (object !== undefined && object.visible && state !== undefined);
      } else if (id.startsWith("naif-") || id.startsWith("provisional-")) {
        if (object?.visible === true && this.satelliteLabelsEnabled && state !== undefined) {
          const fovRad = THREE.MathUtils.degToRad(camera.fov);
          const pixelsPerRad = rect.height / (2 * Math.tan(fovRad / 2));
          const satDiameterPx = THREE.MathUtils.degToRad(state.angularDiameterDeg) * pixelsPerRad;
          const satRadius = this.satelliteRadii.get(id as SolarSystemBodyId) ?? (state.meanRadiusKm ?? 0);
          const isPrimary = satRadius > 100;

          if (isPrimary) {
            let parentDiameterPx = 0;
            const parentStringId = state.parentNaifId ? naifIdToPlanetId(state.parentNaifId) : (state.parentBodyId as SolarSystemBodyId | undefined);
            if (parentStringId) {
              const parentAnchor = this.solarSystemRenderer.getLabelAnchor(parentStringId);
              const parentState = parentAnchor?.userData.apparentState as SolarSystemBodyState | undefined;
              if (parentState) {
                parentDiameterPx = THREE.MathUtils.degToRad(parentState.angularDiameterDeg) * pixelsPerRad;
              }
            }
            isVisible = parentDiameterPx > 20 || satDiameterPx > 0.5;
          } else {
            isVisible = satDiameterPx > 0.1;
          }
        }
      } else {
        isVisible = this.solarSystemRenderer.isPlanetLabelVisible(id as PlanetBodyId, state);
      }

      if (!isVisible || object === undefined || state === undefined || !this.solarSystemRenderer.isBodyVisuallyObservable(state)) {
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

      const baseName = id.startsWith("naif-") || id.startsWith("provisional-")
        ? (state.displayName ?? this.satelliteNames.get(id) ?? id)
        : formatPlanetLabel(id as LabelableBodyId, state.apparentMagnitude);
      
      const diameterKm = state.meanRadiusKm ? state.meanRadiusKm * 2 : 0;
      if (diameterKm > 0) {
        label.text.textContent = `${baseName} (Ø ${diameterKm.toLocaleString(undefined, { maximumFractionDigits: 1 })} km)`;
      } else {
        label.text.textContent = baseName;
      }
      let isOccluded = false;
      if (id.startsWith("naif-") || id.startsWith("provisional-")) {
        const parentStringId = state.parentNaifId ? naifIdToPlanetId(state.parentNaifId) : (state.parentBodyId as SolarSystemBodyId | undefined);
        if (parentStringId) {
          const parentAnchor = this.solarSystemRenderer.getLabelAnchor(parentStringId);
          const parentState = parentAnchor?.userData.apparentState as SolarSystemBodyState | undefined;
          if (parentState) {
            const satDir = new THREE.Vector3(...state.directionENU).normalize();
            const parentDir = new THREE.Vector3(...parentState.directionENU).normalize();
            const angularSepRad = satDir.angleTo(parentDir);
            const parentRadiusRad = THREE.MathUtils.degToRad(parentState.angularRadiusDeg);
            
            if (angularSepRad < parentRadiusRad && state.distanceKm > parentState.distanceKm) {
              isOccluded = true;
            }
          }
        }
      }

      if (isOccluded) {
        label.text.style.opacity = "0.4";
        if (label.dot) label.dot.style.display = "none";
      } else {
        label.text.style.opacity = "1";
        if (label.dot) label.dot.style.display = "block";
      }

      label.text.style.left = `${textOffset}px`;
      label.screenX = screenX;
      label.screenY = screenY;
      label.visible = true;
      visible.push({ label, magnitude: state.apparentMagnitude ?? Number.POSITIVE_INFINITY });
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

  private createLabel(id: SolarSystemBodyId, explicitName?: string): PlanetLabel {
    const knownPlanet = id !== "moon" && id in PLANET_PRESENTATIONS;
    const cssColor = id === "moon" ? "#d8d8d2" : knownPlanet
      ? PLANET_PRESENTATIONS[id as PlanetBodyId].cssColor
      : "#b9cae8";
    const element = document.createElement("div");
    element.style.cssText = "position:absolute;display:none;pointer-events:none;";

    let dot: HTMLSpanElement | undefined;
    if (id !== "moon") {
      dot = document.createElement("span");
      dot.style.cssText = `position:absolute;left:0;top:0;transform:translate(-50%,-50%);width:6px;height:6px;border-radius:50%;background:${cssColor};box-shadow:0 0 6px ${cssColor};`;
      element.appendChild(dot);
    }

    const text = document.createElement("span");
    text.style.cssText = "position:absolute;top:0;transform:translateY(-50%);color:#f5f8ff;font-family:system-ui,-apple-system,sans-serif;font-size:12px;font-weight:600;line-height:14px;text-shadow:0 0 4px rgba(0,0,0,0.95), 0 0 8px rgba(0,0,0,0.95);white-space:nowrap;user-select:none;";
    element.appendChild(text);

    const name = explicitName ?? (id === "moon" ? "Moon" : PLANET_PRESENTATIONS[id as PlanetBodyId].label);
    return {
      element,
      text,
      dot,
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

function naifIdToPlanetId(naifId: number): PlanetBodyId | "sun" | "moon" | undefined {
  switch (naifId) {
    case 10: return "sun";
    case 199: return "mercury";
    case 299: return "venus";
    // Earth is the observer/world root, not a rendered celestial label anchor.
    case 399: return undefined;
    case 301: return "moon";
    case 499: return "mars";
    case 599: return "jupiter";
    case 699: return "saturn";
    case 799: return "uranus";
    case 899: return "neptune";
    case 999: return "pluto";
    default: return undefined;
  }
}
