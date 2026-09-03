import * as THREE from "three";
import { CameraRigImpl } from "../view/three/CameraRigImpl";
import { TrackingTargetResolver } from "../view/three/picking/TrackingTargetResolver";
import { selectionMarkerSizeCssPx } from "../view/three/picking/SelectionMarker";

function assert(condition: boolean, message: string): void {
  if (!condition) {
    throw new Error(`Assertion failed: ${message}`);
  }
}

function assertCloseTo(actual: number, expected: number, tolerance: number, message: string = "") {
  if (Math.abs(actual - expected) > tolerance) {
    throw new Error(`Assertion failed: expected ${expected} +- ${tolerance}, got ${actual}. ${message}`);
  }
}

console.log("=== TerraLab3D Tracking Precision & Float32 Emulation Tests ===");

{
  const wide = selectionMarkerSizeCssPx(400, 60);
  const telescope = selectionMarkerSizeCssPx(400, 0.01);
  const extreme = selectionMarkerSizeCssPx(400, 0.0001);
  assert(wide === 48, "ordinary FOV caps a huge body marker at 48 CSS px");
  assert(telescope === 32, "telescope zoom contracts the marker");
  assert(extreme === 16, "extreme zoom contracts the marker to 16 CSS px");
  assert(wide > telescope && telescope > extreme, "marker size decreases monotonically with zoom");
}

{
  // The shader's angular floating origin must keep a tracked Float32 catalogue
  // direction exactly centred while the celestial transform changes.
  const catalogueDirection = new THREE.Vector3(
    ...new Float32Array([
      Math.cos(0.7) * Math.cos(4.8),
      Math.cos(0.7) * Math.sin(4.8),
      Math.sin(0.7),
    ]),
  );
  let maxCentredDelta = 0;
  for (let index = 0; index < 200; index++) {
    const celestialQuaternion = new THREE.Quaternion().setFromEuler(
      new THREE.Euler(0.73, 1.1 + index * 0.00001, -0.4, "XYZ"),
    );
    const celestial = new THREE.Matrix3().setFromMatrix4(
      new THREE.Matrix4().makeRotationFromQuaternion(celestialQuaternion),
    );
    const displayedDirection = catalogueDirection.clone().applyMatrix3(celestial).normalize();
    const camera = new THREE.PerspectiveCamera(0.0001, 16 / 9, 0.01, 2_000_000);
    camera.lookAt(displayedDirection);
    camera.updateMatrixWorld(true);

    const anchor = camera.getWorldDirection(new THREE.Vector3())
      .applyMatrix3(celestial.clone().invert())
      .normalize();
    const anchorFloat32 = new Float32Array(anchor.toArray());
    maxCentredDelta = Math.max(
      maxCentredDelta,
      Math.abs(catalogueDirection.x - anchorFloat32[0]!),
      Math.abs(catalogueDirection.y - anchorFloat32[1]!),
      Math.abs(catalogueDirection.z - anchorFloat32[2]!),
    );
  }
  assert(maxCentredDelta === 0, "tracked catalogue direction stays exact after Float32 upload");
}

{
  // 1. Emulate WebGL Float32 quantization jitter
  const fov = 0.001; // horizontal FOV
  const viewportWidth = 2160;
  const viewportHeight = 2160;
  const aspect = viewportWidth / viewportHeight;
  
  const camera = new THREE.PerspectiveCamera(fov, aspect, 0.1, 2000000);
  camera.position.set(12345.67, -54321.12, 67890.45);
  // Look at somewhere arbitrary and off-axis
  camera.lookAt(new THREE.Vector3(900000.123, -400000.456, 100000.789));
  camera.updateMatrixWorld();
  camera.updateProjectionMatrix();

  const viewMatrixFloat64 = camera.matrixWorldInverse.clone();
  
  // Model positioned 900,000 units away along the camera forward axis
  const dir = new THREE.Vector3(0, 0, -1).applyMatrix4(camera.matrixWorld).sub(camera.position).normalize();
  const radius = 900000;
  const objectPos = camera.position.clone().add(dir.clone().multiplyScalar(radius));
  
  const modelMatrixFloat64 = new THREE.Matrix4().makeTranslation(objectPos.x, objectPos.y, objectPos.z);
  
  // Position vertex is just origin for the center of the object
  const positionFloat32 = new Float32Array([0.0, 0.0, 0.0, 1.0]);

  // Simulate old behavior: projection * (float32(view) * float32(model)) * pos
  const viewMatrixFloat32 = new Float32Array(viewMatrixFloat64.elements);
  const modelMatrixFloat32 = new Float32Array(modelMatrixFloat64.elements);
  
  // Manual matrix multiplication in float32 space to emulate GPU
  const mat4MulF32 = (a: Float32Array, b: Float32Array): Float32Array => {
    const r = new Float32Array(16);
    for (let i=0; i<4; i++) {
      for (let j=0; j<4; j++) {
        let sum = 0.0;
        for (let k=0; k<4; k++) {
          sum += Math.fround(a[i + k*4]! * b[k + j*4]!);
        }
        r[i + j*4] = Math.fround(sum);
      }
    }
    return r;
  };
  
  const viewF32_modelF32 = mat4MulF32(viewMatrixFloat32, modelMatrixFloat32);
  
  // Apply to position
  const mvPosF32 = new Float32Array(4);
  for (let i=0; i<4; i++) {
    let sum = 0;
    for (let j=0; j<4; j++) {
      sum += Math.fround(viewF32_modelF32[i + j*4]! * positionFloat32[j]!);
    }
    mvPosF32[i] = Math.fround(sum);
  }
  
  // Project to clip space
  const projMatrix = camera.projectionMatrix;
  const clipPosBad = new THREE.Vector4(mvPosF32[0], mvPosF32[1], mvPosF32[2], mvPosF32[3]).applyMatrix4(projMatrix);
  
  // Ndc
  const ndcXBad = clipPosBad.x / clipPosBad.w;
  const ndcYBad = clipPosBad.y / clipPosBad.w;
  const pixelXBad = ((ndcXBad + 1) / 2) * viewportWidth;
  const pixelYBad = ((ndcYBad + 1) / 2) * viewportHeight;
  
  const expectedCenterX = viewportWidth / 2;
  const expectedCenterY = viewportHeight / 2;
  
  const errorPxBadX = Math.abs(pixelXBad - expectedCenterX);
  const errorPxBadY = Math.abs(pixelYBad - expectedCenterY);
  
  console.log(`Float32(view) * Float32(model) error: ${errorPxBadX.toFixed(2)}px, ${errorPxBadY.toFixed(2)}px`);
  assert(errorPxBadX > 0.1 || errorPxBadY > 0.1, "Emulated old behavior should produce jitter > 0.1 px");
  
  // 2. Simulate NEW behavior: Float32(view * model) computed in Float64 CPU
  const modelViewMatrixF64 = new THREE.Matrix4().multiplyMatrices(viewMatrixFloat64, modelMatrixFloat64);
  const modelViewMatrixF32 = new Float32Array(modelViewMatrixF64.elements);
  
  // Apply to position
  const mvPosGoodF32 = new Float32Array(4);
  for (let i=0; i<4; i++) {
    let sum = 0;
    for (let j=0; j<4; j++) {
      sum += Math.fround(modelViewMatrixF32[i + j*4]! * positionFloat32[j]!);
    }
    mvPosGoodF32[i] = Math.fround(sum);
  }
  
  const clipPosGood = new THREE.Vector4(mvPosGoodF32[0], mvPosGoodF32[1], mvPosGoodF32[2], mvPosGoodF32[3]).applyMatrix4(projMatrix);
  const ndcXGood = clipPosGood.x / clipPosGood.w;
  const ndcYGood = clipPosGood.y / clipPosGood.w;
  const pixelXGood = ((ndcXGood + 1) / 2) * viewportWidth;
  const pixelYGood = ((ndcYGood + 1) / 2) * viewportHeight;
  
  const errorPxGoodX = Math.abs(pixelXGood - expectedCenterX);
  const errorPxGoodY = Math.abs(pixelYGood - expectedCenterY);
  
  console.log(`Float32(modelView) error: ${errorPxGoodX.toFixed(4)}px, ${errorPxGoodY.toFixed(4)}px`);
  assert(errorPxGoodX < 0.1 && errorPxGoodY < 0.1, "CPU-computed modelViewMatrix should produce jitter < 0.1 px");
  
  console.log("  ✓ Float32 jitter validation passed.");
}

{
  // 3. Wheel zoom fighting tracking test
  const camera = new THREE.PerspectiveCamera(60, 1, 0.1, 1000);
  const rig = new CameraRigImpl(camera);
  
  const initialFov = rig.pose().horizontalFovDeg;
  
  // Enable tracking mode
  rig.setTrackingState(true);
  
  // Manually trigger onWheel via a dirty hack or just calling the private method using any cast
  const e = {
    preventDefault: () => {},
    deltaY: 100, // zoom out
    clientX: 500, // offset from center to simulate cursor pan zoom
    clientY: 500,
  } as unknown as WheelEvent;
  
  // mock getBoundingClientRect
  rig["container"] = {
    getBoundingClientRect: () => ({ left: 0, top: 0, width: 1000, height: 1000 })
  } as any;
  
  // Keep original direction
  const origPose = rig.pose();
  const origAz = origPose.azimuthDeg;
  const origAlt = origPose.altitudeDeg;
  
  for (let i = 0; i < 20; i++) {
    (rig as any).onWheel(e);
  }
  
  const finalPose = rig.pose();
  
  assert(finalPose.horizontalFovDeg !== initialFov, "FOV should have changed");
  assertCloseTo(finalPose.azimuthDeg, origAz, 1e-6, "Azimuth must remain identical");
  assertCloseTo(finalPose.altitudeDeg, origAlt, 1e-6, "Altitude must remain identical");
  
  console.log("  ✓ Wheel zoom tracking isolation passed.");
}

console.log("=== All Tracking Precision Tests Passed ===");
