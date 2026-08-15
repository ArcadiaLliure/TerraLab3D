/**
 * Terrain sampler for navigation over the resident DEM mesh.
 *
 * The renderer owns one persistent indexed BufferGeometry in GPU memory. A
 * downward Three.js raycast through hundreds of thousands of its triangles on
 * every movement frame is not an acceptable collision strategy. The DEM
 * builder publishes its compact near-grid / polar-ring topology; this class
 * reads the same position and normal attributes directly in O(log rings),
 * without creating another terrain mesh or touching the GPU.
 *
 * A generic raycast remains as a fallback for the small technical startup
 * surface and test meshes that do not have DEM topology metadata.
 */

import * as THREE from "three";
import type { GroundSample, TerrainSampler } from "../../../contracts/TerrainSampler";

const RAD2DEG = 180 / Math.PI;
const UP = new THREE.Vector3(0, 1, 0);
const PROBE_MARGIN_M = 100;

export interface TerrainNavigationSampling {
  readonly nearAxisM: Float32Array<ArrayBufferLike>;
  readonly polarDistanceM: Float32Array<ArrayBufferLike>;
  readonly polarAzimuthStepDeg: number;
  /** Centre of this mesh chunk in the persistent observer ENU world. */
  readonly centerEastM?: number;
  readonly centerNorthM?: number;
}

export class TechnicalTerrainSampler implements TerrainSampler {
  private readonly raycaster = new THREE.Raycaster();
  private readonly rayOrigin = new THREE.Vector3();
  private readonly rayDir = new THREE.Vector3(0, -1, 0);
  private readonly terrainBounds = new THREE.Box3();
  private terrainMesh: THREE.Mesh | null = null;
  private ready = false;

  // Attributes are shared with the persistent render mesh; no duplicate DEM
  // positions or normals are allocated for collision.
  private positions: ArrayLike<number> | null = null;
  private normals: ArrayLike<number> | null = null;
  private validVertices: Uint8Array<ArrayBufferLike> = new Uint8Array(0);
  private nearAxisM: Float32Array<ArrayBufferLike> = new Float32Array(0);
  private polarDistanceM: Float32Array<ArrayBufferLike> = new Float32Array(0);
  private nearVertexCount = 0;
  private polarAzimuthCount = 0;
  private polarAzimuthStepDeg = 0;
  private centerEastM = 0;
  private centerNorthM = 0;
  private hasStructuredDemSampling = false;

  /**
   * Attach the visible terrain mesh. Supplying its topology activates the
   * direct DEM sampler; without it the technical raycast fallback is kept for
   * startup compatibility.
   */
  setTerrainMesh(mesh: THREE.Mesh, sampling?: TerrainNavigationSampling | null): void {
    this.terrainMesh = mesh;
    mesh.updateWorldMatrix(true, false);
    mesh.geometry.computeBoundingBox();
    if (mesh.geometry.boundingBox) {
      this.terrainBounds.copy(mesh.geometry.boundingBox).applyMatrix4(mesh.matrixWorld);
    } else {
      this.terrainBounds.makeEmpty();
    }
    this.configureStructuredDemSampling(mesh.geometry, mesh.matrixWorld, sampling ?? null);
    this.ready = true;
  }

  isReady(): boolean {
    return this.ready && this.terrainMesh !== null;
  }

  sampleGround(
    eastM: number,
    northM: number,
    referenceUpM?: number,
  ): GroundSample | null {
    if (!this.terrainMesh) return null;
    if (this.hasStructuredDemSampling) return this.sampleStructuredDem(eastM, northM);
    return this.sampleByRaycast(eastM, northM, referenceUpM);
  }

  private configureStructuredDemSampling(
    geometry: THREE.BufferGeometry,
    matrixWorld: THREE.Matrix4,
    sampling: TerrainNavigationSampling | null,
  ): void {
    this.hasStructuredDemSampling = false;
    this.positions = null;
    this.normals = null;
    this.validVertices = new Uint8Array(0);
    this.nearAxisM = new Float32Array(0);
    this.polarDistanceM = new Float32Array(0);
    this.nearVertexCount = 0;
    this.polarAzimuthCount = 0;
    this.polarAzimuthStepDeg = 0;
    this.centerEastM = 0;
    this.centerNorthM = 0;
    if (!sampling || !isIdentityMatrix(matrixWorld)) return;

    const position = geometry.getAttribute("position") as THREE.BufferAttribute | undefined;
    const normal = geometry.getAttribute("normal") as THREE.BufferAttribute | undefined;
    if (!position || !normal || position.itemSize !== 3 || normal.itemSize !== 3) return;
    const nearAxisM = sampling.nearAxisM;
    const polarDistanceM = sampling.polarDistanceM;
    const nearVertexCount = nearAxisM.length * nearAxisM.length;
    const polarVertexCount = position.count - nearVertexCount;
    if (
      nearAxisM.length < 2
      || polarDistanceM.length < 2
      || polarVertexCount <= 0
      || polarVertexCount % polarDistanceM.length !== 0
      || !Number.isFinite(sampling.polarAzimuthStepDeg)
      || sampling.polarAzimuthStepDeg <= 0
    ) return;
    const polarAzimuthCount = polarVertexCount / polarDistanceM.length;
    if (polarAzimuthCount < 3) return;

    this.positions = position.array;
    this.normals = normal.array;
    this.validVertices = indexedVertexMask(geometry, position.count);
    this.nearAxisM = nearAxisM;
    this.polarDistanceM = polarDistanceM;
    this.nearVertexCount = nearVertexCount;
    this.polarAzimuthCount = polarAzimuthCount;
    this.polarAzimuthStepDeg = sampling.polarAzimuthStepDeg;
    this.centerEastM = Number.isFinite(sampling.centerEastM) ? sampling.centerEastM! : 0;
    this.centerNorthM = Number.isFinite(sampling.centerNorthM) ? sampling.centerNorthM! : 0;
    this.hasStructuredDemSampling = true;
  }

  private sampleStructuredDem(eastM: number, northM: number): GroundSample | null {
    const localEastM = eastM - this.centerEastM;
    const localNorthM = northM - this.centerNorthM;
    const nearMinimum = this.nearAxisM[0]!;
    const nearMaximum = this.nearAxisM[this.nearAxisM.length - 1]!;
    if (
      localEastM >= nearMinimum && localEastM <= nearMaximum
      && localNorthM >= nearMinimum && localNorthM <= nearMaximum
    ) {
      // The polar mesh overlaps the 160 m patch from 40 m onward. If a DEM
      // nodata cell makes the near quad invalid, continue with that valid
      // overlapping representation rather than creating a collision hole.
      return this.sampleNearGrid(localEastM, localNorthM) ?? this.samplePolarGrid(localEastM, localNorthM);
    }
    return this.samplePolarGrid(localEastM, localNorthM);
  }

  private sampleNearGrid(eastM: number, northM: number): GroundSample | null {
    const eastIndex = lowerGridIndex(this.nearAxisM, eastM);
    const northIndex = lowerGridIndex(this.nearAxisM, northM);
    if (eastIndex < 0 || northIndex < 0) return null;
    const axisLength = this.nearAxisM.length;
    return this.interpolateVertices(
      northIndex * axisLength + eastIndex,
      northIndex * axisLength + eastIndex + 1,
      (northIndex + 1) * axisLength + eastIndex,
      (northIndex + 1) * axisLength + eastIndex + 1,
      gridFraction(this.nearAxisM, eastIndex, eastM),
      gridFraction(this.nearAxisM, northIndex, northM),
    );
  }

  private samplePolarGrid(eastM: number, northM: number): GroundSample | null {
    const distanceM = Math.hypot(eastM, northM);
    const radialIndex = lowerGridIndex(this.polarDistanceM, distanceM);
    if (radialIndex < 0) return null;
    const azimuthDeg = ((Math.atan2(eastM, northM) * RAD2DEG) + 360) % 360;
    const azimuthPosition = azimuthDeg / this.polarAzimuthStepDeg;
    const azimuthIndex = Math.floor(azimuthPosition) % this.polarAzimuthCount;
    const nextAzimuth = (azimuthIndex + 1) % this.polarAzimuthCount;
    const innerOffset = this.nearVertexCount + radialIndex * this.polarAzimuthCount;
    const outerOffset = innerOffset + this.polarAzimuthCount;
    return this.interpolateVertices(
      innerOffset + azimuthIndex,
      innerOffset + nextAzimuth,
      outerOffset + azimuthIndex,
      outerOffset + nextAzimuth,
      azimuthPosition - Math.floor(azimuthPosition),
      gridFraction(this.polarDistanceM, radialIndex, distanceM),
    );
  }

  /** Bilinear interpolation of four vertices in the uploaded DEM mesh. */
  private interpolateVertices(
    lowerLeft: number,
    lowerRight: number,
    upperLeft: number,
    upperRight: number,
    horizontalFraction: number,
    verticalFraction: number,
  ): GroundSample | null {
    if (!this.positions || !this.normals) return null;
    if (
      this.validVertices[lowerLeft] !== 1
      || this.validVertices[lowerRight] !== 1
      || this.validVertices[upperLeft] !== 1
      || this.validVertices[upperRight] !== 1
    ) return null;
    const lowerWeight = 1 - verticalFraction;
    const upperWeight = verticalFraction;
    const leftWeight = 1 - horizontalFraction;
    const rightWeight = horizontalFraction;
    const lowerLeftWeight = lowerWeight * leftWeight;
    const lowerRightWeight = lowerWeight * rightWeight;
    const upperLeftWeight = upperWeight * leftWeight;
    const upperRightWeight = upperWeight * rightWeight;
    const positions = this.positions;
    const normals = this.normals;
    const heightM = (
      positions[lowerLeft * 3 + 1]! * lowerLeftWeight
      + positions[lowerRight * 3 + 1]! * lowerRightWeight
      + positions[upperLeft * 3 + 1]! * upperLeftWeight
      + positions[upperRight * 3 + 1]! * upperRightWeight
    );
    let normalEast = (
      normals[lowerLeft * 3]! * lowerLeftWeight
      + normals[lowerRight * 3]! * lowerRightWeight
      + normals[upperLeft * 3]! * upperLeftWeight
      + normals[upperRight * 3]! * upperRightWeight
    );
    let normalUp = (
      normals[lowerLeft * 3 + 1]! * lowerLeftWeight
      + normals[lowerRight * 3 + 1]! * lowerRightWeight
      + normals[upperLeft * 3 + 1]! * upperLeftWeight
      + normals[upperRight * 3 + 1]! * upperRightWeight
    );
    let normalThreeZ = (
      normals[lowerLeft * 3 + 2]! * lowerLeftWeight
      + normals[lowerRight * 3 + 2]! * lowerRightWeight
      + normals[upperLeft * 3 + 2]! * upperLeftWeight
      + normals[upperRight * 3 + 2]! * upperRightWeight
    );
    const normalLength = Math.hypot(normalEast, normalUp, normalThreeZ);
    if (!Number.isFinite(heightM) || normalLength < 1e-6) return null;
    normalEast /= normalLength;
    normalUp /= normalLength;
    normalThreeZ /= normalLength;
    return {
      heightM,
      normal: { east: normalEast, up: normalUp, north: -normalThreeZ },
      slopeDeg: Math.acos(clamp(normalUp, -1, 1)) * RAD2DEG,
      valid: true,
      surfaceId: "dem_terrain_mesh",
    };
  }

  private sampleByRaycast(
    eastM: number,
    northM: number,
    referenceUpM?: number,
  ): GroundSample | null {
    if (!this.terrainMesh) return null;
    const boundsTop = this.terrainBounds.isEmpty() ? 0 : this.terrainBounds.max.y;
    const boundsBottom = this.terrainBounds.isEmpty() ? 0 : this.terrainBounds.min.y;
    const probeHeight = Math.max(referenceUpM ?? boundsTop, boundsTop) + PROBE_MARGIN_M;
    this.rayOrigin.set(eastM, probeHeight, -northM);
    this.raycaster.set(this.rayOrigin, this.rayDir);
    this.raycaster.far = probeHeight - boundsBottom + PROBE_MARGIN_M;

    const hit = this.raycaster.intersectObject(this.terrainMesh, false)[0];
    if (!hit?.face || !hit.point) return null;
    const normalMatrix = new THREE.Matrix3().getNormalMatrix(this.terrainMesh.matrixWorld);
    const worldNormal = hit.face.normal.clone().applyMatrix3(normalMatrix).normalize();
    if (!Number.isFinite(worldNormal.x) || !Number.isFinite(worldNormal.y) || !Number.isFinite(worldNormal.z)) return null;
    if (worldNormal.lengthSq() < 0.5 || !Number.isFinite(hit.point.y)) return null;
    return {
      heightM: hit.point.y,
      normal: { east: worldNormal.x, up: worldNormal.y, north: -worldNormal.z },
      slopeDeg: Math.acos(clamp(worldNormal.dot(UP), -1, 1)) * RAD2DEG,
      valid: true,
      surfaceId: "technical_terrain",
    };
  }
}

function indexedVertexMask(geometry: THREE.BufferGeometry, vertexCount: number): Uint8Array {
  const mask = new Uint8Array(vertexCount);
  const index = geometry.getIndex();
  if (!index) {
    mask.fill(1);
    return mask;
  }
  for (let offset = 0; offset < index.count; offset++) {
    const vertex = index.getX(offset);
    if (vertex >= 0 && vertex < vertexCount) mask[vertex] = 1;
  }
  return mask;
}

function lowerGridIndex(values: Float32Array<ArrayBufferLike>, value: number): number {
  if (value < values[0]! || value > values[values.length - 1]!) return -1;
  let lower = 0;
  let upper = values.length - 1;
  while (upper - lower > 1) {
    const middle = (lower + upper) >>> 1;
    if (values[middle]! <= value) lower = middle;
    else upper = middle;
  }
  return Math.min(lower, values.length - 2);
}

function gridFraction(values: Float32Array<ArrayBufferLike>, lowerIndex: number, value: number): number {
  const lower = values[lowerIndex]!;
  const upper = values[lowerIndex + 1]!;
  return clamp((value - lower) / Math.max(1e-9, upper - lower), 0, 1);
}

function clamp(value: number, minimum: number, maximum: number): number {
  return Math.max(minimum, Math.min(maximum, value));
}

function isIdentityMatrix(matrix: THREE.Matrix4): boolean {
  const values = matrix.elements;
  return (
    values[0] === 1 && values[1] === 0 && values[2] === 0 && values[3] === 0
    && values[4] === 0 && values[5] === 1 && values[6] === 0 && values[7] === 0
    && values[8] === 0 && values[9] === 0 && values[10] === 1 && values[11] === 0
    && values[12] === 0 && values[13] === 0 && values[14] === 0 && values[15] === 1
  );
}
