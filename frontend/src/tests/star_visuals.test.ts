import {
  computeStarFovScale,
  computeStarPointSizeDevicePx,
} from "../view/three/shaders/starVisualParams";

let passed = 0;
let failed = 0;

function assert(condition: boolean, message: string): void {
  if (condition) passed++;
  else {
    failed++;
    console.error(`FAIL: ${message}`);
  }
}

function approximately(actual: number, expected: number, tolerance: number): boolean {
  return Math.abs(actual - expected) <= tolerance;
}

const referenceScale = computeStarFovScale(45.0);
const wideScale = computeStarFovScale(120.0);
const telescopeScale = computeStarFovScale(13.2);

assert(approximately(referenceScale, 1.0, 1e-12), "45° is the neutral star-size FOV");
assert(wideScale < referenceScale, "wide FOV reduces stellar point diameter");
assert(telescopeScale > referenceScale, "narrow FOV increases stellar point diameter");
assert(
  computeStarFovScale(0.0001) === 2.5,
  "extreme telescope FOV is capped",
);
assert(
  computeStarFovScale(179.0) === 0.45,
  "extreme wide FOV keeps a visible lower bound",
);

const magnitude = 2.0;
const widePointPx = computeStarPointSizeDevicePx(magnitude, wideScale, 1.0);
const referencePointPx = computeStarPointSizeDevicePx(magnitude, referenceScale, 1.0);
const telescopePointPx = computeStarPointSizeDevicePx(magnitude, telescopeScale, 1.0);

assert(
  widePointPx < referencePointPx && referencePointPx < telescopePointPx,
  "rendered point size follows the FOV scale",
);
assert(
  approximately(
    computeStarPointSizeDevicePx(magnitude, referenceScale, 2.0),
    referencePointPx * 2.0,
    1e-12,
  ),
  "device-pixel ratio remains independent from FOV adaptation",
);

console.log(`Star visual tests: ${passed} passed, ${failed} failed`);
if (failed > 0) throw new Error(`${failed} star visual test(s) failed`);
