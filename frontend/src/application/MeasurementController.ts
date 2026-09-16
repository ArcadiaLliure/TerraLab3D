import * as THREE from "three";
import type { WebSocketBridge } from "../bridge/WebSocketBridge";
import type { AngularCoordinate, MeasurementDocumentSnapshot, MeasurementErrorMessage, MeasurementKind, MeasurementSnapshot } from "../contracts/measurement_contracts";
import type { ToolsPage } from "../view/ui/drawer_pages/ToolsPage";
import type { CameraRigImpl } from "../view/three/CameraRigImpl";
import { azimuthAltitudeFromThreeDirection } from "../view/three/celestialCoordinates";
import type { MeasurementLayerRendererImpl, MeasurementPickPart } from "../view/three/layers/MeasurementLayerRenderer";
import type { PointerGestureRouter } from "../view/three/picking/PointerGestureRouter";
import { previewGeometry, rotateCoordinatePair } from "./measurementGeometry";

interface MeasurementControllerOptions {
  readonly canvas: HTMLCanvasElement;
  readonly camera: THREE.PerspectiveCamera;
  readonly bridge: WebSocketBridge;
  readonly cameraRig: CameraRigImpl;
  readonly gestureRouter: PointerGestureRouter;
  readonly renderer: MeasurementLayerRendererImpl;
  readonly presentDocument: (snapshot: MeasurementDocumentSnapshot) => void;
  readonly toolsPage: ToolsPage;
  readonly isTrackingEnabled: () => boolean;
  readonly getTrackingQuaternion: () => THREE.Quaternion;
}

interface ActiveGesture {
  readonly pointerId: number;
  readonly origin: AngularCoordinate;
  readonly measurement: MeasurementSnapshot | null;
  readonly part: MeasurementPickPart | "create";
  current: AngularCoordinate;
  moved: boolean;
}

/** Interpreta gestos de pantalla i envia només intencions angulars al backend. */
export class MeasurementController {
  private readonly raycaster = new THREE.Raycaster();
  private readonly pointerNdc = new THREE.Vector2();
  private snapshot: MeasurementDocumentSnapshot | null = null;
  private activeTool: MeasurementKind | null = null;
  private gesture: ActiveGesture | null = null;
  private commandPending = false;
  private lastClientX = 0;
  private lastClientY = 0;

  constructor(private readonly options: MeasurementControllerOptions) {
    options.canvas.addEventListener("pointerdown", this.onPointerDown, true);
    options.canvas.addEventListener("pointermove", this.onPointerMove, true);
    options.canvas.addEventListener("pointerup", this.onPointerUp, true);
    options.canvas.addEventListener("pointercancel", this.onPointerCancel, true);
    window.addEventListener("keydown", this.onKeyDown, true);
  }

  setTool(kind: MeasurementKind | null): void {
    if (this.commandPending && kind !== null) return;
    this.cancelGesture();
    this.activeTool = this.activeTool === kind ? null : kind;
    this.options.toolsPage.presentActiveTool(this.activeTool);
    this.syncInteractionOwnership();
  }

  undo(): void { this.sendSimpleCommand("undo"); }
  redo(): void { this.sendSimpleCommand("redo"); }
  clear(): void { this.sendSimpleCommand("clear"); }

  setTrackingEnabled(enabled: boolean): void {
    if (this.commandPending || this.snapshot?.trackingEnabled === enabled) return;
    const current = this.options.getTrackingQuaternion();
    this.sendCommand({
      action: "set_tracking",
      tracking: enabled,
      fixedQuaternion: enabled ? null : [current.x, current.y, current.z, current.w],
    });
  }

  deleteSelected(): void {
    const selected = this.snapshot?.selectedMeasurementId;
    if (!selected || this.commandPending) return;
    this.sendCommand({ action: "delete", measurementId: selected });
  }

  present(snapshot: MeasurementDocumentSnapshot): void {
    if (this.snapshot && snapshot.measurementRevision < this.snapshot.measurementRevision) return;
    this.snapshot = snapshot;
    this.commandPending = false;
    this.options.presentDocument(snapshot);
    this.options.toolsPage.presentMeasurements(snapshot);
  }

  presentError(error: MeasurementErrorMessage): void {
    if (error.requestedRevision < (this.snapshot?.measurementRevision ?? 0)) return;
    this.commandPending = false;
    this.options.toolsPage.presentMeasurementError(error.message);
  }

  dispose(): void {
    this.cancelGesture();
    this.activeTool = null;
    this.syncInteractionOwnership();
    this.options.canvas.removeEventListener("pointerdown", this.onPointerDown, true);
    this.options.canvas.removeEventListener("pointermove", this.onPointerMove, true);
    this.options.canvas.removeEventListener("pointerup", this.onPointerUp, true);
    this.options.canvas.removeEventListener("pointercancel", this.onPointerCancel, true);
    window.removeEventListener("keydown", this.onKeyDown, true);
  }

  private readonly onPointerDown = (event: PointerEvent): void => {
    if (event.button !== 0 || this.commandPending) return;
    if (this.activeTool !== null) {
      const coordinate = this.coordinateAt(event.clientX, event.clientY, this.options.isTrackingEnabled());
      if (!coordinate) return;
      this.beginGesture(event, coordinate, null, "create");
      return;
    }
    const hit = this.options.renderer.pick(event.clientX, event.clientY, this.options.camera, this.options.canvas.getBoundingClientRect(), this.options.getTrackingQuaternion());
    if (!hit) return;
    const measurement = this.snapshot?.measurements.find(item => item.measurementId === hit.measurementId);
    if (measurement) {
      const coordinate = this.coordinateAt(event.clientX, event.clientY, measurement);
      if (!coordinate) return;
      this.beginGesture(event, coordinate, measurement, hit.part);
    }
  };

  private readonly onPointerMove = (event: PointerEvent): void => {
    const gesture = this.gesture;
    if (!gesture) {
      if (this.activeTool === null && !this.commandPending) {
        const hit = this.options.renderer.pick(event.clientX, event.clientY, this.options.camera, this.options.canvas.getBoundingClientRect(), this.options.getTrackingQuaternion());
        this.options.renderer.setHovered(hit?.measurementId ?? null);
        if (hit) this.options.canvas.style.cursor = "pointer";
        else this.options.canvas.style.cursor = "";
      }
      return;
    }
    if (gesture.pointerId !== event.pointerId) return;
    const coordinate = this.coordinateAt(event.clientX, event.clientY);
    if (!coordinate) return;
    gesture.current = coordinate;
    gesture.moved ||= Math.hypot(event.clientX - this.lastClientX, event.clientY - this.lastClientY) > 1;
    this.lastClientX = event.clientX;
    this.lastClientY = event.clientY;
    const candidate = this.gesture ? this.candidateForGesture(this.gesture) : null;
    this.options.renderer.presentPreview(candidate ? previewGeometry(candidate.kind, candidate.start, candidate.end, candidate.rotationDeg) : null, candidate?.tracking, candidate?.fixedQuaternion);
    event.preventDefault();
    event.stopImmediatePropagation();
  };

  private readonly onPointerUp = (event: PointerEvent): void => {
    const gesture = this.gesture;
    if (!gesture || gesture.pointerId !== event.pointerId) return;
    
    // Capture precise final coordinate
    const coordinate = this.coordinateAt(event.clientX, event.clientY);
    if (coordinate) gesture.current = coordinate;
    
    event.preventDefault();
    event.stopImmediatePropagation();
    const candidate = this.candidateForGesture(gesture);
    this.finishGesture();
    if (!candidate || !previewGeometry(candidate.kind, candidate.start, candidate.end, candidate.rotationDeg)) return;
    if (gesture.part === "create") {
      this.sendCommand({ action: "create", kind: candidate.kind, start: candidate.start, end: candidate.end, rotationDeg: candidate.rotationDeg, tracking: candidate.tracking, fixedQuaternion: candidate.fixedQuaternion });
      this.activeTool = null;
      this.options.toolsPage.presentActiveTool(null);
      this.syncInteractionOwnership();
    } else if (gesture.moved) {
      this.sendCommand({ action: "update", measurementId: candidate.measurementId, kind: candidate.kind, start: candidate.start, end: candidate.end, rotationDeg: candidate.rotationDeg, tracking: candidate.tracking, fixedQuaternion: candidate.fixedQuaternion });
    } else {
      this.sendCommand({ action: "select", measurementId: candidate.measurementId });
    }
  };

  private readonly onPointerCancel = (event: PointerEvent): void => {
    if (this.gesture?.pointerId === event.pointerId) this.cancelGesture();
  };

  private readonly onKeyDown = (event: KeyboardEvent): void => {
    const target = event.target as HTMLElement | null;
    if (target?.matches("input, textarea, select, [contenteditable='true']")) return;
    if (event.key === "Escape" && (this.gesture || this.activeTool)) {
      event.preventDefault();
      event.stopImmediatePropagation();
      this.cancelGesture();
      this.activeTool = null;
      this.options.toolsPage.presentActiveTool(null);
      this.syncInteractionOwnership();
      return;
    }
    if ((event.key === "Delete" || event.key === "Backspace") && this.snapshot?.selectedMeasurementId) {
      event.preventDefault();
      this.deleteSelected();
      return;
    }
    if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "z") {
      event.preventDefault();
      event.shiftKey ? this.redo() : this.undo();
    } else if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "y") {
      event.preventDefault();
      this.redo();
    }
  };

  private beginGesture(event: PointerEvent, coordinate: AngularCoordinate, measurement: MeasurementSnapshot | null, part: MeasurementPickPart | "create"): void {
    this.gesture = { pointerId: event.pointerId, origin: coordinate, current: coordinate, measurement, part, moved: false };
    this.lastClientX = event.clientX;
    this.lastClientY = event.clientY;
    this.options.canvas.setPointerCapture(event.pointerId);
    this.syncInteractionOwnership();
    event.preventDefault();
    event.stopImmediatePropagation();
  }

  private finishGesture(): void {
    if (this.gesture && this.options.canvas.hasPointerCapture(this.gesture.pointerId)) this.options.canvas.releasePointerCapture(this.gesture.pointerId);
    this.gesture = null;
    this.options.renderer.presentPreview(null);
    this.syncInteractionOwnership();
  }

  private cancelGesture(): void { this.finishGesture(); }

  private candidateForGesture(gesture: ActiveGesture): MeasurementSnapshot | null {
    if (gesture.part === "create") {
      if (!this.activeTool) return null;
      const tracking = this.options.isTrackingEnabled();
      return { measurementId: "preview", kind: this.activeTool, start: gesture.origin, end: gesture.current, rotationDeg: 0, tracking, fixedQuaternion: tracking ? null : [0, 0, 0, 1], entityVersion: 0, geometry: { paths: [], label: "", anchor: gesture.origin } };
    }
    const measurement = gesture.measurement;
    if (!measurement) return null;
    if (gesture.part === "start" && measurement.kind === "ruler") return { ...measurement, start: gesture.current };
    if (gesture.part === "end") return { ...measurement, end: gesture.current };
    const [start, end] = rotateCoordinatePair(measurement.start, measurement.end, gesture.origin, gesture.current);
    return { ...measurement, start, end };
  }

  private coordinateAt(clientX: number, clientY: number, frame?: boolean | MeasurementSnapshot): AngularCoordinate | null {
    const rect = this.options.canvas.getBoundingClientRect();
    this.pointerNdc.x = ((clientX - rect.left) / rect.width) * 2 - 1;
    this.pointerNdc.y = -((clientY - rect.top) / rect.height) * 2 + 1;
    this.raycaster.setFromCamera(this.pointerNdc, this.options.camera);
    const direction = this.raycaster.ray.direction.clone();
    const measurement = typeof frame === "object" ? frame : (frame === undefined ? this.gesture?.measurement : null);
    const useTracking = typeof frame === "boolean" ? frame : (measurement?.tracking ?? this.options.isTrackingEnabled());
    const quaternion = useTracking
      ? this.options.getTrackingQuaternion().clone()
      : measurement?.fixedQuaternion
        ? new THREE.Quaternion(...measurement.fixedQuaternion)
        : null;
    if (quaternion) direction.applyQuaternion(quaternion.invert());
    return azimuthAltitudeFromThreeDirection(direction);
  }

  private sendSimpleCommand(action: "undo" | "redo" | "clear"): void {
    if (!this.commandPending) this.sendCommand({ action });
  }

  private sendCommand(command: Omit<Parameters<WebSocketBridge["sendMeasurementCommand"]>[0], "measurementRevision">): void {
    this.commandPending = true;
    this.options.toolsPage.presentMeasurementPending();
    this.options.bridge.sendMeasurementCommand({ measurementRevision: (this.snapshot?.measurementRevision ?? 0) + 1, ...command });
  }

  private syncInteractionOwnership(): void {
    const ownsPointer = this.activeTool !== null || this.gesture !== null;
    this.options.cameraRig.setInteractionBlocked(ownsPointer);
    this.options.gestureRouter.setEnabled(!ownsPointer);
  }
}
