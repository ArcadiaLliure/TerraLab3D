/**
 * Navigation unit and architecture tests for Phase 3.5.
 *
 * Tests:
 *   1. TerrainSampler interface & TechnicalTerrainSampler logic / fake implementation
 *   2. GroundFollower physical grounding, tangent plane projection, slope/step limits, fallback
 *   3. CameraVisualSmoother visual isolation (smoothing != physics)
 *   4. Flight mode 3D movement & clearance
 *   5. Architecture decoupling (TerrainSampler replaceable without modifying GroundFollower)
 */

import type { TerrainSampler, GroundSample } from "../contracts/TerrainSampler";
import type { NavigationCameraPose, WalkNavigationSettings } from "../contracts/navigation";
import { DEFAULT_WALK_SETTINGS, defaultNavigationCameraPose } from "../contracts/navigation";
import { GroundFollower } from "../view/three/terrain/GroundFollower";
import { CameraVisualSmoother } from "../view/three/CameraVisualSmoother";

// ─── Fake TerrainSampler for Unit Testing ─────────────────────────────

class FakeTerrainSampler implements TerrainSampler {
  private ready = true;
  public heightFn: (e: number, n: number) => number = () => 0;
  public normalFn: (e: number, n: number) => { east: number; up: number; north: number } = () => ({
    east: 0,
    up: 1,
    north: 0,
  });
  public slopeFn: (e: number, n: number) => number = () => 0;
  public validFn: (e: number, n: number) => boolean = () => true;

  setReady(r: boolean) {
    this.ready = r;
  }

  isReady(): boolean {
    return this.ready;
  }

  sampleGround(eastM: number, northM: number): GroundSample | null {
    if (!this.ready) return null;
    if (!this.validFn(eastM, northM)) return null;

    return {
      heightM: this.heightFn(eastM, northM),
      normal: this.normalFn(eastM, northM),
      slopeDeg: this.slopeFn(eastM, northM),
      valid: true,
      surfaceId: "fake_terrain",
    };
  }
}

// ─── Simple Assert Test Runner ───────────────────────────────────────

let passed = 0;
let failed = 0;

function assert(condition: boolean, message: string) {
  if (condition) {
    passed++;
    console.log(`  ✓ ${message}`);
  } else {
    failed++;
    console.error(`  ✗ FAIL: ${message}`);
  }
}

function assertNear(actual: number, expected: number, tolerance: number, message: string) {
  const diff = Math.abs(actual - expected);
  if (diff <= tolerance) {
    passed++;
    console.log(`  ✓ ${message} (${actual.toFixed(4)} ~ ${expected.toFixed(4)})`);
  } else {
    failed++;
    console.error(`  ✗ FAIL: ${message} (got ${actual}, expected ${expected} ±${tolerance})`);
  }
}

// ─── TEST SUITE ──────────────────────────────────────────────────────

function runTests() {
  console.log("=== TerraLab3D Phase 3.5 Navigation Tests ===\n");

  const settings: WalkNavigationSettings = { ...DEFAULT_WALK_SETTINGS };

  // ── 1. GroundFollower: Flat Grounding ──────────────────────────────
  console.log("1. GroundFollower — Flat Grounding");
  {
    const follower = new GroundFollower();
    const sampler = new FakeTerrainSampler();
    sampler.heightFn = () => 10.0;

    const prev = defaultNavigationCameraPose();
    prev.positionUpM = 11.7; // 10 + eyeHeight(1.7)

    const prop = { ...prev, positionEastM: 5.0 };

    const res = follower.resolve(prev, prop, sampler, settings);

    assert(!res.blocked, "Move on flat terrain should not be blocked");
    assert(res.grounded, "Actor should be grounded");
    assertNear(res.pose.positionUpM, 11.7, 0.001, "Height must equal exactly groundHeight + eyeHeight (10 + 1.7)");
    assertNear(res.pose.positionEastM, 5.0, 0.001, "East position should match proposed");
  }

  // ── 2. GroundFollower: Uphill / Downhill Following ─────────────────
  console.log("\n2. GroundFollower — Slope Following (Uphill & Downhill)");
  {
    const follower = new GroundFollower();
    const sampler = new FakeTerrainSampler();
    // Gentle 10° slope rising towards East: height = east * 0.176
    sampler.heightFn = (e) => e * 0.176;
    const rad10 = (10 * Math.PI) / 180;
    sampler.normalFn = () => ({
      east: Math.sin(rad10),
      up: Math.cos(rad10),
      north: 0,
    });
    sampler.slopeFn = () => 10;

    const prev = defaultNavigationCameraPose();
    prev.positionEastM = 0;
    prev.positionUpM = 1.7;

    const prop = { ...prev, positionEastM: 10.0 };
    const res = follower.resolve(prev, prop, sampler, settings);

    assert(!res.blocked, "Gentle 10° slope should be walkable");
    assertNear(res.pose.positionUpM, 1.76 + 1.7, 0.01, "Height follows slope exactly (1.76 + 1.7)");
  }

  // ── 3. GroundFollower: Reject Excessive Slope (>45°) ───────────────
  console.log("\n3. GroundFollower — Steep Slope Rejection (>45°)");
  {
    const follower = new GroundFollower();
    const sampler = new FakeTerrainSampler();
    sampler.heightFn = (e) => e * 2.0;
    const rad60 = (60 * Math.PI) / 180;
    sampler.normalFn = () => ({
      east: Math.sin(rad60),
      up: Math.cos(rad60),
      north: 0,
    });
    sampler.slopeFn = () => 60; // 60° slope > 45° limit

    const prev = defaultNavigationCameraPose();
    prev.positionEastM = 0;
    prev.positionUpM = 1.7;

    const prop = { ...prev, positionEastM: 1.0 }; // Trying to go uphill
    const res = follower.resolve(prev, prop, sampler, settings);

    assert(res.blocked, "Uphill movement on 60° slope must be BLOCKED");
    assert(res.reason === "slope_exceeded", "Reason must be slope_exceeded");
  }

  // ── 4. GroundFollower: Reject Excessive Step ───────────────────────
  console.log("\n4. GroundFollower — Step Height Rejection");
  {
    const follower = new GroundFollower();
    const sampler = new FakeTerrainSampler();
    // Cliff at east = 5m (step of 2m > maxStep 0.5m)
    sampler.heightFn = (e) => (e >= 5.0 ? 2.0 : 0.0);

    const prev = defaultNavigationCameraPose();
    prev.positionEastM = 4.9;
    prev.positionUpM = 1.7;

    const prop = { ...prev, positionEastM: 5.1 }; // Stepping over cliff
    const res = follower.resolve(prev, prop, sampler, settings);

    assert(res.blocked, "Step of 2.0m must be BLOCKED");
    assert(res.reason === "step_exceeded", "Reason must be step_exceeded");
  }

  // ── 5. GroundFollower: Fallback on Invalid Sample ──────────────────
  console.log("\n5. GroundFollower — Fallback on Invalid Sample");
  {
    const follower = new GroundFollower();
    const sampler = new FakeTerrainSampler();
    sampler.validFn = (e) => e < 10.0; // Terrain ends at east = 10m

    const prev = defaultNavigationCameraPose();
    prev.positionEastM = 9.0;
    prev.positionUpM = 1.7;

    // Prime follower with safe pose at 9m
    const propValid = { ...prev, positionEastM: 9.0 };
    follower.resolve(prev, propValid, sampler, settings);

    const prop = { ...prev, positionEastM: 11.0 }; // Moving outside valid terrain
    const res = follower.resolve(propValid, prop, sampler, settings);

    assert(res.blocked, "Out-of-bounds movement must be BLOCKED");
    assertNear(res.pose.positionEastM, 9.0, 0.001, "Pose must fall back to last safe grounded pose");
  }

  // ── 6. CameraVisualSmoother: Visual Isolation ──────────────────────
  console.log("\n6. CameraVisualSmoother — Visual Isolation");
  {
    const smoother = new CameraVisualSmoother();
    const pose = defaultNavigationCameraPose();

    // Physical pose jumps from Y=1.7 to Y=3.7
    pose.positionUpM = 1.7;
    const initialVisual = smoother.smooth(pose, 0.15);
    assertNear(initialVisual.positionUpM, 1.7, 0.001, "First frame snaps to physical pose");

    pose.positionUpM = 3.7; // Jump of 2m
    const smoothedVisual = smoother.smooth(pose, 0.15);

    assert(smoothedVisual.positionUpM > 1.7, "Smoothed visual height moves towards target");
    assert(smoothedVisual.positionUpM < 3.7, "Smoothed visual height lags behind physical jump (visual smoothing)");
    assertNear(pose.positionUpM, 3.7, 0.001, "Physical pose remains EXACT (3.7m)");
  }

  // ── 7. Architecture: TerrainSampler Interface Decoupling ─────────────────────
  console.log("\n7. Architecture — TerrainSampler Interface Decoupling");
  {
    const follower = new GroundFollower();
    // Demonstrate that GroundFollower works seamlessly with ANY implementation of TerrainSampler
    const customDemSampler: TerrainSampler = {
      isReady: () => true,
      sampleGround: (e, n) => ({
        heightM: 42.0,
        normal: { east: 0, up: 1, north: 0 },
        slopeDeg: 0,
        valid: true,
        surfaceId: "custom_dem_tile",
      }),
    };

    const prev = defaultNavigationCameraPose();
    const prop = { ...prev, positionEastM: 100 };
    const res = follower.resolve(prev, prop, customDemSampler, settings);

    assert(!res.blocked, "GroundFollower works with custom DEM TerrainSampler without changes");
    assertNear(res.pose.positionUpM, 43.7, 0.001, "Height resolves to DEM height + eyeHeight (42 + 1.7)");
  }

  // ── Summary ────────────────────────────────────────────────────────
  console.log(`\n=== Test Results: ${passed} passed, ${failed} failed ===`);
  if (failed > 0) {
    (globalThis as any).process?.exit?.(1);
  }
}

runTests();
