import type { CameraRigImpl } from "../CameraRigImpl";
import type { TrackingTargetResolver, TrackingTarget, ResolvedTrackingDirection } from "./TrackingTargetResolver";

export type TrackingState = "inactive" | "acquiring" | "tracking";

export class FocusTrackingController {
  private state: TrackingState = "inactive";
  private currentTarget: TrackingTarget | null = null;
  
  constructor(
    private readonly cameraRig: CameraRigImpl,
    private readonly resolver: TrackingTargetResolver
  ) {
    this.cameraRig.onUserInteraction(() => {
      // Cancel·lar el seguiment automàtic si l'usuari interactua (fa pan)
      if (this.state !== "inactive") {
        this.stopTracking();
      }
    });
  }

  public getTrackingState(): TrackingState {
    return this.state;
  }

  public getTrackingTarget(): TrackingTarget | null {
    return this.currentTarget;
  }

  public startTracking(target: TrackingTarget): void {
    if (!target) return;
    
    this.currentTarget = target;
    this.state = "acquiring";
    
    const resolved = this.resolver.resolve(target);
    if (resolved) {
      const pose = this.cameraRig.pose();
      this.cameraRig.setPose({
        ...pose,
        azimuthDeg: resolved.azimuthDeg,
        altitudeDeg: resolved.altitudeDeg,
      });
      this.state = "tracking";
    }
  }

  public stopTracking(): void {
    if (this.state !== "inactive") {
        this.state = "inactive";
        this.currentTarget = null;
        console.info("MGP: [FocusTrackingController] Tracking aturat");
    }
  }

  /**
   * Called on every frame (from main loop).
   */
  public update(): void {
    if (this.state !== "tracking" || !this.currentTarget) {
      return;
    }

    const resolved = this.resolver.resolve(this.currentTarget);
    if (!resolved) {
      return;
    }

    const pose = this.cameraRig.pose();
    // Força az/alt per seguir l'objectiu continuament
    this.cameraRig.setPose({
      ...pose,
      azimuthDeg: resolved.azimuthDeg,
      altitudeDeg: resolved.altitudeDeg,
    });
  }
}
