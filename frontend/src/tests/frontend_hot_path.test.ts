import { resizeCanvasBackingStore } from "../view/ui/components/TimeBar";
import { computeRenderPixelRatio } from "../view/three/renderResolutionPolicy";
import { CelestialTransformState } from "../view/three/CelestialTransformState";
import { WebSocketBridge, type BridgeState } from "../bridge/WebSocketBridge";

let passed = 0;
let failed = 0;

function assert(condition: boolean, message: string): void {
  if (condition) passed++;
  else {
    failed++;
    console.error(`FAIL: ${message}`);
  }
}

let width = 800;
let height = 48;
let widthWrites = 0;
let heightWrites = 0;
const canvas = {
  get width(): number { return width; },
  set width(value: number) { width = value; widthWrites++; },
  get height(): number { return height; },
  set height(value: number) { height = value; heightWrites++; },
};

assert(!resizeCanvasBackingStore(canvas, 800, 48), "unchanged canvas backing store is retained");
assert(widthWrites === 0 && heightWrites === 0, "unchanged draw performs no canvas dimension writes");
assert(resizeCanvasBackingStore(canvas, 1024, 48), "real width change resizes the backing store");
assert(widthWrites === 1 && heightWrites === 0, "only the changed canvas dimension is assigned");
assert(resizeCanvasBackingStore(canvas, 1024, 64), "real height change resizes the backing store");
assert(widthWrites === 1 && heightWrites === 1, "height resize does not rewrite the stable width");

const screenshotRatio = computeRenderPixelRatio(1.25, 2048, 1050);
assert(screenshotRatio < 1.25, "large high-DPI viewport is reduced below native DPR");
assert(
  2048 * 1050 * screenshotRatio * screenshotRatio <= 2_100_001,
  "large viewport stays inside the WebGL fill-rate budget",
);
assert(
  computeRenderPixelRatio(2, 800, 600) === 2,
  "small high-DPI viewport retains native sharpness",
);

const transform = new CelestialTransformState();
transform.update(1, [1, 0, 0, 0, 1, 0, 0, 0, 1]);
const stableRevision = transform.visualRevision;
assert(!transform.interpolate(performance.now()), "stable celestial transform skips interpolation");
assert(
  transform.visualRevision === stableRevision,
  "stable celestial transform does not invalidate GPU consumers",
);

const quarterTurn = [0, -1, 0, 1, 0, 0, 0, 0, 1];
assert(transform.update(2, quarterTurn, 40), "timeline celestial target is accepted");
assert(
  transform.interpolate(performance.now() + 50),
  "timeline transition reaches a fresh star transform before the next 20 Hz input",
);
assert(
  transform.visualRevision > stableRevision,
  "timeline movement invalidates the shared GPU transform",
);

const bridge = new WebSocketBridge();
let connectedNotifications = 0;
bridge.addStateListener({
  onBridgeStateChanged(state) {
    if (state === "connected") connectedNotifications++;
  },
});
const setBridgeState = (
  bridge as unknown as { setState(state: BridgeState, detail?: string): void }
).setState.bind(bridge);
setBridgeState("connected");
setBridgeState("connected");
assert(
  connectedNotifications === 1,
  "repeated handshake acknowledgements do not repeat connected side effects",
);

console.log(`Frontend hot-path tests: ${passed} passed, ${failed} failed`);
if (failed > 0) throw new Error(`${failed} frontend hot-path test(s) failed`);
