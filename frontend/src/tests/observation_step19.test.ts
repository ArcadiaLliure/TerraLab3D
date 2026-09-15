import * as THREE from "three";
import { cameraOverlayHalfSize } from "../view/three/layers/ImagingPreviewLayerRenderer";
import { telescopeOverlayRadiusY } from "../view/three/layers/ScopeLayerRenderer";
import { StarTrailLayerRendererImpl } from "../view/three/layers/StarTrailLayerRendererImpl";
import { cameraDeepQueryKey } from "../application/ObservationModeController";

let failures = 0;
function assert(condition: boolean, message: string): void {
  if (!condition) { failures++; console.error(`FAIL: ${message}`); }
}
function near(a: number, b: number, epsilon = 1e-10): boolean { return Math.abs(a - b) <= epsilon; }

const aspect = 16 / 9;
const [x, y] = cameraOverlayHalfSize(10, 6, 60, aspect);
const visualH = THREE.MathUtils.degToRad(60);
const visualV = 2 * Math.atan(Math.tan(visualH / 2) / aspect);
assert(near(x, Math.tan(THREE.MathUtils.degToRad(5)) / Math.tan(visualH / 2)), "camera X uses tangent ratio");
assert(near(y, Math.tan(THREE.MathUtils.degToRad(3)) / Math.tan(visualV / 2)), "camera Y uses tangent ratio");

const radiusY = telescopeOverlayRadiusY(2.5, 60, aspect);
const width = 1600; const height = 900;
const verticalRadiusPx = radiusY * height / 2;
const horizontalRadiusPx = (radiusY / aspect) * width / 2;
assert(near(verticalRadiusPx, horizontalRadiusPx), "telescope mask is circular in pixel space");
assert(cameraOverlayHalfSize(100, 80, 30, aspect)[0] > 1, "larger instrumental fields clip without changing visual FOV");

const scientificKey = cameraDeepQueryKey(180, 30, 4.5, 12.25);
assert(scientificKey === cameraDeepQueryKey(180, 30, 4.5, 12.25), "visual zoom, viewport, DPR and transform ticks are absent from the Gaia key");
assert(scientificKey !== cameraDeepQueryKey(180.01, 30, 4.5, 12.25), "scientific pointing invalidates Gaia");
assert(scientificKey !== cameraDeepQueryKey(180, 30, 5.0, 12.25), "instrumental field invalidates Gaia");
assert(scientificKey !== cameraDeepQueryKey(180, 30, 4.5, 13.0), "photometric depth invalidates Gaia");

const root = new THREE.Group();
const fakeCatalog = {
  getResources: () => new Map(),
  setTrailSuppressed: (_suppressed: boolean) => undefined,
};
const fakeViewport = {
  getDrawingBufferSize: (target: THREE.Vector2) => target.set(1600, 900),
  getPixelRatio: () => 1,
};
const trails = new StarTrailLayerRendererImpl(root, fakeCatalog, new THREE.PerspectiveCamera(), fakeViewport);
trails.setCameraPreview(true, 2, 12);
assert(trails.getMetrics().state === "camera_preview", "camera preview owns trails without explicit session");
trails.applySnapshot({ sessionId: "explicit", sessionVersion: 1, state: "running", playbackRate: 1, magnitudeLimit: 6, durationSeconds: 60 });
assert(trails.getMetrics().state === "running", "explicit session has precedence");
trails.applySnapshot({ sessionId: "", sessionVersion: 2, state: "idle", playbackRate: 1, magnitudeLimit: 6 });
assert(trails.getMetrics().state === "camera_preview", "camera preview returns after explicit session");
trails.dispose();

if (failures > 0) throw new Error(`${failures} observation tests failed`);
console.log("Paso 19 observation tests passed");
