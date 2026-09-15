import * as THREE from "three";
import { LineSegments2 } from "three/addons/lines/LineSegments2.js";
import { LineSegmentsGeometry } from "three/addons/lines/LineSegmentsGeometry.js";
import { LineMaterial } from "three/addons/lines/LineMaterial.js";
import type { SceneDelta } from "../../../contracts/scene";
import type { AngularCoordinate, MeasurementDocumentSnapshot, MeasurementGeometrySnapshot, MeasurementSnapshot } from "../../../contracts/measurement_contracts";
import { setThreeFromAzimuthAltitude } from "../celestialCoordinates";
import { CELESTIAL_SCENE_RADIUS } from "../celestialScenePolicy";

export type MeasurementPickPart = "start" | "end" | "edge";
export interface MeasurementPick { readonly measurementId: string; readonly part: MeasurementPickPart; }
interface Entry {
  version: number;
  line: LineSegments2;
  handles: THREE.Points;
  label: HTMLDivElement;
  measurement: MeasurementSnapshot;
}
export interface MeasurementLayerMetrics { readonly geometryBuildCount: number; readonly geometryDisposeCount: number; readonly activeEntityCount: number; readonly lastChangedEntityCount: number; }

export interface MeasurementLayerRenderer {
  applyDelta(delta: SceneDelta): void;
  mountLabels(container: HTMLElement): void;
  presentDocument(snapshot: MeasurementDocumentSnapshot): void;
  presentPreview(geometry: MeasurementGeometrySnapshot | null, tracking?: boolean): void;
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

  // Solid, seamless, smoothed lines without bead artifacts (NormalBlending, opacity 1.0)
  private readonly normalMaterial = new LineMaterial({
    color: 0x00f0ff,
    linewidth: 3.5,
    transparent: true,
    opacity: 1.0,
    depthWrite: false,
    depthTest: false,
    blending: THREE.NormalBlending,
  });

  private readonly hoverMaterial = new LineMaterial({
    color: 0xffffff,
    linewidth: 6.0,
    transparent: true,
    opacity: 1.0,
    depthWrite: false,
    depthTest: false,
    blending: THREE.NormalBlending,
  });

  private readonly selectedMaterial = new LineMaterial({
    color: 0xffb700,
    linewidth: 5.0,
    transparent: true,
    opacity: 1.0,
    depthWrite: false,
    depthTest: false,
    blending: THREE.NormalBlending,
  });

  private readonly previewMaterial = new LineMaterial({
    color: 0x00f0ff,
    linewidth: 3.5,
    transparent: true,
    opacity: 1.0,
    depthWrite: false,
    depthTest: false,
    blending: THREE.NormalBlending,
  });

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

  private mountedContainer: HTMLElement | null = null;
  private geometryBuildCount = 1;
  private geometryDisposeCount = 0;
  private lastChangedEntityCount = 0;
  private readonly projected = new THREE.Vector3();
  private readonly parentPosition = new THREE.Vector3();

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

    this.previewLine = new LineSegments2(this.previewGeometry, this.previewMaterial);
    this.previewLine.renderOrder = 1000;
    this.previewLine.frustumCulled = false;
    this.previewLine.visible = false;
    this.groupFixed.add(this.previewLine);
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

  presentPreview(geometry: MeasurementGeometrySnapshot | null, tracking = true): void {
    if (!geometry || geometry.paths.length === 0) {
      this.previewGeometry.instanceCount = 0;
      this.previewLine.visible = false;
      return;
    }
    const isTracking = tracking ?? true;
    const parentGroup = isTracking ? this.groupTracking : this.groupFixed;
    if (this.previewLine.parent !== parentGroup) parentGroup.add(this.previewLine);

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
    } else {
      this.previewGeometry.instanceCount = 0;
      this.previewLine.visible = false;
    }
  }

  updateLabels(camera: THREE.Camera, viewport: DOMRect, trackingQuaternion = new THREE.Quaternion()): void {
    const res = new THREE.Vector2(viewport.width, viewport.height);
    this.setAllResolutions(res);
    this.groupFixed.parent?.getWorldPosition(this.parentPosition);
    for (const entry of this.entries.values()) {
      setThreeFromAzimuthAltitude(this.projected, entry.measurement.geometry.anchor.azimuthDeg, entry.measurement.geometry.anchor.altitudeDeg, RADIUS);
      const isTracking = entry.measurement.tracking ?? true;
      if (isTracking) this.projected.applyQuaternion(trackingQuaternion);
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
    // Pulse selected line between gold (0xffd200) and warm amber (0xff8800) without altering opacity
    const pulse = Math.sin(timeMs / 200) * 0.5 + 0.5; // 0 to 1
    this.selectedMaterial.color.setRGB(1.0, 0.65 + pulse * 0.22, pulse * 0.1);
    this.handleMaterial.opacity = 0.7 + pulse * 0.3;
  }

  restoreResources(): void {
    for (const material of [
      this.normalMaterial,
      this.hoverMaterial,
      this.selectedMaterial,
      this.previewMaterial,
      this.handleMaterial
    ]) material.needsUpdate = true;
  }

  metrics(): MeasurementLayerMetrics {
    return {
      geometryBuildCount: this.geometryBuildCount,
      geometryDisposeCount: this.geometryDisposeCount,
      activeEntityCount: this.entries.size,
      lastChangedEntityCount: this.lastChangedEntityCount
    };
  }

  dispose(): void {
    for (const entry of this.entries.values()) this.disposeEntry(entry);
    this.entries.clear();
    this.previewGeometry.dispose();
    this.geometryDisposeCount++;
    this.normalMaterial.dispose();
    this.hoverMaterial.dispose();
    this.selectedMaterial.dispose();
    this.previewMaterial.dispose();
    this.handleMaterial.dispose();
    this.groupFixed.removeFromParent();
    this.groupTracking.removeFromParent();
    this.mountedContainer = null;
  }

  private setAllResolutions(res: THREE.Vector2): void {
    this.normalMaterial.resolution = res;
    this.hoverMaterial.resolution = res;
    this.selectedMaterial.resolution = res;
    this.previewMaterial.resolution = res;
  }

  private updateEntryMaterials(entry: Entry): void {
    const isSelected = entry.measurement.measurementId === this.selectedMeasurementId;
    const isHovered = entry.measurement.measurementId === this.hoveredId;
    if (isSelected) {
      entry.line.material = this.selectedMaterial;
      entry.handles.visible = true;
    } else if (isHovered) {
      entry.line.material = this.hoverMaterial;
      entry.handles.visible = false;
    } else {
      entry.line.material = this.normalMaterial;
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
    const mat = isSelected ? this.selectedMaterial : isHovered ? this.hoverMaterial : this.normalMaterial;

    const line = new LineSegments2(geometry, mat);
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

    const isTracking = measurement.tracking ?? true;
    const parentGroup = isTracking ? this.groupTracking : this.groupFixed;
    parentGroup.add(line, points);
    this.geometryBuildCount += 2;

    return { version: measurement.entityVersion, line, handles: points, label, measurement };
  }

  private disposeEntry(entry: Entry): void {
    entry.line.geometry.dispose();
    entry.handles.geometry.dispose();
    this.geometryDisposeCount += 2;
    entry.line.removeFromParent();
    entry.handles.removeFromParent();
    entry.label.remove();
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

  private screenPoint(point: AngularCoordinate, camera: THREE.Camera, viewport: DOMRect, tracking = true, trackingQuaternion?: THREE.Quaternion): readonly [number, number] | null {
    this.groupFixed.parent?.getWorldPosition(this.parentPosition);
    setThreeFromAzimuthAltitude(this.projected, point.azimuthDeg, point.altitudeDeg, RADIUS);
    if (tracking && trackingQuaternion) this.projected.applyQuaternion(trackingQuaternion);
    this.projected.add(this.parentPosition).project(camera);
    if (this.projected.z < -1 || this.projected.z > 1) return null;
    return [viewport.left + (this.projected.x + 1) * viewport.width / 2, viewport.top + (1 - this.projected.y) * viewport.height / 2];
  }

  pick(clientX: number, clientY: number, camera: THREE.Camera, viewport: DOMRect, trackingQuaternion?: THREE.Quaternion): MeasurementPick | null {
    let winner: { distance: number; result: MeasurementPick } | null = null;
    for (const entry of this.entries.values()) {
      const isTracking = entry.measurement.tracking ?? true;
      for (const [part, point] of [["start", entry.measurement.start], ["end", entry.measurement.end]] as const) {
        const distance = this.screenDistance(clientX, clientY, point, camera, viewport, isTracking, trackingQuaternion);
        if (distance <= 18 && (!winner || distance < winner.distance)) winner = { distance, result: { measurementId: entry.measurement.measurementId, part } };
      }
      for (const path of entry.measurement.geometry.paths) for (let index = 1; index < path.length; index++) {
        const first = this.screenPoint(path[index - 1]!, camera, viewport, isTracking, trackingQuaternion);
        const second = this.screenPoint(path[index]!, camera, viewport, isTracking, trackingQuaternion);
        if (!first || !second) continue;
        const distance = pointToSegmentDistance(clientX, clientY, first[0], first[1], second[0], second[1]);
        if (distance <= 15 && (!winner || distance < winner.distance)) winner = { distance, result: { measurementId: entry.measurement.measurementId, part: "edge" } };
      }
    }
    return winner?.result ?? null;
  }

  private screenDistance(clientX: number, clientY: number, point: AngularCoordinate, camera: THREE.Camera, viewport: DOMRect, tracking = false, trackingQuaternion?: THREE.Quaternion): number {
    const projected = this.screenPoint(point, camera, viewport, tracking, trackingQuaternion);
    return projected ? Math.hypot(clientX - projected[0], clientY - projected[1]) : Number.POSITIVE_INFINITY;
  }
}

function pointToSegmentDistance(px: number, py: number, x0: number, y0: number, x1: number, y1: number): number {
  const dx = x1 - x0, dy = y1 - y0;
  const lengthSquared = dx * dx + dy * dy;
  const t = lengthSquared <= 1e-12 ? 0 : Math.max(0, Math.min(1, ((px - x0) * dx + (py - y0) * dy) / lengthSquared));
  return Math.hypot(px - (x0 + t * dx), py - (y0 + t * dy));
}
