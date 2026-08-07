/**
 * GroundFollower — physical grounding contract for walk mode.
 *
 * Responsible for deciding how a walking actor remains physically bound
 * to the terrain surface. This class does NOT know where the terrain
 * data comes from (raycaster, DEM, heightfield, etc.).
 *
 * Responsibilities:
 *   - Validate the terrain sample.
 *   - Project the proposed horizontal movement onto the tangent plane
 *     defined by the surface normal.
 *   - Enforce maximum walkable slope.
 *   - Enforce maximum step height.
 *   - Set physical height to exactly groundHeightM + eyeHeightM.
 *   - Return lastSafeGroundedPose when the sample is invalid.
 *
 * NOT responsible for:
 *   - Querying terrain (uses TerrainSampler passed as argument).
 *   - Visual smoothing (that is CameraVisualSmoother).
 *   - Flight mode (that is FlightController).
 *   - Input handling.
 */

import type { NavigationCameraPose, WalkNavigationSettings } from "./navigation";
import type { TerrainSampler } from "./TerrainSampler";

// ─── Ground Resolution ──────────────────────────────────────────────

/** Result of resolving a proposed walk movement against terrain. */
export interface GroundResolution {
  /** The resolved physical pose — grounded to the surface. */
  pose: NavigationCameraPose;
  /** Whether the actor is properly grounded on a valid surface. */
  grounded: boolean;
  /** Whether the proposed movement was rejected (slope/step/invalid). */
  blocked: boolean;
  /** Human-readable reason if blocked. */
  reason?: string;
}

// ─── GroundFollower Interface ────────────────────────────────────────

export interface IGroundFollower {
  /**
   * Resolve a proposed walk movement against terrain.
   *
   * @param previousPose     The current (valid, grounded) physical pose.
   * @param proposedPose     The new pose after applying input-driven movement
   *                         (E/N displacement from WASD, same altitude).
   * @param terrainSampler   The terrain query interface (never concrete).
   * @param settings         Walk navigation configuration.
   * @returns  Resolved pose, grounding status, and block reason if applicable.
   */
  resolve(
    previousPose: NavigationCameraPose,
    proposedPose: NavigationCameraPose,
    terrainSampler: TerrainSampler,
    settings: WalkNavigationSettings,
  ): GroundResolution;
}
