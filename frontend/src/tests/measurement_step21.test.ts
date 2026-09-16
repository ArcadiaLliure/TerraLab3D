import * as THREE from "three";
import { angularDistanceDeg, previewGeometry, rotateCoordinatePair } from "../application/measurementGeometry";
import type { MeasurementDocumentSnapshot, MeasurementKind, MeasurementSnapshot } from "../contracts/measurement_contracts";
import { MeasurementLayerRendererImpl, setMeasurementPresentationQuaternion } from "../view/three/layers/MeasurementLayerRenderer";

let failures = 0;
function assert(condition: boolean, message: string): void {
  if (!condition) { failures++; console.error(`FAIL: ${message}`); }
}
function near(actual: number, expected: number, epsilon = 1e-7): boolean { return Math.abs(actual - expected) <= epsilon; }

assert(near(angularDistanceDeg({ altitudeDeg: 0, azimuthDeg: 359.9 }, { altitudeDeg: 0, azimuthDeg: 0.1 }), 0.2), "distance crosses the 0/360 seam");
assert(near(angularDistanceDeg({ altitudeDeg: 89.9, azimuthDeg: 0 }, { altitudeDeg: 89.9, azimuthDeg: 180 }), 0.2), "distance remains stable near zenith");
assert(near(angularDistanceDeg({ altitudeDeg: 0, azimuthDeg: 0 }, { altitudeDeg: 0, azimuthDeg: 180 }), 180), "antipodal distance remains stable");
assert(previewGeometry("circle", { altitudeDeg: 10, azimuthDeg: 20 }, { altitudeDeg: 10, azimuthDeg: 20 }) === null, "zero-radius preview is rejected");

for (const kind of ["ruler", "square", "rectangle", "circle"] as MeasurementKind[]) {
  const geometry = previewGeometry(kind, { altitudeDeg: 15, azimuthDeg: 30 }, { altitudeDeg: 19, azimuthDeg: 36 });
  assert(geometry !== null && geometry.paths[0]!.length >= 49 && geometry.label.length > 0, `${kind} has spherical preview and label`);
  if (kind !== "ruler") assert(geometry!.paths[0]![0]!.azimuthDeg === geometry!.paths[0]!.at(-1)!.azimuthDeg, `${kind} path closes`);
}

const initialStart = { altitudeDeg: 10, azimuthDeg: 359 };
const initialEnd = { altitudeDeg: 18, azimuthDeg: 7 };
const initialExtent = angularDistanceDeg(initialStart, initialEnd);
const [movedStart, movedEnd] = rotateCoordinatePair(initialStart, initialEnd, { altitudeDeg: 20, azimuthDeg: 25 }, { altitudeDeg: 22, azimuthDeg: 31 });
assert(near(angularDistanceDeg(movedStart, movedEnd), initialExtent), "moving a shape rigidly preserves its angular extent");

class FakeLabel {
  className = ""; textContent = ""; hidden = false; style = { transform: "" }; dataset: Record<string, string> = {}; removed = false;
  remove(): void { this.removed = true; }
}
const previousDocument = globalThis.document;
const fakeLabels: FakeLabel[] = [];
Object.defineProperty(globalThis, "document", { configurable: true, value: { createElement: () => { const label = new FakeLabel(); fakeLabels.push(label); return label; } } });

function entity(id: string, version: number, endAzimuth: number): MeasurementSnapshot {
  const start = { altitudeDeg: 10, azimuthDeg: 20 };
  const end = { altitudeDeg: 14, azimuthDeg: endAzimuth };
  return { measurementId: id, kind: "ruler", start, end, rotationDeg: 0, tracking: true, fixedQuaternion: null, entityVersion: version, geometry: previewGeometry("ruler", start, end)! };
}
function snapshot(revision: number, measurements: readonly MeasurementSnapshot[], selected: string | null = null): MeasurementDocumentSnapshot {
  return { type: "measurement_snapshot", schemaVersion: 1, measurementRevision: revision, trackingEnabled: true, measurements, selectedMeasurementId: selected, canUndo: revision > 0, canRedo: false, warning: null };
}

const movingSky = new THREE.Quaternion().setFromAxisAngle(new THREE.Vector3(0, 1, 0), Math.PI / 3);
const frozen = new THREE.Quaternion().setFromAxisAngle(new THREE.Vector3(1, 0, 0), Math.PI / 5);
const resolved = new THREE.Quaternion();
setMeasurementPresentationQuaternion({ tracking: false, fixedQuaternion: [frozen.x, frozen.y, frozen.z, frozen.w] }, movingSky, resolved);
assert(near(resolved.angleTo(frozen), 0), "tracking off keeps the frozen 3D orientation independently of the current sky");
setMeasurementPresentationQuaternion({ tracking: true, fixedQuaternion: null }, movingSky, resolved);
assert(near(resolved.angleTo(movingSky), 0), "tracking on follows the current celestial orientation");

const parent = new THREE.Group();
const renderer = new MeasurementLayerRendererImpl(parent, parent);
renderer.mountLabels({ appendChild: () => undefined } as unknown as HTMLElement);
renderer.presentDocument(snapshot(1, [entity("a", 1, 25), entity("b", 1, 30)]));
const afterCreate = renderer.metrics();
assert(afterCreate.activeEntityCount === 2 && afterCreate.lastChangedEntityCount === 2, "initial snapshot builds both retained entities");
renderer.presentPreview(previewGeometry("circle", { altitudeDeg: 0, azimuthDeg: 0 }, { altitudeDeg: 2, azimuthDeg: 0 }));
assert(renderer.metrics().geometryBuildCount === afterCreate.geometryBuildCount, "pointer preview reuses its fixed GPU buffer");
renderer.presentDocument(snapshot(2, [entity("a", 2, 27), entity("b", 1, 30)], "a"));
const afterOneEdit = renderer.metrics();
assert(afterOneEdit.lastChangedEntityCount === 1, "editing one measurement only rebuilds one entity batch");
assert(afterOneEdit.geometryBuildCount - afterCreate.geometryBuildCount === 2, "one edit builds one line and one handle geometry");
assert(afterOneEdit.geometryDisposeCount === 2, "one edit disposes the replaced line and handle geometry");
const camera = new THREE.PerspectiveCamera(60, 16 / 9, 0.1, 10_000_000);
camera.updateProjectionMatrix(); camera.updateMatrixWorld();
renderer.updateLabels(camera, { left: 0, top: 0, width: 1600, height: 900 } as DOMRect);
assert(fakeLabels.some(label => !label.hidden && label.style.transform.length > 0), "accepted labels reproject against camera and viewport");
renderer.dispose();
assert(renderer.metrics().activeEntityCount === 0, "dispose releases all retained entities");

Object.defineProperty(globalThis, "document", { configurable: true, value: previousDocument });
if (failures > 0) throw new Error(`${failures} measurement tests failed`);
console.log("Paso 21 measurement tests passed");
