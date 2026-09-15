import * as THREE from 'three';
import { LineSegmentsGeometry } from 'three/examples/jsm/lines/LineSegmentsGeometry.js';
import { LineMaterial } from 'three/examples/jsm/lines/LineMaterial.js';
import { LineSegments2 } from 'three/examples/jsm/lines/LineSegments2.js';

try {
  const geom = new LineSegmentsGeometry();
  console.log("Setting 0 positions");
  geom.setPositions(new Float32Array(0));
  console.log("Success with 0 positions");
} catch (e) {
  console.error("Error with 0 positions:", e);
}

try {
  const geom = new LineSegmentsGeometry();
  geom.setPositions(new Float32Array([0,0,0, 1,1,1]));
  const mat = new LineMaterial({ dashed: true });
  const line = new LineSegments2(geom, mat);
  console.log("Computing distances");
  line.computeLineDistances();
  console.log("Success with computeLineDistances");
} catch (e) {
  console.error("Error with computeLineDistances:", e);
}
