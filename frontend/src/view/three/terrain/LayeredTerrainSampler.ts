/**
 * Collision sampler for a persistent coarse DEM mesh plus retained streamed
 * detail chunks. Newer chunks win where they have valid coverage; older
 * chunks and finally the long-range resident mesh provide spatial fallback.
 */

import * as THREE from "three";
import type { GroundSample, TerrainSampler } from "../../../contracts/TerrainSampler";
import {
  TechnicalTerrainSampler,
  type TerrainNavigationSampling,
} from "./TechnicalTerrainSampler";

export interface TerrainDetailLayer {
  readonly contentKey: string;
  readonly mesh: THREE.Mesh;
  readonly sampling: TerrainNavigationSampling | null;
}

interface DetailSamplerEntry {
  readonly mesh: THREE.Mesh;
  readonly sampler: TechnicalTerrainSampler;
}

export class LayeredTerrainSampler implements TerrainSampler {
  private readonly base = new TechnicalTerrainSampler();
  private details = new Map<string, DetailSamplerEntry>();
  private detailSamplers: readonly DetailSamplerEntry[] = [];

  setBaseTerrain(mesh: THREE.Mesh, sampling?: TerrainNavigationSampling | null): void {
    this.base.setTerrainMesh(mesh, sampling);
  }

  setDetailTerrain(mesh: THREE.Mesh | null, sampling?: TerrainNavigationSampling | null): void {
    if (!mesh) {
      this.details.clear();
      this.detailSamplers = [];
      return;
    }
    this.setDetailTerrains([{ contentKey: "legacy-detail", mesh, sampling: sampling ?? null }]);
  }

  /** Reuse collision samplers for chunks that remain resident in the GPU cache. */
  setDetailTerrains(layers: readonly TerrainDetailLayer[]): void {
    const next = new Map<string, DetailSamplerEntry>();
    for (const layer of layers) {
      const existing = this.details.get(layer.contentKey);
      if (existing?.mesh === layer.mesh) {
        next.set(layer.contentKey, existing);
        continue;
      }
      const sampler = new TechnicalTerrainSampler();
      sampler.setTerrainMesh(layer.mesh, layer.sampling);
      next.set(layer.contentKey, { mesh: layer.mesh, sampler });
    }
    this.details = next;
    this.detailSamplers = Array.from(next.values());
  }

  isReady(): boolean {
    return this.base.isReady();
  }

  sampleGround(eastM: number, northM: number, referenceUpM?: number): GroundSample | null {
    for (let index = this.detailSamplers.length - 1; index >= 0; index--) {
      const detailSample = this.detailSamplers[index]!.sampler.sampleGround(
        eastM,
        northM,
        referenceUpM,
      );
      if (detailSample) return detailSample;
    }
    return this.base.sampleGround(eastM, northM, referenceUpM);
  }
}
