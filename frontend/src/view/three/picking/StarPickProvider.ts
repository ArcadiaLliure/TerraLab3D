/**
 * StarPickProvider — proveïdor de picking estel·lar local.
 *
 * Responsable de:
 * - Convertir un punt de pantalla CSS px → ray de càmera Three.js real
 * - Inverse celestial transform → direcció equatorial
 * - Consulta de l'índex espacial (candidats)
 * - Refinament screen-space amb projecció exacta
 * - Ranking determinista dels hits
 * - Verificació de visibilitat, magnitud i oclusió
 *
 * NO fa:
 * - Round-trip al backend per determinar si hi ha hit
 * - Raycaster.intersectObject contra star points (el shader transforma posicions)
 * - GPU readback
 *
 * Usa el Raycaster NOMÉS per obtenir el ray real de la càmera.
 */

import * as THREE from "three";
import type { StarPickHit, StarPickRef } from "../../../contracts/star_picking_contracts";
import type { SkyVisibilityState } from "../../../contracts/sky_environment_contracts";
import type { StarResourceEntry } from "../StarFieldRenderer";
import type { CelestialTransformState } from "../CelestialTransformState";
import { StarSpatialIndex } from "./StarSpatialIndex";
import { StarVisibilityEvaluator } from "./StarVisibilityEvaluator";
import {
  computeStarHitRadiusCssPx,
  computeStarVisualRadiusCssPx,
} from "../shaders/starVisualParams";

const LOG_PREFIX = "MGP: [StarPickProvider]";

/** Radi de l'esfera celeste (ha de coincidir amb u_radius del shader). */
const SKY_RADIUS = 1000000.0;

/** Prioritat de recursos per al ranking. Menys = més prioritari. */
const ROLE_PRIORITY: Record<string, number> = {
  general: 0,
  deep_tile: 1,
  supplement: 2,
  fallback: 3,
};

// ─── Scratch vectors (reutilitzables, zero allocs hot path) ──────────

const _raycaster = new THREE.Raycaster();
const _ndcVec = new THREE.Vector2();
const _rayDir = new THREE.Vector3();
const _eqDir = new THREE.Vector3();
const _worldPos = new THREE.Vector3();
const _screenPos = new THREE.Vector3();
const _mat3Inv = new THREE.Matrix3();

export interface StarPickProviderDeps {
  camera: THREE.PerspectiveCamera;
  transformState: CelestialTransformState;
  renderer: THREE.WebGLRenderer;
  worldRoot: THREE.Group;
  getStarResources: () => ReadonlyMap<string, StarResourceEntry>;
  getMagnitudeLimit: () => number;
  getSkyVisibilityState: () => SkyVisibilityState | null;
  getPointScale: () => number;
  isStarLayerVisible: () => boolean;
}

interface ScoredCandidate {
  ref: StarPickRef;
  screenDistCssPx: number;
  visualRadiusCssPx: number;
  hitRadiusCssPx: number;
  normalizedDist: number;
  magnitude: number;
  rolePriority: number;
  screenXCssPx: number;
  screenYCssPx: number;
}

export class StarPickProvider {
  private readonly deps: StarPickProviderDeps;
  private readonly spatialIndices = new Map<string, StarSpatialIndex>();

  // ─── Instrumentació ────────────────────────────────────────────────
  private _queryCount = 0;
  private _hitCount = 0;
  private _missCount = 0;
  private readonly _queryTimesMs: number[] = [];
  private readonly _candidateCounts: number[] = [];

  constructor(deps: StarPickProviderDeps) {
    this.deps = deps;
  }

  /**
   * Construeix o actualitza l'índex espacial per a un recurs.
   * Cridat quan un recurs es registra per primera vegada.
   */
  buildIndex(resourceId: string, entry: StarResourceEntry): void {
    // Dispose old if exists
    const existing = this.spatialIndices.get(resourceId);
    if (existing) {
      existing.dispose();
    }

    const index = new StarSpatialIndex();
    index.build(entry.equatorialPositions);
    this.spatialIndices.set(resourceId, index);

    console.log(
      `${LOG_PREFIX} [buildIndex] [Índex construït: ${resourceId} (${entry.starCount} estrelles)]`,
    );
  }

  /**
   * Disposa l'índex espacial d'un recurs.
   */
  disposeIndex(resourceId: string): void {
    const index = this.spatialIndices.get(resourceId);
    if (index) {
      index.dispose();
      this.spatialIndices.delete(resourceId);
      console.log(`${LOG_PREFIX} [disposeIndex] [Índex disposat: ${resourceId}]`);
    }
  }

  /**
   * Realitza un picking local contra totes les estrelles residents visibles.
   *
   * @param clientX — coordenada X del pointer (CSS px, event.clientX)
   * @param clientY — coordenada Y del pointer (CSS px, event.clientY)
   * @returns StarPickHit o null si no hi ha hit
   */
  pick(clientX: number, clientY: number): StarPickHit | null {
    const t0 = performance.now();
    this._queryCount++;

    // 0. Verificar que l'estat és vàlid
    if (!this.deps.isStarLayerVisible()) {
      this._missCount++;
      return null;
    }

    if (!this.deps.transformState.isValid) {
      this._missCount++;
      return null;
    }

    const visibilityState = this.deps.getSkyVisibilityState();
    if (!visibilityState) {
      // Si no tenim estat de visibilitat, no podem saber què és clicable
      return null;
    }

    const { camera, renderer, transformState } = this.deps;
    const rect = renderer.domElement.getBoundingClientRect();

    // 1. Convertir client px → NDC [-1, 1]
    const localX = clientX - rect.left;
    const localY = clientY - rect.top;
    _ndcVec.set(
      (localX / rect.width) * 2 - 1,
      -(localY / rect.height) * 2 + 1,
    );

    // 2. Obtenir ray REAL de la càmera via Raycaster
    _raycaster.setFromCamera(_ndcVec, camera);
    const ray = _raycaster.ray;

    // 3. Convertir la direcció del ray a espai equatorial via inverse transform
    _rayDir.copy(ray.direction).normalize();
    _mat3Inv.copy(this.deps.transformState.threeToEquatorial);
    _eqDir.copy(_rayDir).applyMatrix3(_mat3Inv).normalize();

    // 4. Calcular radi angular de consulta basat en FOV i hit radius
    const dpr = this.deps.renderer.getPixelRatio();
    const maxHitCssPx = 30; // radi de cerca generós en CSS px
    const queryAngleRad = this.computeQueryAngleRad(
      _ndcVec.x,
      _ndcVec.y,
      maxHitCssPx,
      rect.width,
      rect.height,
      camera,
    );

    // 5. Consultar candidats per cada recurs registrat
    const magnitudeLimit = this.deps.getMagnitudeLimit();
    const pointScale = this.deps.getPointScale();
    const candidates: ScoredCandidate[] = [];
    let totalCandidates = 0;

    const resources = this.deps.getStarResources();
    for (const [resId, entry] of resources) {
      const index = this.spatialIndices.get(resId);
      if (!index) continue;

      const rawCandidates = index.queryCone(
        _eqDir.x,
        _eqDir.y,
        _eqDir.z,
        queryAngleRad,
      );
      totalCandidates += rawCandidates.length;

      // 6. Refinament screen-space per cada candidat
      for (const starIdx of rawCandidates) {
        const mag = entry.magnitudesArray[starIdx];
        if (mag === undefined) continue;

        // Rebutjar per magnitud (límit dur del catàleg)
        if (mag > magnitudeLimit) continue;

        // Posició equatorial
        const eqX = entry.equatorialPositions[starIdx * 3];
        const eqY = entry.equatorialPositions[starIdx * 3 + 1];
        const eqZ = entry.equatorialPositions[starIdx * 3 + 2];
        const catalogIndex = entry.catalogIndices[starIdx];
        if (catalogIndex === undefined || eqX === undefined || eqY === undefined || eqZ === undefined) continue;

        // Transformar a Three.js via matriu actual
        _worldPos.set(eqX, eqY, eqZ);
        _worldPos.applyMatrix3(this.deps.transformState.equatorialToThree);
        
        // Avaluar altitud i visibilitat fotomètrica real (Pas 7)
        // Altitud: asin(world.y / radius)
        const altitudeDeg = Math.asin(Math.max(-1.0, Math.min(1.0, _worldPos.y))) * (180.0 / Math.PI);
        const evalResult = StarVisibilityEvaluator.evaluate(mag, altitudeDeg, visibilityState, camera.position.y);
        
        if (!evalResult.visible) {
          continue; // Invisible fotomètricament
        }
        
        // Reescalar la posició a l'esfera
        _worldPos.multiplyScalar(SKY_RADIUS);

        // Afegir offset celestialRoot (centrat a camera)
        _worldPos.add(camera.position);

        // Projectar a screen
        _screenPos.copy(_worldPos).project(camera);

        // Verificar que està davant la càmera
        if (_screenPos.z > 1 || _screenPos.z < -1) continue;

        // NDC → CSS px
        const screenX = ((_screenPos.x + 1) / 2) * rect.width;
        const screenY = ((1 - _screenPos.y) / 2) * rect.height;

        // Verificar que està dins del viewport
        if (screenX < -50 || screenX > rect.width + 50 ||
            screenY < -50 || screenY > rect.height + 50) continue;

        // Distància screen-space (CSS px)
        const dx = localX - screenX;
        const dy = localY - screenY;
        const dist = Math.sqrt(dx * dx + dy * dy);

        // Mida visual i hit radius
        const visualRadius = computeStarVisualRadiusCssPx(mag, pointScale, dpr);
        const hitRadius = computeStarHitRadiusCssPx(mag, pointScale, dpr);

        if (dist > hitRadius) continue;

        // Normalitzar distància pel hit radius
        const normalizedDist = dist / hitRadius;

        candidates.push({
          ref: {
            resourceId: resId,
            resourceVersion: entry.version,
            catalogIndex,
          },
          screenDistCssPx: dist,
          visualRadiusCssPx: visualRadius,
          hitRadiusCssPx: hitRadius,
          normalizedDist,
          magnitude: mag,
          rolePriority: ROLE_PRIORITY[entry.role] ?? 99,
          screenXCssPx: screenX,
          screenYCssPx: screenY,
        });
      }
    }

    this._candidateCounts.push(totalCandidates);
    if (this._candidateCounts.length > 1000) this._candidateCounts.shift();

    // 7. Worldroot occlusion check (star behind opaque world geometry)
    // Només si hi ha candidats
    if (candidates.length > 0) {
      this.filterOccluded(candidates, camera);
    }

    // 8. Ranking determinista
    if (candidates.length === 0) {
      this._missCount++;
      const elapsed = performance.now() - t0;
      this._queryTimesMs.push(elapsed);
      if (this._queryTimesMs.length > 1000) this._queryTimesMs.shift();
      return null;
    }

    candidates.sort((a, b) => {
      // 1. Menor distància normalitzada
      if (Math.abs(a.normalizedDist - b.normalizedDist) > 0.001) {
        return a.normalizedDist - b.normalizedDist;
      }
      // 2. Més brillant (menor magnitud)
      if (Math.abs(a.magnitude - b.magnitude) > 0.01) {
        return a.magnitude - b.magnitude;
      }
      // 3. Prioritat de recurs
      if (a.rolePriority !== b.rolePriority) {
        return a.rolePriority - b.rolePriority;
      }
      // 4. Clau estable
      const refCmp = a.ref.resourceId.localeCompare(b.ref.resourceId);
      if (refCmp !== 0) return refCmp;
      return a.ref.catalogIndex - b.ref.catalogIndex;
    });

    const winner = candidates[0]!;
    this._hitCount++;
    const elapsed = performance.now() - t0;
    this._queryTimesMs.push(elapsed);
    if (this._queryTimesMs.length > 1000) this._queryTimesMs.shift();

    return {
      kind: "star",
      ref: winner.ref,
      screenXCssPx: winner.screenXCssPx,
      screenYCssPx: winner.screenYCssPx,
      screenDistanceCssPx: winner.screenDistCssPx,
      visualRadiusCssPx: winner.visualRadiusCssPx,
      hitRadiusCssPx: winner.hitRadiusCssPx,
      magnitude: winner.magnitude,
    };
  }

  /**
   * Reproyecta una estrella seleccionada a screen-space.
   * Retorna null si no és visible (darrere càmera, fora viewport, etc.)
   */
  reprojectRef(ref: StarPickRef): { x: number; y: number } | null {
    if (!this.deps.transformState.isValid) return null;

    const resources = this.deps.getStarResources();
    const entry = resources.get(ref.resourceId);
    if (!entry || entry.version !== ref.resourceVersion) return null;

    // Trobar l'índex dins del buffer per catalogIndex
    // catalogIndex == array index (generat seqüencialment)
    const idx = this.findArrayIndexByCatalogIndex(entry, ref.catalogIndex);
    if (idx < 0) return null;

    const camera = this.deps.camera;
    const rect = this.deps.renderer.domElement.getBoundingClientRect();

    const eqX = entry.equatorialPositions[idx * 3];
    const eqY = entry.equatorialPositions[idx * 3 + 1];
    const eqZ = entry.equatorialPositions[idx * 3 + 2];
    if (eqX === undefined || eqY === undefined || eqZ === undefined) return null;

    _worldPos.set(eqX, eqY, eqZ);
    _worldPos.applyMatrix3(this.deps.transformState.equatorialToThree);
    _worldPos.multiplyScalar(SKY_RADIUS);
    _worldPos.add(camera.position);

    _screenPos.copy(_worldPos).project(camera);

    if (_screenPos.z > 1 || _screenPos.z < -1) return null;

    const screenX = ((_screenPos.x + 1) / 2) * rect.width;
    const screenY = ((1 - _screenPos.y) / 2) * rect.height;

    if (screenX < -50 || screenX > rect.width + 50 ||
        screenY < -50 || screenY > rect.height + 50) return null;

    return { x: screenX, y: screenY };
  }

  /**
   * Retorna mètriques de rendiment del picking.
   */
  getMetrics(): {
    queryCount: number;
    hitCount: number;
    missCount: number;
    p50Ms: number;
    p95Ms: number;
    maxMs: number;
    candidateP50: number;
    candidateP95: number;
  } {
    return {
      queryCount: this._queryCount,
      hitCount: this._hitCount,
      missCount: this._missCount,
      p50Ms: percentile(this._queryTimesMs, 50),
      p95Ms: percentile(this._queryTimesMs, 95),
      maxMs: this._queryTimesMs.length > 0 ? Math.max(...this._queryTimesMs) : 0,
      candidateP50: percentile(this._candidateCounts, 50),
      candidateP95: percentile(this._candidateCounts, 95),
    };
  }

  dispose(): void {
    for (const index of this.spatialIndices.values()) {
      index.dispose();
    }
    this.spatialIndices.clear();
  }

  // ─── Private ──────────────────────────────────────────────────────

  /**
   * Calcula el radi angular de consulta a partir del viewport i la mida de hit.
   */
  private computeQueryAngleRad(
    ndcX: number,
    ndcY: number,
    maxHitCssPx: number,
    viewportW: number,
    viewportH: number,
    camera: THREE.PerspectiveCamera,
  ): number {
    // Ray al pointer
    const r0 = new THREE.Vector2(ndcX, ndcY);
    _raycaster.setFromCamera(r0, camera);
    const dir0 = _raycaster.ray.direction.clone().normalize();

    // Ray al punt desplaçat per maxHitCssPx
    const offsetNdcX = ndcX + (maxHitCssPx / viewportW) * 2;
    const r1 = new THREE.Vector2(offsetNdcX, ndcY);
    _raycaster.setFromCamera(r1, camera);
    const dir1 = _raycaster.ray.direction.clone().normalize();

    const angle = Math.acos(Math.min(1, dir0.dot(dir1)));

    // Marge de seguretat
    return Math.max(angle * 1.5, 0.01);
  }

  /**
   * Filtra candidats ocults per geometria opaca del worldRoot.
   */
  private filterOccluded(
    candidates: ScoredCandidate[],
    camera: THREE.PerspectiveCamera,
  ): void {
    const worldRoot = this.deps.worldRoot;
    if (!worldRoot || worldRoot.children.length === 0) return;

    // Recollir objectes que oclouen (meshes opaques del worldRoot)
    const occluders: THREE.Object3D[] = [];
    worldRoot.traverse((obj) => {
      if (obj instanceof THREE.Mesh && obj.visible) {
        // Només objectes marcats o meshes opaques per defecte
        if (obj.userData.occludesCelestialPicking !== false) {
          occluders.push(obj);
        }
      }
    });

    if (occluders.length === 0) return;

    // Per cada candidat, verificar si hi ha un occluder entre la càmera i el cel
    const occlusionRaycaster = new THREE.Raycaster();
    for (let i = candidates.length - 1; i >= 0; i--) {
      const c = candidates[i];
      if (c === undefined) continue;

      // Reconstruir la posició visual de l'estrella
      const entry = this.deps.getStarResources().get(c.ref.resourceId);
      if (!entry) { candidates.splice(i, 1); continue; }

      const idx = this.findArrayIndexByCatalogIndex(entry, c.ref.catalogIndex);
      if (idx < 0) { candidates.splice(i, 1); continue; }

      const eqX = entry.equatorialPositions[idx * 3];
      const eqY = entry.equatorialPositions[idx * 3 + 1];
      const eqZ = entry.equatorialPositions[idx * 3 + 2];
      if (eqX === undefined || eqY === undefined || eqZ === undefined) {
        candidates.splice(i, 1);
        continue;
      }

      _worldPos.set(eqX, eqY, eqZ);
      _worldPos.applyMatrix3(this.deps.transformState.equatorialToThree);
      _worldPos.multiplyScalar(SKY_RADIUS);
      _worldPos.add(camera.position);

      // Ray des de la càmera cap a l'estrella
      const dir = _worldPos.clone().sub(camera.position).normalize();
      occlusionRaycaster.set(camera.position, dir);
      occlusionRaycaster.far = SKY_RADIUS + 100;

      const hits = occlusionRaycaster.intersectObjects(occluders, true);
      if (hits[0]?.distance !== undefined && hits[0].distance < SKY_RADIUS) {
        // L'estrella està darrere d'un objecte opac
        candidates.splice(i, 1);
      }
    }
  }

  /**
   * Troba l'índex de l'array per un catalogIndex donat.
   * Com que els catalogIndices són seqüencials (0..N-1), l'índex == catalogIndex.
   */
  private findArrayIndexByCatalogIndex(
    entry: StarResourceEntry,
    catalogIndex: number,
  ): number {
    if (catalogIndex < 0 || catalogIndex >= entry.starCount) return -1;
    // Verify: the catalogIndices array at this position should match
    if (entry.catalogIndices[catalogIndex] !== catalogIndex) {
      // Search linearly only if mismatch (shouldn't happen with current data)
      for (let i = 0; i < entry.starCount; i++) {
        if (entry.catalogIndices[i] === catalogIndex) return i;
      }
      return -1;
    }
    return catalogIndex;
  }
}

// ─── Helpers ──────────────────────────────────────────────────────────

function percentile(arr: number[], p: number): number {
  if (arr.length === 0) return 0;
  const sorted = [...arr].sort((a, b) => a - b);
  const idx = Math.floor((p / 100) * sorted.length);
  return sorted[Math.min(idx, sorted.length - 1)]!;
}
