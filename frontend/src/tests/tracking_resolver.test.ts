import * as THREE from "three";
import { TrackingTargetResolver } from "../view/three/picking/TrackingTargetResolver";
import { CelestialTransformState } from "../view/three/CelestialTransformState";
import type { SolarSystemRenderer } from "../view/three/SolarSystemRenderer";
import { threeDirectionToCameraPose } from "../view/three/CameraRigImpl";

function assert(condition: boolean, message: string): void {
  if (!condition) {
    throw new Error(`Assertion failed: ${message}`);
  }
}

function assertCloseTo(actual: number, expected: number, tolerance = 0.05, message = "") {
  if (Math.abs(actual - expected) > tolerance) {
    throw new Error(`Assertion failed: expected ${expected} +- ${tolerance}, got ${actual}. ${message}`);
  }
}

console.log("Running TrackingTargetResolver tests...");

{
  const resolver = new TrackingTargetResolver();
  const transform = new CelestialTransformState();
  // We use Identity matrix for equatorialToThree.
  // This means Equatorial (X,Y,Z) maps directly to ENU (East, Up, -North).
  transform.update(1, [
    1, 0, 0,
    0, 1, 0,
    0, 0, 1
  ]);
  resolver.updateCelestialTransform(transform);
  
  // Case 1: RA=0, Dec=0 -> Equatorial [1,0,0] -> ENU [1,0,0] (East -> az 270)
  const res1 = resolver.resolve({ kind: "coordinate", raDeg: 0, decDeg: 0, frame: "J2000" });
  assertCloseTo(res1!.azimuthDeg, 270, 0.5, "RA=0, Dec=0 -> East");
  assertCloseTo(res1!.altitudeDeg, 0, 0.5, "RA=0, Dec=0 -> Alt 0");

  // Case 2: RA=90, Dec=0 -> Equatorial [0,1,0] -> ENU [0,1,0] (North -> az 0)
  const res2 = resolver.resolve({ kind: "coordinate", raDeg: 90, decDeg: 0, frame: "J2000" });
  assertCloseTo(res2!.azimuthDeg, 0, 0.5, "RA=90, Dec=0 -> North");
  assertCloseTo(res2!.altitudeDeg, 0, 0.5, "RA=90, Dec=0 -> Alt 0");

  // Case 3: Dec=+90 -> Equatorial [0,0,1] -> ENU [0,0,1] (Zenith -> alt 90)
  const res3 = resolver.resolve({ kind: "coordinate", raDeg: 0, decDeg: 90, frame: "J2000" });
  assertCloseTo(res3!.altitudeDeg, 90, 0.5, "Dec=+90 -> Zenith");

  // Case 4: Dec=-90 -> Equatorial [0,0,-1] -> ENU [0,0,-1] (Nadir -> alt -90)
  const res4 = resolver.resolve({ kind: "coordinate", raDeg: 0, decDeg: -90, frame: "J2000" });
  assertCloseTo(res4!.altitudeDeg, -90, 0.5, "Dec=-90 -> Nadir");
}

{
  const resolver = new TrackingTargetResolver();
  
  // Fake SolarSystemRenderer
  const mockRenderer = {
    getDisplayedBodyDirection: (id: string) => {
      if (id === "moon") {
        return new THREE.Vector3(1, 0, 0); // East
      }
      if (id === "sun") {
        return new THREE.Vector3(0, 1, 0); // Zenith
      }
      if (id === "jupiter") {
        return new THREE.Vector3(-1, 0, -1).normalize(); // NW
      }
      if (id === "test1") {
        return new THREE.Vector3(0.001, 0, -1).normalize(); // Slightly East of North
      }
      if (id === "test2") {
        return new THREE.Vector3(-0.001, 0, -1).normalize(); // Slightly West of North
      }
      return null;
    }
  } as unknown as SolarSystemRenderer;
  
  resolver.updateSolarSystemRenderer(mockRenderer);
  
  const resultMoon = resolver.resolve({ kind: "solar_system", bodyId: "moon" });
  assertCloseTo(resultMoon!.azimuthDeg, 270, 0.5, "Moon az 270");
  assertCloseTo(resultMoon!.altitudeDeg, 0, 0.5, "Moon alt 0");
  
  const resultSun = resolver.resolve({ kind: "solar_system", bodyId: "sun" });
  assertCloseTo(resultSun!.altitudeDeg, 90, 0.5, "Sun alt 90");
  
  const resultJup = resolver.resolve({ kind: "solar_system", bodyId: "jupiter" });
  assertCloseTo(resultJup!.azimuthDeg, 45, 0.5, "Jupiter az 45");
  
  const slightlyEast = resolver.resolve({ kind: "solar_system", bodyId: "test1" });
  assertCloseTo(slightlyEast!.azimuthDeg, 359.94, 0.1, "Test1 az ~360");
  
  const slightlyWest = resolver.resolve({ kind: "solar_system", bodyId: "test2" });
  assertCloseTo(slightlyWest!.azimuthDeg, 0.06, 0.1, "Test2 az ~0");
}



{
  // Test: Geometric precision & Projection test (Case B requirements)
  // Ensure that taking an exact ENU direction (e.g. from SolarSystemRenderer)
  // converting it to CameraRig pose, and applying it to a camera,
  // yields exactly the same direction and projects to NDC (0,0).
  
  // Simulated displayed ENU direction (very extreme FOV precision check)
  const dirENU = new THREE.Vector3(-0.123456789, 0.987654321, -0.555555555).normalize();
  
  // 1. Resolve to az/alt using centralized function
  const pose = threeDirectionToCameraPose(dirENU);
  
  // 2. Simulate CameraRigImpl.applyToCamera()
  const azRad = pose.azimuthDeg * (Math.PI / 180);
  const altRad = pose.altitudeDeg * (Math.PI / 180);
  
  const cosAlt = Math.cos(altRad);
  const camDir = new THREE.Vector3(
    -Math.sin(azRad) * cosAlt,
    Math.sin(altRad),
    -Math.cos(azRad) * cosAlt
  );
  
  // 3. Angular Error check
  const angularError = dirENU.angleTo(camDir) * (180 / Math.PI);
  assertCloseTo(angularError, 0, 2e-6, "Angular error must be < 2e-6 degrees");
  
  // 4. Projection check (NDC X~0, Y~0)
  const camera = new THREE.PerspectiveCamera(0.001, 1.0, 0.1, 1000);
  camera.position.set(100, 200, 300); // arbitrary position
  const target = camera.position.clone().add(camDir);
  camera.lookAt(target);
  camera.updateMatrixWorld();
  
  // Project the original displayed direction body center (far away)
  const bodyCenter = camera.position.clone().add(dirENU.clone().multiplyScalar(1e8));
  bodyCenter.project(camera);
  
  assertCloseTo(bodyCenter.x, 0, 1e-5, "NDC.x ~= 0");
  assertCloseTo(bodyCenter.y, 0, 1e-5, "NDC.y ~= 0");
}

console.log("TrackingTargetResolver tests passed.");
