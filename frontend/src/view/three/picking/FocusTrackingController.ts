import type { CameraRigImpl } from "../CameraRigImpl";
import type { TrackingTargetResolver, ResolvedTrackingDirection } from "./TrackingTargetResolver";
import type { CelestialTargetRef } from "../../../contracts/celestial_selection_contracts";

export type TrackingState = "inactive" | "acquiring" | "tracking";

export class FocusTrackingController {
  private state: TrackingState = "inactive";
  private currentTarget: CelestialTargetRef | null = null;
  
  constructor(
    private readonly cameraRig: CameraRigImpl,
    private readonly resolver: TrackingTargetResolver
  ) {
    this.cameraRig.onUserInteraction(() => {
      console.log("[DEBUG EVENT] FocusTrackingController received onUserInteraction. Current state:", this.state);
      // Cancel·lar el seguiment automàtic si l'usuari interactua (fa pan)
      if (this.state !== "inactive") {
        this.stopTracking();
      }
    });
  }

  public getTrackingState(): TrackingState {
    return this.state;
  }

  public getTrackingTarget(): CelestialTargetRef | null {
    return this.currentTarget;
  }

  public startTracking(target: CelestialTargetRef | null): void {
    if (!target) return;
    
    this.currentTarget = target;
    this.state = "acquiring";
    
    const resolved = this.resolver.resolve(target);
    if (resolved) {
      const pose = this.cameraRig.pose();
      // Animem fins a l'objectiu la primera vegada
      this.cameraRig.animateTo(resolved.azimuthDeg, resolved.altitudeDeg, pose.horizontalFovDeg, 600);
      this.state = "tracking";
      this.cameraRig.setTrackingState(true);
    }
  }

  public stopTracking(): void {
    if (this.state !== "inactive") {
        this.state = "inactive";
        this.currentTarget = null;
        this.cameraRig.setTrackingState(false);
        console.info("MGP: [FocusTrackingController] Tracking aturat");
    }
  }

  /**
   * Called on every frame (from main loop).
   */
  public update(): void {
    if (this.state === "inactive" || !this.currentTarget) return;

    const resolved = this.resolver.resolve(this.currentTarget);
    if (!resolved) {
      return;
    }

    if (this.state === "acquiring") {
       this.state = "tracking";
       this.cameraRig.setTrackingState(true);
       const pose = this.cameraRig.pose();
       this.cameraRig.animateTo(resolved.azimuthDeg, resolved.altitudeDeg, pose.horizontalFovDeg, 600);
       return;
    }

    if (this.cameraRig.isAnimating()) {
       // Si s'està animant cap al target, no forcem la pose encara per permetre la transició suau
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
