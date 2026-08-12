import * as THREE from "three";
import type { DeepSkyPickHit, DeepSkyPickRef } from "../../../contracts/deep_sky_picking_contracts";
import type { SkyVisibilityState } from "../../../contracts/sky_environment_contracts";
import { DEFAULT_SKY_VISIBILITY } from "../../../contracts/sky_visibility_defaults";
import type { CelestialTransformState } from "../CelestialTransformState";
import type { DeepSkyRenderer } from "../DeepSkyRenderer";

const LOG_PREFIX = "MGP: [DeepSkyPickProvider]";
const SKY_RADIUS = 1000000.0;

const _raycaster = new THREE.Raycaster();
const _ndcVec = new THREE.Vector2();
const _rayDir = new THREE.Vector3();
const _eqDir = new THREE.Vector3();
const _worldPos = new THREE.Vector3();
const _screenPos = new THREE.Vector3();
const _mat3Inv = new THREE.Matrix3();

export interface DeepSkyPickProviderDeps {
  camera: THREE.PerspectiveCamera;
  transformState: CelestialTransformState;
  renderer: THREE.WebGLRenderer;
  deepSkyRenderer: DeepSkyRenderer;
  getSkyVisibilityState: () => SkyVisibilityState | null;
  isDeepSkyLayerVisible: () => boolean;
}

export class DeepSkyPickProvider {
  private readonly deps: DeepSkyPickProviderDeps;

  constructor(deps: DeepSkyPickProviderDeps) {
    this.deps = deps;
  }

  pick(clientX: number, clientY: number): DeepSkyPickHit | null {
    if (!this.deps.isDeepSkyLayerVisible() || !this.deps.deepSkyRenderer.visible) {
      return null;
    }

    if (!this.deps.transformState.isValid) {
      return null;
    }

    const { camera, renderer, deepSkyRenderer } = this.deps;
    const { metadata, payloadBuffer } = deepSkyRenderer;

    if (!metadata || !payloadBuffer) {
      return null;
    }

    const rect = renderer.domElement.getBoundingClientRect();
    const localX = clientX - rect.left;
    const localY = clientY - rect.top;
    _ndcVec.set((localX / rect.width) * 2 - 1, -(localY / rect.height) * 2 + 1);

    _raycaster.setFromCamera(_ndcVec, camera);
    const ray = _raycaster.ray;

    _rayDir.copy(ray.direction).normalize();
    _mat3Inv.copy(this.deps.transformState.threeToEquatorial);
    _eqDir.copy(_rayDir).applyMatrix3(_mat3Inv).normalize();

    const maxHitCssPx = 30;
    const queryAngleRad = this.computeQueryAngleRad(_ndcVec.x, _ndcVec.y, maxHitCssPx, rect.width, rect.height, camera);

    const count = metadata.renderableCount ?? metadata.recordCount;
    const layout = metadata.bufferLayout;

    const eqDirs = new Float32Array(payloadBuffer, layout.equatorialDirections.offset, count * 3);
    const mags = new Float32Array(payloadBuffer, layout.magnitude.offset, count);
    const majAx = new Float32Array(payloadBuffer, layout.majorAxisArcmin.offset, count);
    const minAx = new Float32Array(payloadBuffer, layout.minorAxisArcmin.offset, count);
    const paDeg = new Float32Array(payloadBuffer, layout.positionAngleDeg.offset, count);
    const surfBr = new Float32Array(payloadBuffer, layout.surfaceBrightness.offset, count);
    const famU32 = new Uint32Array(payloadBuffer, layout.familyCode.offset, count);
    const catU32 = new Uint32Array(payloadBuffer, layout.catalogIndex.offset, count);
    const objectLabels = (metadata.objectLabels as string[] | undefined) ?? [];

    let bestHit: DeepSkyPickHit | null = null;
    const visibilityState = this.deps.getSkyVisibilityState() ?? DEFAULT_SKY_VISIBILITY;

    // Linear scan for 14k items is very fast (~0.1ms)
    for (let i = 0; i < count; i++) {
      const vx = eqDirs[i * 3]!;
      const vy = eqDirs[i * 3 + 1]!;
      const vz = eqDirs[i * 3 + 2]!;

      // Dot product to check if it's within the query cone
      const dot = _eqDir.x * vx + _eqDir.y * vy + _eqDir.z * vz;
      if (dot < Math.cos(queryAngleRad)) continue;

      _worldPos.set(vx, vy, vz);
      _worldPos.applyMatrix3(this.deps.transformState.equatorialToThree);

      // Check horizon cull (y > 0ish)
      if (_worldPos.y < -0.1) continue;

      const mag = mags[i]! > -1 ? mags[i]! : 15.0;

      // Twilight fade check
      const fade = 1.0 - visibilityState.twilightSuppression;
      if (fade <= 0.01) continue;

      _worldPos.multiplyScalar(SKY_RADIUS);
      _worldPos.add(camera.position);

      _screenPos.copy(_worldPos).project(camera);

      if (_screenPos.z > 1 || _screenPos.z < -1) continue;

      const screenX = ((_screenPos.x + 1) / 2) * rect.width;
      const screenY = ((1 - _screenPos.y) / 2) * rect.height;

      const dx = localX - screenX;
      const dy = localY - screenY;
      const dist = Math.sqrt(dx * dx + dy * dy);

      // Give larger objects a larger hit radius, up to maxHitCssPx
      const maj = majAx[i]! > 0 ? majAx[i]! : 2.0;
      const pxPerArcmin = (rect.height / camera.fov) * (1 / 60.0);
      const visualRadius = Math.max(5, (maj / 2.0) * pxPerArcmin);
      const hitRadius = Math.min(maxHitCssPx, visualRadius + 15);

      if (dist > hitRadius) continue;

      if (!bestHit || dist < bestHit.screenDistanceCssPx) {
        const decDeg = Math.asin(vz) * (180 / Math.PI);
        const raDeg = ((Math.atan2(vy, vx) * (180 / Math.PI)) + 360) % 360;

        bestHit = {
          kind: "deep_sky",
          ref: {
            resourceId: metadata.resourceId,
            resourceVersion: metadata.version || "unknown",
            catalogIndex: catU32[i]!,
          },
          screenXCssPx: screenX,
          screenYCssPx: screenY,
          screenDistanceCssPx: dist,
          visualRadiusCssPx: visualRadius,
          hitRadiusCssPx: hitRadius,
          objectLabel: objectLabels[i] || "NGC",
          magnitude: mags[i]! > -1 ? mags[i]! : null,
          majorAxisArcmin: majAx[i]! > 0 ? majAx[i]! : null,
          minorAxisArcmin: minAx[i]! > 0 ? minAx[i]! : null,
          positionAngleDeg: (paDeg[i]! >= 0 || paDeg[i]! < 0) ? paDeg[i]! : null, // check NaN
          surfaceBrightness: surfBr[i]! > 0 ? surfBr[i]! : null,
          familyCode: famU32[i]!,
          raDeg,
          decDeg,
        };
      }
    }

    return bestHit;
  }

  reprojectRef(ref: DeepSkyPickRef): { x: number; y: number; visualRadiusCssPx: number } | null {
    if (!this.deps.transformState.isValid) return null;
    const { metadata, payloadBuffer, catalogIndexToBufferIndex } = this.deps.deepSkyRenderer;
    if (!metadata || !payloadBuffer || metadata.resourceId !== ref.resourceId) return null;
    if (metadata.version && metadata.version !== ref.resourceVersion) return null; // Invalidate old version

    const idx = catalogIndexToBufferIndex.get(ref.catalogIndex);
    if (idx === undefined) return null;

    const count = metadata.renderableCount ?? metadata.recordCount;
    const layout = metadata.bufferLayout;
    const eqDirs = new Float32Array(payloadBuffer, layout.equatorialDirections.offset, count * 3);
    const majAx = new Float32Array(payloadBuffer, layout.majorAxisArcmin.offset, count);

    const camera = this.deps.camera;
    const rect = this.deps.renderer.domElement.getBoundingClientRect();

    const vx = eqDirs[idx * 3]!;
    const vy = eqDirs[idx * 3 + 1]!;
    const vz = eqDirs[idx * 3 + 2]!;

    _worldPos.set(vx, vy, vz);
    _worldPos.applyMatrix3(this.deps.transformState.equatorialToThree);
    _worldPos.multiplyScalar(SKY_RADIUS);
    _worldPos.add(camera.position);

    _screenPos.copy(_worldPos).project(camera);

    if (_screenPos.z > 1 || _screenPos.z < -1) return null;

    const screenX = ((_screenPos.x + 1) / 2) * rect.width;
    const screenY = ((1 - _screenPos.y) / 2) * rect.height;

    if (screenX < -50 || screenX > rect.width + 50 || screenY < -50 || screenY > rect.height + 50) return null;

    const maj = majAx[idx]! > 0 ? majAx[idx]! : 2.0;
    const pxPerArcmin = (rect.height / camera.fov) * (1 / 60.0);
    const visualRadius = Math.max(5, (maj / 2.0) * pxPerArcmin);

    return { x: screenX, y: screenY, visualRadiusCssPx: visualRadius };
  }

  private computeQueryAngleRad(
    ndcX: number, ndcY: number, maxHitCssPx: number, viewportW: number, viewportH: number, camera: THREE.PerspectiveCamera,
  ): number {
    const r0 = new THREE.Vector2(ndcX, ndcY);
    _raycaster.setFromCamera(r0, camera);
    const dir0 = _raycaster.ray.direction.clone().normalize();

    const offsetNdcX = ndcX + (maxHitCssPx / viewportW) * 2;
    const r1 = new THREE.Vector2(offsetNdcX, ndcY);
    _raycaster.setFromCamera(r1, camera);
    const dir1 = _raycaster.ray.direction.clone().normalize();

    const angle = Math.acos(Math.min(1, dir0.dot(dir1)));
    return Math.max(angle * 1.5, 0.01);
  }

  dispose(): void {
    // No spatial index to dispose
  }
}
