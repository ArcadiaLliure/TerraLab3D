import * as THREE from "three";
import type { WebSocketBridge } from "../bridge/WebSocketBridge";
import type {
  CameraCaptureSnapshot,
  ObservationErrorMessage,
  ObservationMode,
  ObservationSnapshotMessage,
  TelescopeSnapshot,
} from "../contracts/observation_contracts";
import type { CameraPose } from "../view/three/CameraRig";
import type { CameraRigImpl } from "../view/three/CameraRigImpl";
import type { CelestialTransformState } from "../view/three/CelestialTransformState";
import { setThreeFromAzimuthAltitude } from "../view/three/celestialCoordinates";
import type { ThreeSceneHostImpl } from "../view/three/ThreeSceneHostImpl";
import type { StarTrailLayerRendererImpl } from "../view/three/layers/StarTrailLayerRendererImpl";
import type { TrackingTargetResolver } from "../view/three/picking/TrackingTargetResolver";
import type { FocusTrackingController } from "../view/three/picking/FocusTrackingController";
import type { LocationPage } from "../view/ui/drawer_pages/LocationPage";
import type { OpticsPanelImpl } from "../view/ui/panels/OpticsPanelImpl";
import type { ObservationHUD } from "../view/ui/panels/ObservationHUD";
import type { CameraProfileMessage } from "../contracts/observation_contracts";
import type { CelestialTargetRef } from "../contracts/celestial_selection_contracts";

export function cameraDeepQueryKey(
  azimuthDeg: number,
  altitudeDeg: number,
  instrumentalDiagonalDeg: number,
  photometricLimit: number,
): string {
  return [
    azimuthDeg.toFixed(6), altitudeDeg.toFixed(6),
    instrumentalDiagonalDeg.toFixed(6), photometricLimit.toFixed(4),
  ].join(":");
}

export class ObservationModeController {
  private snapshot: ObservationSnapshotMessage | null = null;
  private deepQueryRevision = 0;
  private gotoRevision = 0;
  private pendingDeepTimer: number | null = null;
  private lastDeepKey = "";
  private deepActive = false;
  private selectedTarget: CelestialTargetRef | null = null;
  private pendingCamera: CameraCaptureSnapshot | null = null;
  private cameraMutationTimer: number | null = null;
  private readonly direction = new THREE.Vector3();

  constructor(
    private readonly bridge: WebSocketBridge,
    private readonly sceneHost: ThreeSceneHostImpl,
    private readonly cameraRig: CameraRigImpl,
    private readonly transform: CelestialTransformState,
    private readonly trackingResolver: TrackingTargetResolver,
    private readonly focusTrackingController: FocusTrackingController,
    private readonly trailRenderer: StarTrailLayerRendererImpl,
    private readonly locationPage: LocationPage,
    private readonly panel: OpticsPanelImpl,
    private readonly hud: ObservationHUD,
  ) {
    window.addEventListener("keydown", this.onGlobalKeyDown, true);
    this.sceneHost.renderer.domElement.addEventListener("wheel", this.onInstrumentWheel, { capture: true, passive: false });
    this.sceneHost.getImagingPreviewLayerRenderer().attachRotationInteraction(
      this.sceneHost.renderer.domElement,
      rotationDeg => this.updateCamera({ frameRotationDeg: rotationDeg }),
    );
  }

  requestMode(mode: ObservationMode): void {
    if (mode === "eye") this.focusTrackingController.stopTracking();
    this.bridge.setObservationMode(mode, (this.snapshot?.observationRevision ?? 0) + 1);
  }

  configureCamera(camera: CameraCaptureSnapshot): void {
    this.bridge.configureCamera(camera, (this.snapshot?.observationRevision ?? 0) + 1);
  }

  configureTelescope(telescope: TelescopeSnapshot): void {
    this.bridge.configureTelescope(telescope, (this.snapshot?.observationRevision ?? 0) + 1);
  }

  mutateProfile(message: Omit<CameraProfileMessage, "type" | "observationRevision">): void {
    this.bridge.mutateCameraProfile({
      ...message,
      observationRevision: (this.snapshot?.observationRevision ?? 0) + 1,
    });
  }

  present(snapshot: ObservationSnapshotMessage): void {
    if (this.snapshot && snapshot.observationRevision < this.snapshot.observationRevision) return;
    if (snapshot.deepCatalog.deepQueryRevision < (this.snapshot?.deepCatalog.deepQueryRevision ?? 0)) return;
    this.snapshot = snapshot;
    this.panel.present(snapshot);
    this.hud.present(snapshot);
    this.locationPage.presentObservationMode(snapshot.mode);
    this.sceneHost.presentObservation(snapshot);
    if (this.cameraMutationTimer === null) this.pendingCamera = null;
    this.syncInstrumentTracking();

    const cameraPreview = snapshot.mode === "camera" && !snapshot.camera.trackingEnabled;
    this.trailRenderer.setCameraPreview(
      cameraPreview,
      snapshot.camera.exposureSeconds,
      snapshot.photographicPreview?.estimatedLimitMagnitude ?? 8.0,
    );
    this.sceneHost.getStarFieldRenderer().setMagnitudeLimit(
      snapshot.mode === "camera"
        ? snapshot.photographicPreview?.estimatedLimitMagnitude ?? 8.0
        : 8.0,
    );
    if (snapshot.mode === "camera") {
      this.scheduleDeepQuery(this.cameraRig.pose());
    } else {
      this.cancelDeepQuery();
    }
  }

  presentError(error: ObservationErrorMessage): void {
    if (error.requestedRevision <= (this.snapshot?.observationRevision ?? 0)) return;
    this.panel.presentError(error);
  }

  onScientificPointingChanged(pose: CameraPose): void {
    if (this.snapshot?.mode === "camera") this.scheduleDeepQuery(pose);
  }

  onSelectionChanged(target: CelestialTargetRef | null): void {
    this.selectedTarget = target;
    this.syncInstrumentTracking();
  }

  manualGoto(raDeg: number, decDeg: number): void {
    const revision = ++this.gotoRevision;
    const resolved = this.trackingResolver.resolve({ kind: "coordinate", raDeg, decDeg, frame: "J2000" });
    if (!resolved || revision !== this.gotoRevision) return;
    this.cameraRig.animateTo(
      resolved.azimuthDeg, resolved.altitudeDeg,
      this.cameraRig.pose().horizontalFovDeg, 600,
    );
  }

  gotoTarget(target: CelestialTargetRef | null): void {
    const revision = ++this.gotoRevision;
    const resolved = this.trackingResolver.resolve(target);
    if (!resolved || revision !== this.gotoRevision) return;
    this.cameraRig.animateTo(
      resolved.azimuthDeg, resolved.altitudeDeg,
      this.cameraRig.pose().horizontalFovDeg, 600,
    );
  }

  acceptsDeepResource(metadata: { role?: string; deepQueryRevision?: number }): boolean {
    return metadata.role !== "deep_tile" || metadata.deepQueryRevision === this.deepQueryRevision;
  }

  dispose(): void {
    this.cancelDeepQuery();
    if (this.cameraMutationTimer !== null) window.clearTimeout(this.cameraMutationTimer);
    window.removeEventListener("keydown", this.onGlobalKeyDown, true);
    this.sceneHost.renderer.domElement.removeEventListener("wheel", this.onInstrumentWheel, true);
    this.sceneHost.getImagingPreviewLayerRenderer().detachRotationInteraction();
    this.trailRenderer.setCameraPreview(false, 0, 8.0);
  }

  private syncInstrumentTracking(): void {
    const snapshot = this.snapshot;
    const shouldTrack = snapshot?.mode === "telescope"
      || (snapshot?.mode === "camera" && snapshot.camera.trackingEnabled);
    if (shouldTrack && this.selectedTarget) {
      this.focusTrackingController.startTracking(this.selectedTarget, true);
    } else {
      this.focusTrackingController.stopTracking();
    }
  }

  private updateCamera(update: Partial<CameraCaptureSnapshot>): void {
    const base = this.pendingCamera ?? this.snapshot?.camera;
    if (!base || this.snapshot?.mode !== "camera") return;
    this.pendingCamera = { ...base, ...update };
    if (this.cameraMutationTimer !== null) window.clearTimeout(this.cameraMutationTimer);
    this.cameraMutationTimer = window.setTimeout(() => {
      this.cameraMutationTimer = null;
      const camera = this.pendingCamera;
      if (!camera) return;
      this.pendingCamera = null;
      this.configureCamera(camera);
    }, 80);
  }

  private readonly onGlobalKeyDown = (event: KeyboardEvent): void => {
    if (event.key !== "Escape") return;
    this.focusTrackingController.stopTracking();
    if (this.snapshot?.mode !== "eye") this.requestMode("eye");
  };

  private readonly onInstrumentWheel = (event: WheelEvent): void => {
    if (!event.ctrlKey || this.snapshot?.mode !== "camera") return;
    event.preventDefault();
    event.stopImmediatePropagation();
    const base = this.pendingCamera?.focalLengthMm ?? this.snapshot.camera.focalLengthMm;
    const focalLengthMm = THREE.MathUtils.clamp(base * Math.exp(-event.deltaY * 0.0015), 0.1, 100_000);
    this.updateCamera({ focalLengthMm });
  };

  private scheduleDeepQuery(pose: CameraPose): void {
    const snapshot = this.snapshot;
    const field = snapshot?.field;
    const limit = snapshot?.photographicPreview?.estimatedLimitMagnitude;
    if (!snapshot || snapshot.mode !== "camera" || !field || limit === undefined || limit <= 8.0) {
      this.cancelDeepQuery();
      return;
    }
    if (!this.transform.isValid) return;
    const key = cameraDeepQueryKey(
      pose.azimuthDeg,
      pose.altitudeDeg,
      field.diagonalDeg ?? field.widthDeg,
      limit,
    );
    if (key === this.lastDeepKey) return;
    this.lastDeepKey = key;
    if (this.pendingDeepTimer !== null) window.clearTimeout(this.pendingDeepTimer);
    if (this.deepActive) {
      this.deepActive = false;
      this.bridge.cancelCameraDepth(++this.deepQueryRevision);
    }
    // Never show stars from the previous cone while the new scientific key
    // is being debounced or calculated.
    this.sceneHost.getStarFieldRenderer().disposeResource("stars:deep:camera");
    this.pendingDeepTimer = window.setTimeout(() => {
      this.pendingDeepTimer = null;
      if (this.snapshot !== snapshot || snapshot.mode !== "camera") return;
      const equatorial = setThreeFromAzimuthAltitude(this.direction, pose.azimuthDeg, pose.altitudeDeg)
        .applyMatrix3(this.transform.threeToEquatorial).normalize();
      const raDeg = (THREE.MathUtils.radToDeg(Math.atan2(equatorial.y, equatorial.x)) + 360) % 360;
      const decDeg = THREE.MathUtils.radToDeg(Math.asin(THREE.MathUtils.clamp(equatorial.z, -1, 1)));
      const revision = ++this.deepQueryRevision;
      this.deepActive = true;
      this.bridge.requestCameraDepth({
        observationRevision: snapshot.observationRevision,
        deepQueryRevision: revision,
        raDeg, decDeg,
        radiusDeg: (field.diagonalDeg ?? field.widthDeg) * 0.55,
        photometricLimit: limit,
      });
    }, 300);
  }

  private cancelDeepQuery(): void {
    if (!this.deepActive && this.pendingDeepTimer === null) return;
    if (this.pendingDeepTimer !== null) window.clearTimeout(this.pendingDeepTimer);
    this.pendingDeepTimer = null;
    this.lastDeepKey = "";
    const revision = ++this.deepQueryRevision;
    this.deepActive = false;
    this.bridge.cancelCameraDepth(revision);
    this.sceneHost.getStarFieldRenderer().disposeResource("stars:deep:camera");
  }
}
