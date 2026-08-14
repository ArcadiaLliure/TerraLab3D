/**
 * Grid and overlay tests for Phase 4.
 *
 * Tests:
 *   1. ENU convention verification (N=0°, E=90°, S=180°, W=270°)
 *   2. Azimuth normalisation
 *   3. Degenerate azimuth at zenith/nadir
 *   4. FOV-to-LOD mapping with hysteresis
 *   5. Label priority ordering
 *   6. Grid geometry build count stability
 *   7. View azimuth computation
 *   8. Cardinal direction mapping
 */

import * as THREE from "three";
import { HorizontalGrid } from "../view/three/HorizontalGrid";

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

// ─── Test Helpers ────────────────────────────────────────────────────

const DEG = Math.PI / 180;

/**
 * Convert (azDeg, altDeg) to Three.js world position on a unit sphere.
 * This mirrors the convention used in HorizontalGrid and CelestialLabels.
 */
function azAltToWorld(azDeg: number, altDeg: number): [number, number, number] {
  const azRad = azDeg * DEG;
  const altRad = altDeg * DEG;
  const cosAlt = Math.cos(altRad);
  const sinAlt = Math.sin(altRad);

  const x = Math.sin(azRad) * cosAlt;       // East
  const y = sinAlt;                           // Up
  const z = -Math.cos(azRad) * cosAlt;       // -North (Three.js Z)
  return [x, y, z];
}

/** Normalise azimuth to [0, 360). */
function normalizeAzimuth(deg: number): number {
  return ((deg % 360) + 360) % 360;
}

/** Compute view azimuth, returning null for degenerate cases. */
function computeViewAzimuth(azDeg: number, altDeg: number): number | null {
  const cosAlt = Math.cos(altDeg * DEG);
  if (Math.abs(cosAlt) < 0.01) return null;
  return normalizeAzimuth(azDeg);
}

/** Map azimuth to cardinal direction. */
function azimuthToCardinal(azDeg: number): string {
  const az = normalizeAzimuth(azDeg);
  if (az >= 337.5 || az < 22.5) return "N";
  if (az >= 22.5 && az < 67.5) return "NE";
  if (az >= 67.5 && az < 112.5) return "E";
  if (az >= 112.5 && az < 157.5) return "SE";
  if (az >= 157.5 && az < 202.5) return "S";
  if (az >= 202.5 && az < 247.5) return "SO";
  if (az >= 247.5 && az < 292.5) return "O";
  return "NO";
}

// ─── FOV-to-LOD logic (mirror of HorizontalGrid) ────────────────────

type GridLODLevel = "coarse" | "medium" | "fine";

const LOD_FINE_ENTER = 30;
const LOD_FINE_EXIT = 35;
const LOD_COARSE_ENTER = 80;
const LOD_COARSE_EXIT = 75;

function computeLOD(fov: number, current: GridLODLevel): GridLODLevel {
  if (current === "medium") {
    if (fov < LOD_FINE_ENTER) return "fine";
    if (fov > LOD_COARSE_ENTER) return "coarse";
    return "medium";
  } else if (current === "fine") {
    if (fov > LOD_FINE_EXIT) return "medium";
    return "fine";
  } else { // coarse
    if (fov < LOD_COARSE_EXIT) return "medium";
    return "coarse";
  }
}

// ─── TEST SUITE ──────────────────────────────────────────────────────

function runTests() {
  console.log("=== TerraLab3D Phase 4 Grid & Overlay Tests ===\n");

  // ── 1. ENU Convention ──────────────────────────────────────────────
  console.log("1. ENU Convention — Cardinal Directions");
  {
    // North = azimuth 0° → points towards -Z in Three.js
    const [nx, ny, nz] = azAltToWorld(0, 0);
    assertNear(nx, 0, 0.001, "North X = 0");
    assertNear(ny, 0, 0.001, "North Y = 0");
    assertNear(nz, -1, 0.001, "North Z = -1 (Three.js -Z)");

    // East = azimuth 90° → points towards +X
    const [ex, ey, ez] = azAltToWorld(90, 0);
    assertNear(ex, 1, 0.001, "East X = +1");
    assertNear(ey, 0, 0.001, "East Y = 0");
    assertNear(ez, 0, 0.001, "East Z = 0");

    // South = azimuth 180° → points towards +Z
    const [sx, sy, sz] = azAltToWorld(180, 0);
    assertNear(sx, 0, 0.001, "South X = 0");
    assertNear(sy, 0, 0.001, "South Y = 0");
    assertNear(sz, 1, 0.001, "South Z = +1");

    // West = azimuth 270° → points towards -X
    const [wx, wy, wz] = azAltToWorld(270, 0);
    assertNear(wx, -1, 0.001, "West X = -1");
    assertNear(wy, 0, 0.001, "West Y = 0");
    assertNear(wz, 0, 0.001, "West Z = 0");
  }

  // ── 2. Zenith and Horizon ──────────────────────────────────────────
  console.log("\n2. Zenith and Horizon");
  {
    // Zenith = altitude +90° → Y = +1
    const [zx, zy, zz] = azAltToWorld(0, 90);
    assertNear(zx, 0, 0.001, "Zenith X = 0");
    assertNear(zy, 1, 0.001, "Zenith Y = +1 (up)");
    assertNear(zz, 0, 0.001, "Zenith Z = 0");

    // Horizon = altitude 0° → Y = 0
    const [hx, hy, hz] = azAltToWorld(45, 0);
    assertNear(hy, 0, 0.001, "Horizon Y = 0");

    // Nadir = altitude -90° → Y = -1
    const [ndx, ndy, ndz] = azAltToWorld(0, -90);
    assertNear(ndx, 0, 0.001, "Nadir X = 0");
    assertNear(ndy, -1, 0.001, "Nadir Y = -1 (down)");
    assertNear(ndz, 0, 0.001, "Nadir Z = 0");
  }

  // ── 3. Azimuth Normalisation ───────────────────────────────────────
  console.log("\n3. Azimuth Normalisation");
  {
    assertNear(normalizeAzimuth(0), 0, 0.001, "0° → 0°");
    assertNear(normalizeAzimuth(360), 0, 0.001, "360° → 0°");
    assertNear(normalizeAzimuth(720), 0, 0.001, "720° → 0°");
    assertNear(normalizeAzimuth(-90), 270, 0.001, "-90° → 270°");
    assertNear(normalizeAzimuth(-360), 0, 0.001, "-360° → 0°");
    assertNear(normalizeAzimuth(45), 45, 0.001, "45° → 45°");
    assertNear(normalizeAzimuth(359.9), 359.9, 0.01, "359.9° → 359.9°");
  }

  // ── 4. Degenerate Azimuth at Zenith/Nadir ──────────────────────────
  console.log("\n4. Degenerate Azimuth at Zenith/Nadir");
  {
    assert(computeViewAzimuth(45, 90) === null, "Azimuth at zenith (alt=90°) is null");
    assert(computeViewAzimuth(45, -90) === null, "Azimuth at nadir (alt=-90°) is null");
    assert(computeViewAzimuth(45, 89.5) === null, "Azimuth near zenith (alt=89.5°) is null");
    assert(computeViewAzimuth(45, -89.5) === null, "Azimuth near nadir (alt=-89.5°) is null");
    assert(computeViewAzimuth(45, 85) !== null, "Azimuth at alt=85° is NOT null");
    assert(computeViewAzimuth(45, 0) !== null, "Azimuth at horizon is NOT null");

    // When not degenerate, azimuth should be the normalised input
    const az = computeViewAzimuth(45, 20);
    assert(az !== null, "Azimuth at alt=20° is NOT null");
    assertNear(az!, 45, 0.001, "Azimuth at alt=20° equals 45°");
  }

  // ── 5. No NaN / Infinity ──────────────────────────────────────────
  console.log("\n5. No NaN / Infinity in conversions");
  {
    const testCases: Array<[number, number]> = [
      [0, 0], [0, 90], [0, -90], [180, 45],
      [359.999, 0], [0.001, 89.999], [270, -89.999],
    ];
    for (const [az, alt] of testCases) {
      const [x, y, z] = azAltToWorld(az, alt);
      assert(!isNaN(x) && !isNaN(y) && !isNaN(z), `No NaN for (az=${az}, alt=${alt})`);
      assert(isFinite(x) && isFinite(y) && isFinite(z), `No Infinity for (az=${az}, alt=${alt})`);
    }
  }

  // ── 6. FOV-to-LOD Mapping ──────────────────────────────────────────
  console.log("\n6. FOV-to-LOD Mapping with Hysteresis");
  {
    // Start at medium
    let lod: GridLODLevel = "medium";
    lod = computeLOD(60, lod);
    assert(lod === "medium", "FOV=60 stays medium");

    lod = computeLOD(25, lod);
    assert(lod === "fine", "FOV=25 → fine");

    // Hysteresis: going back to 32° should stay fine (exit threshold = 35)
    lod = computeLOD(32, lod);
    assert(lod === "fine", "FOV=32 stays fine (hysteresis, exit=35)");

    lod = computeLOD(36, lod);
    assert(lod === "medium", "FOV=36 → medium (above exit=35)");

    lod = computeLOD(85, lod);
    assert(lod === "coarse", "FOV=85 → coarse");

    // Hysteresis: going back to 77° should stay coarse (exit threshold = 75)
    lod = computeLOD(77, lod);
    assert(lod === "coarse", "FOV=77 stays coarse (hysteresis, exit=75)");

    lod = computeLOD(74, lod);
    assert(lod === "medium", "FOV=74 → medium (below exit=75)");
  }

  // ── 7. Cardinal Direction Mapping ──────────────────────────────────
  console.log("\n7. Cardinal Direction Mapping");
  {
    assert(azimuthToCardinal(0) === "N", "0° = N");
    assert(azimuthToCardinal(45) === "NE", "45° = NE");
    assert(azimuthToCardinal(90) === "E", "90° = E");
    assert(azimuthToCardinal(135) === "SE", "135° = SE");
    assert(azimuthToCardinal(180) === "S", "180° = S");
    assert(azimuthToCardinal(225) === "SO", "225° = SO");
    assert(azimuthToCardinal(270) === "O", "270° = O");
    assert(azimuthToCardinal(315) === "NO", "315° = NO");
    assert(azimuthToCardinal(359) === "N", "359° = N");
    assert(azimuthToCardinal(22) === "N", "22° = N (boundary)");
    assert(azimuthToCardinal(23) === "NE", "23° = NE (boundary)");
  }

  // ── 8. Grid Geometry Build Count Stability ─────────────────────────
  console.log("\n8. Grid Build Count Stability Concept");
  {
    // Verify that the LOD logic doesn't flip-flop at boundaries
    let lod: GridLODLevel = "medium";
    let switchCount = 0;

    // Simulate FOV oscillating around the fine threshold
    const fovSequence = [31, 29, 31, 33, 31, 29, 34, 36]; // crosses 30/35
    for (const fov of fovSequence) {
      const newLod = computeLOD(fov, lod);
      if (newLod !== lod) switchCount++;
      lod = newLod;
    }

    // With hysteresis, this should only switch twice:
    // medium→fine (at 29) and fine→medium (at 36)
    assert(switchCount === 2, `LOD switches with hysteresis = ${switchCount} (expected 2)`);
  }

  // ── 9. Altitude Circle Position ────────────────────────────────────
  console.log("\n9. Altitude Circle Position Correctness");
  {
    // At alt=30°, the circle radius should be cos(30°) and Y should be sin(30°)
    const alt30 = 30;
    const [x, y, z] = azAltToWorld(0, alt30);
    const expectedY = Math.sin(alt30 * DEG);
    const expectedR = Math.cos(alt30 * DEG);
    assertNear(y, expectedY, 0.001, `Alt 30° Y = sin(30°) = ${expectedY.toFixed(4)}`);
    assertNear(Math.sqrt(x * x + z * z), expectedR, 0.001, `Alt 30° horizontal radius = cos(30°) = ${expectedR.toFixed(4)}`);
  }

  // ── 10. Grid Composition Order ─────────────────────────────────────
  console.log("\n10. Grid Composition Behind Celestial Content");
  {
    const grid = new HorizontalGrid();
    let lineCount = 0;
    let allLinesAvoidDepthWrites = true;
    let allLinesRenderBehindStars = true;

    grid.root.traverse((object) => {
      if (!(object instanceof THREE.Line)) return;
      lineCount++;
      const materials = Array.isArray(object.material) ? object.material : [object.material];
      allLinesAvoidDepthWrites &&= materials.every((material) => !material.depthWrite);
      allLinesRenderBehindStars &&= object.renderOrder < 0;
    });

    assert(lineCount > 0, "horizontal grid exposes persistent line primitives");
    assert(allLinesAvoidDepthWrites, "grid lines do not occlude stars or trails in the depth buffer");
    assert(allLinesRenderBehindStars, "grid lines render before stellar content");
    grid.dispose();
  }

  // ── Summary ────────────────────────────────────────────────────────
  console.log(`\n=== Test Results: ${passed} passed, ${failed} failed ===`);
  if (failed > 0) {
    (globalThis as any).process?.exit?.(1);
  }
}

runTests();
