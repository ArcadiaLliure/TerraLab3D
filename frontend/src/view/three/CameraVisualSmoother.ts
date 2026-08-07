/**
 * CameraVisualSmoother — purely visual smoothing between physical pose
 * and the rendered camera position.
 *
 * This layer absorbs:
 *   - Small vertical terrain jitter (LOD transitions, triangle edges)
 *   - Micro-variations from future DEM data
 *   - Abrupt surface changes between terrain cells
 *
 * This layer does NOT affect:
 *   - Physical pose (always exact grounding)
 *   - Collision detection
 *   - Bounds checking
 *   - Slope/step calculations
 *   - GroundFollower decisions
 *
 * Architecture:
 *   GroundFollower → PhysicalCameraPose → CameraVisualSmoother → CameraRig → Three.js Camera
 */

import type { NavigationCameraPose } from "../../contracts/navigation";

export class CameraVisualSmoother {
  private smoothedUpM: number = 0;
  private initialized = false;

  /**
   * Compute the visual (rendered) pose from the physical pose.
   * The smoothed pose is identical to the physical pose except for
   * a damped vertical component that absorbs small terrain jitter.
   *
   * @param physicalPose  The exact, grounded physical pose from GroundFollower.
   * @param smoothingFactor  0..1. 0 = no smoothing (instant snap), 1 = max smooth.
   *                         Typical value: 0.15
   * @returns  The visual pose to apply to Three.js camera.
   */
  smooth(physicalPose: NavigationCameraPose, smoothingFactor: number): NavigationCameraPose {
    if (!this.initialized) {
      this.smoothedUpM = physicalPose.positionUpM;
      this.initialized = true;
      return physicalPose;
    }

    // Clamp factor to valid range
    const factor = Math.max(0, Math.min(1, smoothingFactor));

    // Lerp vertical position only. Horizontal and orientation are exact.
    const diff = physicalPose.positionUpM - this.smoothedUpM;
    this.smoothedUpM += diff * (1 - factor);

    // Never let visual position diverge too far from physical
    // (prevent floating/sinking artifacts in extreme cases)
    const maxDivergence = 0.5; // metres
    if (Math.abs(this.smoothedUpM - physicalPose.positionUpM) > maxDivergence) {
      this.smoothedUpM = physicalPose.positionUpM + Math.sign(diff) * maxDivergence;
    }

    return {
      ...physicalPose,
      positionUpM: this.smoothedUpM,
    };
  }

  /** Force an immediate snap to the physical pose (e.g. on mode change or reset). */
  reset(upM: number): void {
    this.smoothedUpM = upM;
    this.initialized = true;
  }

  /** Whether the smoother has been initialized with at least one pose. */
  get isInitialized(): boolean {
    return this.initialized;
  }
}
