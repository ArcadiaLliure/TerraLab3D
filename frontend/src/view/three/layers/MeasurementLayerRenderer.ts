import * as THREE from "three";
import { LineSegments2 } from "three/addons/lines/LineSegments2.js";
import { LineSegmentsGeometry } from "three/addons/lines/LineSegmentsGeometry.js";
import type { SceneDelta } from "../../../contracts/scene";
import type { AngularCoordinate, MeasurementDocumentSnapshot, MeasurementGeometrySnapshot, MeasurementSnapshot } from "../../../contracts/measurement_contracts";
import { setThreeFromAzimuthAltitude } from "../celestialCoordinates";
import { CELESTIAL_SCENE_RADIUS } from "../celestialScenePolicy";
import {
  createOverlayLineMaterials,
  disposeOverlayLineMaterials,
  OVERLAY_LINE_PROFILES,
  setOverlayIntensity,
  setOverlayResolution,
  type OverlayLineMaterials,
} from "../materials/OverlayLineStyle";

export type MeasurementPickPart = "start" | "end" | "edge";
export interface MeasurementPick { readonly measurementId: string; readonly part: MeasurementPickPart; }
interface Entry {
  version: number;
  line: LineSegments2;
  halo: LineSegments2;
  handles: THREE.Points;
  label: HTMLDivElement;
  measurement: MeasurementSnapshot;
}
export interface MeasurementLayerMetrics { readonly geometryBuildCount: number; readonly geometryDisposeCount: number; readonly activeEntityCount: number; readonly lastChangedEntityCount: number; readonly activeMaterialCount: number; }

/** Resol l'orientació visual d'una mesura sense confondre seguiment celeste i posició 3D fixa. */
export function setMeasurementPresentationQuaternion(
  measurement: Pick<MeasurementSnapshot, "tracking" | "fixedQuaternion">,
  trackingQuaternion: THREE.Quaternion,
  target: THREE.Quaternion,
): THREE.Quaternion {
  if (measurement.tracking) return target.copy(trackingQuaternion);
  const fixed = measurement.fixedQuaternion;
  return fixed ? target.set(fixed[0], fixed[1], fixed[2], fixed[3]) : target.identity();
}

export interface MeasurementLayerRenderer {
  applyDelta(delta: SceneDelta): void;
  mountLabels(container: HTMLElement): void;
  presentDocument(snapshot: MeasurementDocumentSnapshot): void;
  presentPreview(geometry: MeasurementGeometrySnapshot | null, tracking?: boolean, fixedQuaternion?: readonly [number, number, number, number] | null): void;
  pick(clientX: number, clientY: number, camera: THREE.Camera, viewport: DOMRect, trackingQuaternion?: THREE.Quaternion): MeasurementPick | null;
  updateLabels(camera: THREE.Camera, viewport: DOMRect, trackingQuaternion?: THREE.Quaternion): void;
  setHovered(id: string | null): void;
  updateTime(timeMs: number, trackingQuaternion?: THREE.Quaternion): void;
  restoreResources(): void;
  metrics(): MeasurementLayerMetrics;
  dispose(): void;
}

const RADIUS = CELESTIAL_SCENE_RADIUS.distantSky * 0.995;
const MAX_PREVIEW_VERTICES = 512;

export class MeasurementLayerRendererImpl implements MeasurementLayerRenderer {
  private readonly groupFixed = new THREE.Group();
  private readonly groupTracking = new THREE.Group();
  private hoveredId: string | null = null;
  private selectedMeasurementId: string | null = null;

  private readonly normalMaterials = createOverlayLineMaterials(OVERLAY_LINE_PROFILES.measurementNormal);
  private readonly hoverMaterials = createOverlayLineMaterials(OVERLAY_LINE_PROFILES.measurementHover);
  private readonly selectedMaterials = createOverlayLineMaterials(OVERLAY_LINE_PROFILES.measurementSelected);

  private readonly handleMaterial = new THREE.PointsMaterial({
    color: 0xffffff,
    size: 7,
    sizeAttenuation: false,
    transparent: true,
    opacity: 0.95,
    depthWrite: false,
    depthTest: false,
  });

  private readonly entries = new Map<string, Entry>();
  private readonly previewPositions = new Float32Array(MAX_PREVIEW_VERTICES * 3);
  private readonly previewGeometry = new LineSegmentsGeometry();
  private readonly previewLine: LineSegments2;
  private readonly previewHalo: LineSegments2;

  private mountedContainer: HTMLElement | null = null;
  private geometryBuildCount = 1;
  private geometryDisposeCount = 0;
  private lastChangedEntityCount = 0;
  private readonly projected = new THREE.Vector3();
  private readonly parentPosition = new THREE.Vector3();
  private readonly presentationQuaternion = new THREE.Quaternion();

  constructor(parentFixed: THREE.Group, _parentTracking: THREE.Group) {
    this.groupFixed.name = "measurement-layer-fixed";
    this.groupTracking.name = "measurement-layer-tracking";
    parentFixed.add(this.groupFixed);
    parentFixed.add(this.groupTracking);

    const initialRes = new THREE.Vector2(
      typeof window !== "undefined" && window.innerWidth ? window.innerWidth : 1920,
      typeof window !== "undefined" && window.innerHeight ? window.innerHeight : 1080
    );
    this.setAllResolutions(initialRes);

    this.previewGeometry.setPositions(this.previewPositions);
    this.previewGeometry.instanceCount = 0;

    this.previewHalo = new LineSegments2(this.previewGeometry, this.normalMaterials.halo);
    this.previewHalo.name = "measurement:preview:halo";
    this.previewHalo.renderOrder = 999;
    this.previewHalo.frustumCulled = false;
    this.previewHalo.visible = false;
    this.previewLine = new LineSegments2(this.previewGeometry, this.normalMaterials.core);
    this.previewLine.name = "measurement:preview:core";
    this.previewLine.renderOrder = 1000;
    this.previewLine.frustumCulled = false;
    this.previewLine.visible = false;
    this.groupFixed.add(this.previewHalo, this.previewLine);
  }

  mountLabels(container: HTMLElement): void { this.mountedContainer = container; }
  applyDelta(_delta: SceneDelta): void { /* Contracte històric; el snapshot v1 és la frontera autoritativa actual. */ }

  presentDocument(snapshot: MeasurementDocumentSnapshot): void {
    this.selectedMeasurementId = snapshot.selectedMeasurementId;
    const incoming = new Set(snapshot.measurements.map(item => item.measurementId));
    let changed = 0;
    for (const [id, entry] of this.entries) {
      if (!incoming.has(id)) { this.disposeEntry(entry); this.entries.delete(id); changed++; }
    }
    for (const measurement of snapshot.measurements) {
      const current = this.entries.get(measurement.measurementId);
      if (!current || current.version !== measurement.entityVersion) {
        if (current) this.disposeEntry(current);
        this.entries.set(measurement.measurementId, this.createEntry(measurement));
        changed++;
      } else {
        current.measurement = measurement;
        current.label.textContent = measurement.geometry.label;
      }
    }
    for (const entry of this.entries.values()) {
      this.updateEntryMaterials(entry);
    }
    this.lastChangedEntityCount = changed;
  }

  presentPreview(geometry: MeasurementGeometrySnapshot | null, tracking = true, fixedQuaternion: readonly [number, number, number, number] | null = null): void {
    if (!geometry || geometry.paths.length === 0) {
      this.previewGeometry.instanceCount = 0;
      this.previewLine.visible = false;
      this.previewHalo.visible = false;
      return;
    }
    const isTracking = tracking ?? true;
    const parentGroup = isTracking ? this.groupTracking : this.groupFixed;
    if (this.previewLine.parent !== parentGroup) parentGroup.add(this.previewLine);
    if (this.previewHalo.parent !== parentGroup) parentGroup.add(this.previewHalo);
    this.previewLine.quaternion.identity();
    this.previewHalo.quaternion.identity();
    if (!isTracking && fixedQuaternion) this.previewLine.quaternion.set(...fixedQuaternion);
    if (!isTracking && fixedQuaternion) this.previewHalo.quaternion.set(...fixedQuaternion);

    let cursor = 0;
    for (const path of geometry.paths) {
      for (let index = 1; index < path.length; index++) {
        if (cursor + 2 > MAX_PREVIEW_VERTICES) break;
        cursor = this.writeDirection(cursor, path[index - 1]!);
        cursor = this.writeDirection(cursor, path[index]!);
      }
    }
    if (cursor > 0) {
      const buffer = this.previewGeometry.attributes.instanceStart as THREE.InterleavedBufferAttribute;
      (buffer.data as any).needsUpdate = true;
      this.previewGeometry.instanceCount = Math.floor(cursor / 2);
      this.previewGeometry.computeBoundingBox();
      this.previewGeometry.computeBoundingSphere();
      this.previewLine.visible = true;
      this.previewHalo.visible = true;
    } else {
      this.previewGeometry.instanceCount = 0;
      this.previewLine.visible = false;
      this.previewHalo.visible = false;
    }
  }

  updateLabels(camera: THREE.Camera, viewport: DOMRect, trackingQuaternion = new THREE.Quaternion()): void {
    const res = new THREE.Vector2(viewport.width, viewport.height);
    this.setAllResolutions(res);
    this.groupFixed.parent?.getWorldPosition(this.parentPosition);
    for (const entry of this.entries.values()) {
      setThreeFromAzimuthAltitude(this.projected, entry.measurement.geometry.anchor.azimuthDeg, entry.measurement.geometry.anchor.altitudeDeg, RADIUS);
      setMeasurementPresentationQuaternion(entry.measurement, trackingQuaternion, this.presentationQuaternion);
      this.projected.applyQuaternion(this.presentationQuaternion);
      this.projected.add(this.parentPosition).project(camera);
      const visible = this.projected.z >= -1 && this.projected.z <= 1 && Math.abs(this.projected.x) <= 1.1 && Math.abs(this.projected.y) <= 1.1;
      entry.label.hidden = !visible;
      if (visible) entry.label.style.transform = `translate(${(this.projected.x + 1) * viewport.width / 2}px, ${(1 - this.projected.y) * viewport.height / 2}px)`;
    }
  }

  setHovered(id: string | null): void {
    if (this.hoveredId === id) return;
    const previous = this.hoveredId ? this.entries.get(this.hoveredId) : null;
    this.hoveredId = id;
    if (previous) this.updateEntryMaterials(previous);
    if (id) {
      const current = this.entries.get(id);
      if (current) this.updateEntryMaterials(current);
    }
  }

  updateTime(timeMs: number, trackingQuaternion?: THREE.Quaternion): void {
    if (trackingQuaternion) {
      this.groupTracking.quaternion.copy(trackingQuaternion);
    }
    // La mesura conserva la propietat de la pulsació; l'estil comú només
    // aplica una intensitat transitòria al nucli i al halo grocs.
    const pulse = Math.sin(timeMs / 360) * 0.5 + 0.5;
    setOverlayIntensity(this.selectedMaterials, 0.84 + pulse * 0.16);
    this.handleMaterial.opacity = 0.78 + pulse * 0.2;
  }

  restoreResources(): void {
    for (const materials of [this.normalMaterials, this.hoverMaterials, this.selectedMaterials]) {
      materials.core.needsUpdate = true;
      materials.halo.needsUpdate = true;
    }
    this.handleMaterial.needsUpdate = true;
  }

  metrics(): MeasurementLayerMetrics {
    return {
      geometryBuildCount: this.geometryBuildCount,
      geometryDisposeCount: this.geometryDisposeCount,
      activeEntityCount: this.entries.size,
      lastChangedEntityCount: this.lastChangedEntityCount,
      activeMaterialCount: 7,
    };
  }

  dispose(): void {
    for (const entry of this.entries.values()) this.disposeEntry(entry);
    this.entries.clear();
    this.previewGeometry.dispose();
    this.geometryDisposeCount++;
    disposeOverlayLineMaterials(this.normalMaterials);
    disposeOverlayLineMaterials(this.hoverMaterials);
    disposeOverlayLineMaterials(this.selectedMaterials);
    this.handleMaterial.dispose();
    this.groupFixed.removeFromParent();
    this.groupTracking.removeFromParent();
    this.mountedContainer = null;
  }

  private setAllResolutions(res: THREE.Vector2): void {
    setOverlayResolution(this.normalMaterials, res.x, res.y);
    setOverlayResolution(this.hoverMaterials, res.x, res.y);
    setOverlayResolution(this.selectedMaterials, res.x, res.y);
  }

  private updateEntryMaterials(entry: Entry): void {
    const isSelected = entry.measurement.measurementId === this.selectedMeasurementId;
    const isHovered = entry.measurement.measurementId === this.hoveredId;
    if (isSelected) {
      this.setEntryMaterials(entry, this.selectedMaterials);
      entry.handles.visible = true;
    } else if (isHovered) {
      this.setEntryMaterials(entry, this.hoverMaterials);
      entry.handles.visible = false;
    } else {
      this.setEntryMaterials(entry, this.normalMaterials);
      entry.handles.visible = false;
    }
  }

  private createEntry(measurement: MeasurementSnapshot): Entry {
    const positions: number[] = [];
    for (const path of measurement.geometry.paths) {
      for (let index = 1; index < path.length; index++) {
        this.pushDirection(positions, path[index - 1]!);
        this.pushDirection(positions, path[index]!);
      }
    }
    const geometry = new LineSegmentsGeometry();
    geometry.setPositions(positions);

    const isSelected = measurement.measurementId === this.selectedMeasurementId;
    const isHovered = measurement.measurementId === this.hoveredId;
    const materials = isSelected ? this.selectedMaterials : isHovered ? this.hoverMaterials : this.normalMaterials;

    const halo = new LineSegments2(geometry, materials.halo);
    halo.name = `measurement:${measurement.measurementId}:halo`;
    halo.frustumCulled = false;
    halo.renderOrder = 999;
    const line = new LineSegments2(geometry, materials.core);
    line.name = `measurement:${measurement.measurementId}:core`;
    line.frustumCulled = false;
    line.renderOrder = 1000;

    const handleGeometry = new THREE.BufferGeometry();
    const handles: number[] = [];
    this.pushDirection(handles, measurement.start);
    this.pushDirection(handles, measurement.end);
    handleGeometry.setAttribute("position", new THREE.Float32BufferAttribute(handles, 3));

    const points = new THREE.Points(handleGeometry, this.handleMaterial);
    points.frustumCulled = false;
    points.renderOrder = 1001;
    points.visible = isSelected;

    const label = document.createElement("div");
    label.className = "measurement-label";
    label.dataset.measurementId = measurement.measurementId;
    label.dataset.measurementKind = measurement.kind;
    label.textContent = measurement.geometry.label;
    this.mountedContainer?.appendChild(label);

    const isTracking = measurement.tracking;
    const parentGroup = isTracking ? this.groupTracking : this.groupFixed;
    if (!isTracking) {
      setMeasurementPresentationQuaternion(measurement, new THREE.Quaternion(), this.presentationQuaternion);
      line.quaternion.copy(this.presentationQuaternion);
      halo.quaternion.copy(this.presentationQuaternion);
      points.quaternion.copy(this.presentationQuaternion);
    }
    parentGroup.add(halo, line, points);
    this.geometryBuildCount += 2;

    return { version: measurement.entityVersion, line, halo, handles: points, label, measurement };
  }

  private disposeEntry(entry: Entry): void {
    entry.line.geometry.dispose();
    entry.handles.geometry.dispose();
    this.geometryDisposeCount += 2;
    entry.line.removeFromParent();
    entry.halo.removeFromParent();
    entry.handles.removeFromParent();
    entry.label.remove();
  }

  private setEntryMaterials(entry: Entry, materials: OverlayLineMaterials): void {
    entry.line.material = materials.core;
    entry.halo.material = materials.halo;
  }

  private pushDirection(target: number[], point: AngularCoordinate): void {
    const value = setThreeFromAzimuthAltitude(this.projected, point.azimuthDeg, point.altitudeDeg, RADIUS);
    target.push(value.x, value.y, value.z);
  }

  private writeDirection(cursor: number, point: AngularCoordinate): number {
    const value = setThreeFromAzimuthAltitude(this.projected, point.azimuthDeg, point.altitudeDeg, RADIUS);
    const base = cursor * 3;
    this.previewPositions[base] = value.x;
    this.previewPositions[base + 1] = value.y;
    this.previewPositions[base + 2] = value.z;
    return cursor + 1;
  }

  private screenPoint(point: AngularCoordinate, measurement: MeasurementSnapshot, camera: THREE.Camera, viewport: DOMRect, trackingQuaternion = new THREE.Quaternion()): readonly [number, number] | null {
    this.groupFixed.parent?.getWorldPosition(this.parentPosition);
    setThreeFromAzimuthAltitude(this.projected, point.azimuthDeg, point.altitudeDeg, RADIUS);
    setMeasurementPresentationQuaternion(measurement, trackingQuaternion, this.presentationQuaternion);
    this.projected.applyQuaternion(this.presentationQuaternion);
    this.projected.add(this.parentPosition).project(camera);
    if (this.projected.z < -1 || this.projected.z > 1) return null;
    return [viewport.left + (this.projected.x + 1) * viewport.width / 2, viewport.top + (1 - this.projected.y) * viewport.height / 2];
  }

  pick(clientX: number, clientY: number, camera: THREE.Camera, viewport: DOMRect, trackingQuaternion?: THREE.Quaternion): MeasurementPick | null {
    let winner: { distance: number; result: MeasurementPick } | null = null;
    for (const entry of this.entries.values()) {
      for (const [part, point] of [["start", entry.measurement.start], ["end", entry.measurement.end]] as const) {
        const distance = this.screenDistance(clientX, clientY, point, entry.measurement, camera, viewport, trackingQuaternion);
        if (distance <= 18 && (!winner || distance < winner.distance)) winner = { distance, result: { measurementId: entry.measurement.measurementId, part } };
      }
      for (const path of entry.measurement.geometry.paths) for (let index = 1; index < path.length; index++) {
        const first = this.screenPoint(path[index - 1]!, entry.measurement, camera, viewport, trackingQuaternion);
        const second = this.screenPoint(path[index]!, entry.measurement, camera, viewport, trackingQuaternion);
        if (!first || !second) continue;
        const distance = pointToSegmentDistance(clientX, clientY, first[0], first[1], second[0], second[1]);
        if (distance <= 15 && (!winner || distance < winner.distance)) winner = { distance, result: { measurementId: entry.measurement.measurementId, part: "edge" } };
      }
    }
    return winner?.result ?? null;
  }

  private screenDistance(clientX: number, clientY: number, point: AngularCoordinate, measurement: MeasurementSnapshot, camera: THREE.Camera, viewport: DOMRect, trackingQuaternion?: THREE.Quaternion): number {
    const projected = this.screenPoint(point, measurement, camera, viewport, trackingQuaternion);
    return projected ? Math.hypot(clientX - projected[0], clientY - projected[1]) : Number.POSITIVE_INFINITY;
  }
}

function pointToSegmentDistance(px: number, py: number, x0: number, y0: number, x1: number, y1: number): number {
  const dx = x1 - x0, dy = y1 - y0;
  const lengthSquared = dx * dx + dy * dy;
  const t = lengthSquared <= 1e-12 ? 0 : Math.max(0, Math.min(1, ((px - x0) * dx + (py - y0) * dy) / lengthSquared));
  return Math.hypot(px - (x0 + t * dx), py - (y0 + t * dy));
}
