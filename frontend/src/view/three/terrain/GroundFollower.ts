/**
 * GroundFollower — concrete implementation of IGroundFollower.
 *
 * Resolves walk-mode locomotion against the terrain surface.
 * Uses TerrainSampler (interface only — no knowledge of concrete type).
 *
 * Pipeline per call to resolve():
 *   1. Query terrain at proposed E/N position.
 *   2. Validate the sample (null, NaN, degenerate normal → block).
 *   3. Check slope against maximumWalkableSlopeDeg.
 *   4. Check step height against maximumStepHeightM.
 *   5. Project movement onto the tangent plane of the surface.
 *   6. Set physicalUpM = groundHeightM + eyeHeightM (EXACT, no lerp).
 *   7. Return GroundResolution with pose, grounded, blocked status.
 */

import type { NavigationCameraPose, WalkNavigationSettings } from "../../../contracts/navigation";
import type { TerrainSampler } from "../../../contracts/TerrainSampler";
import type { GroundSample } from "../../../contracts/TerrainSampler";
import type { IGroundFollower, GroundResolution } from "../../../contracts/GroundFollower";

const LOG_PREFIX = "MGP: [GroundFollower]";

export class GroundFollower implements IGroundFollower {
  private lastSafeGroundedPose: NavigationCameraPose | null = null;
  private lastLoggedReason: string = "";

  resolve(
    previousPose: NavigationCameraPose,
    proposedPose: NavigationCameraPose,
    terrainSampler: TerrainSampler,
    settings: WalkNavigationSettings,
  ): GroundResolution {
    // ── 1. Query terrain at proposed position ─────────────────────────
    const sample = terrainSampler.sampleGround(
      proposedPose.positionEastM,
      proposedPose.positionNorthM,
      previousPose.positionUpM,
    );

    // ── 2. Validate sample ────────────────────────────────────────────
    if (!this.isValidSample(sample)) {
      this.logOnce("resolve", "Mostra invàlida; es conserva lastSafeGroundedPose");
      return this.fallbackResolution(previousPose, "invalid_sample");
    }

    // sample is guaranteed non-null and valid here
    const ground = sample!;

    // ── 3. Check slope ────────────────────────────────────────────────
    if (ground.slopeDeg > settings.maximumWalkableSlopeDeg) {
      // Only block if trying to move UPHILL on the steep slope
      if (this.isMovingUphill(previousPose, proposedPose, ground)) {
        this.logOnce(
          "resolve",
          `Pendent rebutjada slope_deg=${ground.slopeDeg.toFixed(1)} limit_deg=${settings.maximumWalkableSlopeDeg}`,
        );
        return this.fallbackResolution(previousPose, "slope_exceeded");
      }
    }

    // ── 4. Check step height ──────────────────────────────────────────
    const previousGround = terrainSampler.sampleGround(
      previousPose.positionEastM,
      previousPose.positionNorthM,
      previousPose.positionUpM,
    );
    if (previousGround && previousGround.valid) {
      const dE = proposedPose.positionEastM - previousPose.positionEastM;
      const dN = proposedPose.positionNorthM - previousPose.positionNorthM;
      const dist = Math.sqrt(dE * dE + dN * dN);

      const slopeRad = (ground.slopeDeg * Math.PI) / 180;
      const expectedSlopeRise = dist * Math.sin(slopeRad);
      const heightDelta = Math.abs(ground.heightM - previousGround.heightM);
      const stepDiscontinuity = Math.max(0, heightDelta - expectedSlopeRise);

      if (stepDiscontinuity > settings.maximumStepHeightM) {
        this.logOnce(
          "resolve",
          `Step rebutjat step_m=${stepDiscontinuity.toFixed(2)} limit_m=${settings.maximumStepHeightM}`,
        );
        return this.fallbackResolution(previousPose, "step_exceeded");
      }
    }

    // ── 5. Project movement onto tangent plane ────────────────────────
    const projected = this.projectOnSurface(previousPose, proposedPose, ground);

    // ── 6. Set exact grounded height ──────────────────────────────────
    const groundedPose: NavigationCameraPose = {
      ...projected,
      positionUpM: ground.heightM + settings.eyeHeightM,
      rollDeg: 0, // Walk mode: no roll
    };

    // ── 7. Save as last safe and return ───────────────────────────────
    this.lastSafeGroundedPose = { ...groundedPose };
    this.lastLoggedReason = "";

    return {
      pose: groundedPose,
      grounded: true,
      blocked: false,
    };
  }

  // ─── Private helpers ───────────────────────────────────────────────

  private isValidSample(sample: GroundSample | null): sample is GroundSample {
    if (sample === null) return false;
    if (!sample.valid) return false;
    if (!isFinite(sample.heightM)) return false;
    if (!isFinite(sample.normal.east) || !isFinite(sample.normal.up) || !isFinite(sample.normal.north)) {
      return false;
    }
    // Check for degenerate normal (near-zero length)
    const lenSq =
      sample.normal.east * sample.normal.east +
      sample.normal.up * sample.normal.up +
      sample.normal.north * sample.normal.north;
    if (lenSq < 0.5) return false;
    if (!isFinite(sample.slopeDeg)) return false;
    return true;
  }

  /**
   * Determine if the proposed movement goes uphill on the surface.
   * We consider direction of movement relative to the steepest ascent.
   */
  private isMovingUphill(
    previous: NavigationCameraPose,
    proposed: NavigationCameraPose,
    sample: GroundSample,
  ): boolean {
    // Movement direction in ENU (horizontal)
    const dE = proposed.positionEastM - previous.positionEastM;
    const dN = proposed.positionNorthM - previous.positionNorthM;
    const moveLenSq = dE * dE + dN * dN;
    if (moveLenSq < 1e-10) return false;

    // Steepest ascent direction = horizontal projection of the surface normal
    // (pointing "uphill" = opposite to the horizontal component of the normal when tilted)
    // For an upward-pointing normal on a slope, the horizontal component points uphill.
    const uphillE = sample.normal.east;
    const uphillN = sample.normal.north;

    // Dot product: positive = moving uphill
    const dot = dE * uphillE + dN * uphillN;
    return dot > 0;
  }

  /**
   * Project the horizontal movement vector onto the tangent plane
   * defined by the surface normal. This makes the actor walk ON
   * the surface, not just translate horizontally.
   */
  private projectOnSurface(
    previous: NavigationCameraPose,
    proposed: NavigationCameraPose,
    sample: GroundSample,
  ): NavigationCameraPose {
    // Movement vector (horizontal only from input)
    const dE = proposed.positionEastM - previous.positionEastM;
    const dN = proposed.positionNorthM - previous.positionNorthM;

    // If nearly no movement, skip projection
    const moveLenSq = dE * dE + dN * dN;
    if (moveLenSq < 1e-10) {
      return proposed;
    }

    // Normal vector (ENU)
    const nE = sample.normal.east;
    const nU = sample.normal.up;
    const nN = sample.normal.north;

    // On a flat surface (normal = [0,1,0]), projection is identity.
    // On a slope, we project the movement vector onto the tangent plane.
    //
    // For a 3D movement vector v = (dE, 0, dN) (horizontal input),
    // project onto plane with normal n:
    //   v_projected = v - (v·n / n·n) * n
    //
    // Then we extract just the horizontal components (E, N) since
    // the vertical component is handled by grounding.

    const vDotN = dE * nE + 0 * nU + dN * nN;
    const nDotN = nE * nE + nU * nU + nN * nN;

    if (nDotN < 1e-10) {
      // Degenerate normal — just use proposed as-is
      return proposed;
    }

    const scale = vDotN / nDotN;
    const projE = dE - scale * nE;
    const projN = dN - scale * nN;
    // projU = 0 - scale * nU; (vertical handled by grounding)

    // Preserve original movement magnitude to avoid speed loss on slopes
    const projLenSq = projE * projE + projN * projN;
    const moveLen = Math.sqrt(moveLenSq);
    let finalE: number;
    let finalN: number;

    if (projLenSq > 1e-10) {
      const projLen = Math.sqrt(projLenSq);
      const renormScale = moveLen / projLen;
      finalE = projE * renormScale;
      finalN = projN * renormScale;
    } else {
      // Movement is perpendicular to slope (e.g. walking into a wall) → block
      finalE = 0;
      finalN = 0;
    }

    return {
      ...proposed,
      positionEastM: previous.positionEastM + finalE,
      positionNorthM: previous.positionNorthM + finalN,
    };
  }

  private fallbackResolution(
    safePose: NavigationCameraPose,
    reason: string,
  ): GroundResolution {
    const pose = this.lastSafeGroundedPose ?? safePose;
    return {
      pose: { ...pose },
      grounded: this.lastSafeGroundedPose !== null,
      blocked: true,
      reason,
    };
  }

  /** Log a message only once per unique reason to avoid spam. */
  private logOnce(method: string, message: string): void {
    if (this.lastLoggedReason === message) return;
    this.lastLoggedReason = message;
    console.warn(`${LOG_PREFIX} [${method}] [${message}]`);
  }
}
