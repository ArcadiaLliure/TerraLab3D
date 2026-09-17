import * as THREE from "three";
import { Line2 } from "three/addons/lines/Line2.js";
import { LineGeometry } from "three/addons/lines/LineGeometry.js";
import { LineSegments2 } from "three/addons/lines/LineSegments2.js";
import { LineSegmentsGeometry } from "three/addons/lines/LineSegmentsGeometry.js";

import type {
  ApparentTrajectoryEvent,
  ApparentTrajectoryMetadata,
  TrajectoryVisibilityState,
} from "../../contracts/astronomical_event_contracts";
import { CELESTIAL_SCENE_RADIUS } from "./celestialScenePolicy";
import { threeFromEnu } from "./celestialCoordinates";
import {
  createOverlayLineMaterials,
  disposeOverlayLineMaterials,
  OVERLAY_LINE_PROFILES,
  setOverlayResolution,
  withOverlayColor,
  type OverlayLineMaterials,
} from "./materials/OverlayLineStyle";

const TRAJECTORY_RADIUS = CELESTIAL_SCENE_RADIUS.solarSystem * 0.97;
const MARKER_RADIUS = TRAJECTORY_RADIUS + 1_000;
const STATE_ORDER: readonly TrajectoryVisibilityState[] = [
  "visible",
  "terrain_occluded",
  "below_astronomical_horizon",
  "insufficient_data",
];

interface SegmentLine {
  readonly root: THREE.Group;
  readonly geometry: LineSegmentsGeometry;
  readonly materials: OverlayLineMaterials;
}

export type TrajectoryCoverage = "empty" | "covered" | "outside_interval";

export interface ApparentTrajectoryMetrics {
  readonly geometryBuildCount: number;
  readonly materialBuildCount: number;
  readonly resourceApplyCount: number;
  readonly staleResourceCount: number;
  readonly bridgeBytes: number;
  readonly activeGeometryCount: number;
  readonly activeOverlayMaterialCount: number;
  readonly activeMarkerUpdateCount: number;
}

/** Persistent renderer for one selected observer-sky path with retroilluminated styling. */
export class ApparentTrajectoryRenderer {
  readonly root = new THREE.Group();
  private readonly legacyGeometry = new LineGeometry();
  private readonly legacyMaterials = createOverlayLineMaterials(OVERLAY_LINE_PROFILES.trajectoryPrimary);
  private readonly legacyRoot = new THREE.Group();
  private readonly legacyHalo = new Line2(this.legacyGeometry, this.legacyMaterials.halo);
  private readonly legacyLine = new Line2(this.legacyGeometry, this.legacyMaterials.core);
  private readonly segmentLines = new Map<TrajectoryVisibilityState, SegmentLine>();
  private readonly eventRoot = new THREE.Group();
  private readonly labelRoot = new THREE.Group();
  private readonly activeMarkerGeometry = new THREE.BufferGeometry();
  private readonly activeMarkerMaterial = new THREE.PointsMaterial({
    color: 0xf3f5fa,
    size: 9,
    sizeAttenuation: false,
    depthTest: false,
    depthWrite: false,
  });
  private readonly activeMarker = new THREE.Points(
    this.activeMarkerGeometry,
    this.activeMarkerMaterial,
  );
  private metadata: ApparentTrajectoryMetadata | null = null;
  private directions = new Float32Array();
  private offsets = new Float32Array();
  private validity = new Uint8Array();
  private expectedRequestId: string | null = null;
  private expectedObjectId: string | null = null;
  private enabled = true;
  private showTerrainOccluded = true;
  private showBelowHorizon = true;
  private currentFovDeg = 60;
  private currentHeightPx = 800;
  private disposed = false;
  // Pas-9 metrics count the persistent trajectory line; the active marker is
  // a Pas-22 auxiliary that never rebuilds and stays outside that regression.
  private _geometryBuildCount = 1;
  private _materialBuildCount = 2;
  private _resourceApplyCount = 0;
  private _staleResourceCount = 0;
  private _bridgeBytes = 0;
  private _activeMarkerUpdateCount = 0;

  constructor(parent: THREE.Object3D) {
    this.root.name = "apparentTrajectories";
    this.legacyGeometry.setPositions(new Float32Array([0, 0, 0, 0, 0, 0]));
    this.legacyGeometry.instanceCount = 0;
    this.legacyRoot.name = "apparentTrajectory:legacy-or-visible";
    this.legacyHalo.name = "apparentTrajectory:legacy-or-visible:halo";
    this.legacyHalo.frustumCulled = false;
    this.legacyHalo.renderOrder = 89;
    this.legacyLine.name = "apparentTrajectory:legacy-or-visible:core";
    this.legacyLine.frustumCulled = false;
    this.legacyLine.renderOrder = 90;
    this.legacyRoot.add(this.legacyHalo, this.legacyLine);
    this.activeMarker.name = "apparentTrajectory:active-time";
    this.activeMarker.visible = false;
    this.activeMarker.renderOrder = 106;
    this.eventRoot.name = "apparentTrajectory:events";
    this.labelRoot.name = "apparentTrajectory:event-labels";
    this.root.add(this.legacyRoot, this.eventRoot, this.labelRoot, this.activeMarker);
    parent.add(this.root);
  }

  /** Immediately invalidates the previous identity while latest-wins work runs. */
  beginRequest(requestId: string, objectId: string): void {
    const objectChanged = this.expectedObjectId !== objectId;
    this.expectedRequestId = requestId;
    this.expectedObjectId = objectId;
    if (objectChanged) {
      this.clearVisualData();
    }
    this.root.userData.trajectoryStatus = "calculating";
  }

  registerBinaryResource(metadata: ApparentTrajectoryMetadata, payload: ArrayBuffer): boolean {
    if (this.disposed || metadata.role !== "apparent_trajectory") return false;
    if (
      this.expectedRequestId !== null
      && (metadata.requestId !== this.expectedRequestId || metadata.objectId !== this.expectedObjectId)
    ) {
      this._staleResourceCount++;
      return false;
    }
    const previous = this.metadata;
    if (previous !== null && (
      metadata.observerGeneration < previous.observerGeneration
      || (
        metadata.observerGeneration === previous.observerGeneration
        && (
          metadata.generation < previous.generation
          || metadata.version === previous.version
        )
      )
    )) {
      this._staleResourceCount++;
      return false;
    }
    const requiredBytes = this.requiredBytes(metadata);
    if (payload.byteLength < requiredBytes) return false;

    this.directions = new Float32Array(new Float32Array(
      payload,
      metadata.directionByteOffset,
      metadata.sampleCount * 3,
    ));
    this.offsets = new Float32Array(new Float32Array(
      payload,
      metadata.timeOffsetByteOffset,
      metadata.sampleCount,
    ));
    this.validity = new Uint8Array(new Uint8Array(
      payload,
      metadata.validityByteOffset,
      metadata.sampleCount,
    ));
    this.metadata = metadata;

    if (metadata.contractVersion === 2 && metadata.visibilityByteOffset !== undefined) {
      const visibility = new Uint8Array(payload, metadata.visibilityByteOffset, metadata.sampleCount);
      this.applySegmentedTrajectory(metadata, visibility);
      this.applyEvents(metadata.events ?? []);
    } else {
      this.applyLegacyTrajectory();
      this.clearEvents();
    }
    this.root.visible = this.enabled;
    this.root.userData.trajectoryMetadata = metadata;
    this.root.userData.trajectoryStatus = "ready";
    this._resourceApplyCount++;
    this._bridgeBytes = payload.byteLength;
    return true;
  }

  updateSimulationTime(instantUtc: string): TrajectoryCoverage {
    const metadata = this.metadata;
    const timeMs = Date.parse(instantUtc);
    if (metadata === null || this.offsets.length === 0 || !Number.isFinite(timeMs)) {
      this.activeMarker.visible = false;
      return "empty";
    }
    const startMs = Date.parse(metadata.startUtc);
    const offsetSeconds = (timeMs - startMs) / 1_000;
    const lastOffset = this.offsets[this.offsets.length - 1] ?? 0;
    if (offsetSeconds < 0 || offsetSeconds > lastOffset) {
      this.activeMarker.visible = false;
      this.root.userData.trajectoryCoverage = "outside_interval";
      return "outside_interval";
    }
    let right = 1;
    while (right < this.offsets.length && this.offsets[right]! < offsetSeconds) right++;
    const left = Math.max(0, right - 1);
    right = Math.min(this.offsets.length - 1, right);
    if (this.validity[left] === 0 || this.validity[right] === 0) {
      this.activeMarker.visible = false;
      return "empty";
    }
    const leftOffset = this.offsets[left] ?? 0;
    const rightOffset = this.offsets[right] ?? leftOffset;
    const fraction = rightOffset <= leftOffset
      ? 0
      : THREE.MathUtils.clamp((offsetSeconds - leftOffset) / (rightOffset - leftOffset), 0, 1);
    const direction = this.directionAt(left).lerp(this.directionAt(right), fraction).normalize();
    const position = direction.multiplyScalar(MARKER_RADIUS);
    const attribute = this.activeMarkerGeometry.getAttribute("position") as THREE.BufferAttribute | undefined;
    if (attribute === undefined) {
      this.activeMarkerGeometry.setAttribute(
        "position",
        new THREE.BufferAttribute(new Float32Array([position.x, position.y, position.z]), 3),
      );
    } else {
      attribute.setXYZ(0, position.x, position.y, position.z);
      attribute.needsUpdate = true;
    }
    this.activeMarker.visible = this.enabled;
    this.root.userData.trajectoryCoverage = "covered";
    this._activeMarkerUpdateCount++;
    return "covered";
  }

  updateCamera(fovDeg: number, heightPx: number): void {
    this.currentFovDeg = fovDeg;
    this.currentHeightPx = heightPx;
    const widthPx = heightPx * (typeof window !== "undefined" && window.innerHeight > 0
      ? window.innerWidth / window.innerHeight
      : 16 / 9);
    setOverlayResolution(this.legacyMaterials, widthPx, heightPx);
    for (const line of this.segmentLines.values()) {
      setOverlayResolution(line.materials, widthPx, heightPx);
    }
    this.updateLabelScales();
  }

  setEnabled(enabled: boolean): void {
    this.enabled = enabled;
    this.root.visible = enabled;
  }

  setHiddenSegmentsVisible(visible: boolean): void {
    this.showTerrainOccluded = visible;
    this.updateLayerVisibility();
  }

  setBelowHorizonVisible(visible: boolean): void {
    this.showBelowHorizon = visible;
    this.updateLayerVisibility();
  }

  clear(): void {
    // Keep a rejection sentinel so a response already in flight cannot
    // repopulate a trajectory after the user has disabled the capability.
    this.expectedRequestId = "__trajectory-disabled__";
    this.expectedObjectId = "";
    this.metadata = null;
    this.clearVisualData();
    this.root.userData.trajectoryStatus = "empty";
  }

  metrics(): ApparentTrajectoryMetrics {
    return {
      geometryBuildCount: this._geometryBuildCount,
      materialBuildCount: this._materialBuildCount,
      resourceApplyCount: this._resourceApplyCount,
      staleResourceCount: this._staleResourceCount,
      bridgeBytes: this._bridgeBytes,
      activeGeometryCount: this.disposed
        ? 0
        : 2 + this.segmentLines.size + this.eventRoot.children.length,
      activeOverlayMaterialCount: this.disposed ? 0 : 2 + this.segmentLines.size * 2,
      activeMarkerUpdateCount: this._activeMarkerUpdateCount,
    };
  }

  dispose(): void {
    if (this.disposed) return;
    this.disposed = true;
    this.root.removeFromParent();
    this.legacyGeometry.dispose();
    disposeOverlayLineMaterials(this.legacyMaterials);
    this.activeMarkerGeometry.dispose();
    this.activeMarkerMaterial.dispose();
    for (const line of this.segmentLines.values()) {
      line.geometry.dispose();
      disposeOverlayLineMaterials(line.materials);
    }
    this.clearEvents();
    this.segmentLines.clear();
  }

  private requiredBytes(metadata: ApparentTrajectoryMetadata): number {
    if (metadata.horizonProvenanceByteOffset !== undefined) {
      return metadata.horizonProvenanceByteOffset + metadata.sampleCount;
    }
    if (metadata.visibilityByteOffset !== undefined) {
      return metadata.visibilityByteOffset + metadata.sampleCount;
    }
    return metadata.validityByteOffset + metadata.sampleCount;
  }

  private applyLegacyTrajectory(): void {
    for (const line of this.segmentLines.values()) line.root.visible = false;
    const positions = new Float32Array(this.metadata!.sampleCount * 3);
    for (let index = 0; index < this.metadata!.sampleCount; index++) {
      const target = index * 3;
      if (this.validity[index] === 0) {
        positions.fill(Number.NaN, target, target + 3);
      } else {
        this.directionAt(index).normalize().multiplyScalar(TRAJECTORY_RADIUS).toArray(positions, target);
      }
    }
    this.legacyGeometry.setPositions(positions);
    this.legacyGeometry.computeBoundingSphere();
    this.legacyRoot.visible = this.enabled;
  }

  private applySegmentedTrajectory(
    metadata: ApparentTrajectoryMetadata,
    visibility: Uint8Array,
  ): void {
    const positionsByState = new Map<TrajectoryVisibilityState, number[]>();
    for (const state of STATE_ORDER) {
      positionsByState.set(state, []);
    }
    const sampleCount = metadata.sampleCount;
    const segments = metadata.segments ?? this.deriveSegments(visibility);

    for (const segment of segments) {
      const positions = positionsByState.get(segment.visibility)!;
      for (let index = segment.startIndex; index < segment.endIndex; index++) {
        if (this.validity[index] === 0 || this.validity[index + 1] === 0) continue;
        const left = this.directionAt(index).normalize().multiplyScalar(TRAJECTORY_RADIUS);
        const right = this.directionAt(index + 1).normalize().multiplyScalar(TRAJECTORY_RADIUS);

        positions.push(left.x, left.y, left.z, right.x, right.y, right.z);
      }
    }

    // Tancament de bucle 360° (Loop closure): connectar l'última mostra amb la primera si ambdues són vàlides
    if (sampleCount >= 2 && this.validity[sampleCount - 1] !== 0 && this.validity[0] !== 0) {
      const lastState = segments.length > 0 ? segments[segments.length - 1]!.visibility : "visible";
      const positions = positionsByState.get(lastState)!;
      const left = this.directionAt(sampleCount - 1).normalize().multiplyScalar(TRAJECTORY_RADIUS);
      const right = this.directionAt(0).normalize().multiplyScalar(TRAJECTORY_RADIUS);
      // Només afegir segment de tancament si no coincideixen exactament en coordenades
      if (left.distanceToSquared(right) > 1e-8) {
        positions.push(left.x, left.y, left.z, right.x, right.y, right.z);
      }
    }

    this.legacyRoot.visible = false;
    for (const state of STATE_ORDER) {
      const line = this.ensureSegmentLine(state);
      const positions = positionsByState.get(state)!;
      if (positions.length >= 6) {
        line.geometry.setPositions(new Float32Array(positions));
      } else {
        line.geometry.setPositions(new Float32Array([0, 0, 0, 0, 0, 0]));
        line.geometry.instanceCount = 0;
      }
      line.geometry.computeBoundingSphere();
    }
    this.updateLayerVisibility();
  }

  private deriveSegments(visibility: Uint8Array): NonNullable<ApparentTrajectoryMetadata["segments"]> {
    if (visibility.length === 0) return [];
    const segments: Array<NonNullable<ApparentTrajectoryMetadata["segments"]>[number]> = [];
    let start = 0;
    let state = stateFromCode(visibility[0] ?? 3);
    for (let index = 1; index < visibility.length; index++) {
      const next = stateFromCode(visibility[index] ?? 3);
      if (next === state) continue;
      segments.push({
        startIndex: start,
        endIndex: index,
        visibility: state,
        horizonProvenance: "fallback_astronomical",
      });
      start = index;
      state = next;
    }
    segments.push({
      startIndex: start,
      endIndex: visibility.length - 1,
      visibility: state,
      horizonProvenance: "fallback_astronomical",
    });
    return segments;
  }

  private ensureSegmentLine(state: TrajectoryVisibilityState): SegmentLine {
    const existing = this.segmentLines.get(state);
    if (existing !== undefined) return existing;
    const geometry = new LineSegmentsGeometry();
    geometry.setPositions(new Float32Array([0, 0, 0, 0, 0, 0]));
    geometry.instanceCount = 0;
    const style = stateStyle(state);
    const baseProfile = state === "visible"
      ? OVERLAY_LINE_PROFILES.trajectoryPrimary
      : OVERLAY_LINE_PROFILES.trajectorySecondary;
    const materials = createOverlayLineMaterials(withOverlayColor(
      baseProfile,
      style.color,
      style.opacity,
      style.depthTest,
    ));
    setOverlayResolution(materials, 1920, 1080);
    const renderOrder = state === "terrain_occluded" ? 100 : (state === "below_astronomical_horizon" ? 95 : 90);
    const halo = new LineSegments2(geometry, materials.halo);
    halo.name = `apparentTrajectory:${state}:halo`;
    halo.frustumCulled = false;
    halo.renderOrder = renderOrder - 1;
    const core = new LineSegments2(geometry, materials.core);
    core.name = `apparentTrajectory:${state}:core`;
    core.frustumCulled = false;
    core.renderOrder = renderOrder;
    const root = new THREE.Group();
    root.name = `apparentTrajectory:${state}`;
    root.add(halo, core);

    const line = { root, geometry, materials };
    this.segmentLines.set(state, line);
    this.root.add(root);
    this._geometryBuildCount += 1;
    this._materialBuildCount += 2;
    return line;
  }

  private updateLayerVisibility(): void {
    for (const [state, line] of this.segmentLines) {
      const isVisible = this.enabled && (
        state === "visible"
        || state === "insufficient_data"
        || (state === "terrain_occluded" && this.showTerrainOccluded)
        || (state === "below_astronomical_horizon" && this.showBelowHorizon)
      );
      line.root.visible = isVisible;
    }
  }

  private applyEvents(events: readonly ApparentTrajectoryEvent[]): void {
    this.clearEvents();
    const rise: number[] = [];
    const set: number[] = [];
    for (const event of events) {
      if (event.kind === "tangent") continue;
      const position = threeFromEnu(event.directionENU).normalize().multiplyScalar(MARKER_RADIUS);
      (event.kind === "rise" ? rise : set).push(position.x, position.y, position.z);
      const label = this.createEventLabel(event, position);
      if (label !== null) this.labelRoot.add(label);
    }
    this.addEventPoints("rise", rise, 0x34d399);
    this.addEventPoints("set", set, 0xf87171);
  }

  private addEventPoints(name: string, positions: number[], color: number): void {
    if (positions.length === 0) return;
    const geometry = new THREE.BufferGeometry();
    geometry.setAttribute("position", new THREE.BufferAttribute(new Float32Array(positions), 3));
    const material = new THREE.PointsMaterial({
      color,
      size: 9,
      sizeAttenuation: false,
      depthTest: false,
      depthWrite: false,
    });
    const points = new THREE.Points(geometry, material);
    points.name = `apparentTrajectory:${name}-events`;
    points.userData.eventKind = name;
    points.renderOrder = 108;
    this.eventRoot.add(points);
    this._geometryBuildCount++;
    this._materialBuildCount++;
  }

  private createEventLabel(
    event: ApparentTrajectoryEvent,
    position: THREE.Vector3,
  ): THREE.Sprite | null {
    if (typeof document === "undefined") return null;
    const canvas = document.createElement("canvas");
    canvas.width = 310;
    canvas.height = 50;
    const context = canvas.getContext("2d");
    if (context === null) return null;

    context.clearRect(0, 0, canvas.width, canvas.height);

    // Rounded high-contrast card background
    const radius = 6;
    const x = 2;
    const y = 2;
    const w = canvas.width - 4;
    const h = canvas.height - 4;

    context.beginPath();
    context.moveTo(x + radius, y);
    context.lineTo(x + w - radius, y);
    context.quadraticCurveTo(x + w, y, x + w, y + radius);
    context.lineTo(x + w, y + h - radius);
    context.quadraticCurveTo(x + w, y + h, x + w - radius, y + h);
    context.lineTo(x + radius, y + h);
    context.quadraticCurveTo(x, y + h, x, y + h - radius);
    context.lineTo(x, y + radius);
    context.quadraticCurveTo(x, y, x + radius, y);
    context.closePath();

    context.fillStyle = "rgba(7, 12, 24, 0.88)";
    context.fill();

    const isRise = event.kind === "rise";
    const accentColor = isRise ? "#34d399" : "#f87171";
    context.lineWidth = 2;
    context.strokeStyle = accentColor;
    context.stroke();

    context.font = "bold 19px Segoe UI, Roboto, system-ui, sans-serif";
    context.fillStyle = accentColor;
    const symbol = isRise ? "↑ Alba" : "↓ Posta";
    context.fillText(symbol, 12, 32);

    context.font = "17px Segoe UI, Roboto, system-ui, sans-serif";
    context.fillStyle = "#f8fafc";
    const timeStr = new Date(event.instantUtc).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" });
    const azStr = `Az ${event.azimuthDeg.toFixed(1)}°`;
    context.fillText(`${timeStr} · ${azStr}`, 108, 32);

    const texture = new THREE.CanvasTexture(canvas);
    texture.needsUpdate = true;
    const material = new THREE.SpriteMaterial({
      map: texture,
      transparent: true,
      depthTest: false,
      depthWrite: false,
    });
    const sprite = new THREE.Sprite(material);
    sprite.name = `apparentTrajectory:${event.kind}-label`;
    sprite.position.copy(position).multiplyScalar(1.0015);
    sprite.userData.event = event;
    sprite.renderOrder = 110;

    const scale = this.calculateLabelScale();
    sprite.scale.set(scale.width, scale.height, 1);
    return sprite;
  }

  private calculateLabelScale(): { width: number; height: number } {
    const fovDeg = Math.max(0.01, this.currentFovDeg);
    const heightPx = Math.max(1, this.currentHeightPx);
    const fovRad = THREE.MathUtils.degToRad(fovDeg);
    const pixelsPerRad = heightPx / (2 * Math.tan(fovRad / 2));
    const targetHeightPx = 16; // Refined smaller height in CSS pixels on screen
    const worldHeight = targetHeightPx * (MARKER_RADIUS / pixelsPerRad);
    const aspectRatio = 310 / 50;
    return {
      width: worldHeight * aspectRatio,
      height: worldHeight,
    };
  }

  private updateLabelScales(): void {
    if (this.currentHeightPx <= 0 || this.labelRoot.children.length === 0) return;
    const { width, height } = this.calculateLabelScale();
    for (const child of this.labelRoot.children) {
      if (child instanceof THREE.Sprite) {
        child.scale.set(width, height, 1);
      }
    }
  }

  private clearEvents(): void {
    for (const child of [...this.eventRoot.children]) {
      child.removeFromParent();
      const points = child as THREE.Points<THREE.BufferGeometry, THREE.PointsMaterial>;
      points.geometry?.dispose();
      points.material?.dispose();
    }
    for (const child of [...this.labelRoot.children]) {
      child.removeFromParent();
      const sprite = child as THREE.Sprite;
      sprite.material.map?.dispose();
      sprite.material.dispose();
    }
  }

  private clearVisualData(): void {
    this.legacyGeometry.instanceCount = 0;
    this.legacyRoot.visible = false;
    for (const line of this.segmentLines.values()) {
      line.geometry.instanceCount = 0;
      line.root.visible = false;
    }
    this.activeMarker.visible = false;
    this.clearEvents();
    this.directions = new Float32Array();
    this.offsets = new Float32Array();
    this.validity = new Uint8Array();
    this.metadata = null;
    delete this.root.userData.trajectoryMetadata;
    delete this.root.userData.trajectoryCoverage;
  }

  private directionAt(index: number): THREE.Vector3 {
    const offset = index * 3;
    return threeFromEnu([
      this.directions[offset] ?? 0,
      this.directions[offset + 1] ?? 0,
      this.directions[offset + 2] ?? 0,
    ]);
  }
}

function stateFromCode(code: number): TrajectoryVisibilityState {
  return STATE_ORDER[code] ?? "insufficient_data";
}

function stateStyle(state: TrajectoryVisibilityState): {
  readonly color: number;
  readonly opacity: number;
  readonly depthTest: boolean;
} {
  switch (state) {
    case "visible":
      return {
        color: 0x38bdf8,
        opacity: 1.0,
        depthTest: true,
      };
    case "terrain_occluded":
      return {
        color: 0xd946ef,
        opacity: 0.95,
        depthTest: false,
      };
    case "below_astronomical_horizon":
      return {
        color: 0xc084fc,
        opacity: 0.90,
        depthTest: false,
      };
    case "insufficient_data":
      return {
        color: 0xfbbf24,
        opacity: 0.80,
        depthTest: true,
      };
  }
}
