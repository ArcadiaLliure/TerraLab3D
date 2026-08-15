/**
 * NavigationWorld — manages the preloaded navigable zone and its terrain.
 *
 * Responsibilities:
 *   - Build and manage the technical terrain mesh (hills, valleys, slopes).
 *   - Place reference objects at various distances for parallax demo.
 *   - Own and expose a TerrainSampler (via getTerrainSampler()).
 *   - Track NavigationEnvelope readiness states.
 *   - Enforce horizontal/vertical bounds.
 *
 * The terrain mesh lives inside the worldRoot provided by ThreeSceneHostImpl.
 */

import * as THREE from "three";
import type { TerrainSampler } from "../../../contracts/TerrainSampler";
import type { NavigationEnvelope, NavigationReadiness } from "../../../contracts/navigation";
import type { TerrainNavigationSampling } from "./TechnicalTerrainSampler";
import {
  LayeredTerrainSampler,
  type TerrainDetailLayer,
} from "./LayeredTerrainSampler";
import { PBRMaterialPolicy } from "../materials/PBRMaterialPolicy";

const TERRAIN_SIZE = 500;        // ±500m → 1000×1000m total
const TERRAIN_SEGMENTS = 128;    // 128×128 grid
const BOUNDS_RADIUS = 500;       // metres horizontal
const MAX_ALTITUDE = 500;        // metres vertical

const LOG_PREFIX = "MGP: [NavigationWorld]";

export class NavigationWorld {
  private readonly sampler: LayeredTerrainSampler;
  private readonly materialPolicy = new PBRMaterialPolicy();
  private terrainMesh: THREE.Mesh | null = null;
  private terrainGroup: THREE.Group;
  private referenceObjects: THREE.Group;
  private boundsIndicator: THREE.LineLoop | null = null;
  private technicalPresentationVisible = true;
  private _envelope: NavigationEnvelope;
  private disposed = false;

  constructor() {
    this.sampler = new LayeredTerrainSampler();
    this.terrainGroup = new THREE.Group();
    this.terrainGroup.name = "terrain";
    this.referenceObjects = new THREE.Group();
    this.referenceObjects.name = "localReferenceObjects";

    this._envelope = {
      centerEastM: 0,
      centerNorthM: 0,
      minimumUpM: 0,
      maximumUpM: MAX_ALTITUDE,
      horizontalRadiusM: BOUNDS_RADIUS,
      readiness: "empty",
      generation: 0,
    };
  }

  get envelope(): Readonly<NavigationEnvelope> {
    return this._envelope;
  }

  /** Returns the TerrainSampler interface — consumers never see the concrete class. */
  getTerrainSampler(): TerrainSampler {
    return this.sampler;
  }

  /**
   * Make collision use the same observer-relative DEM geometry that is drawn.
   * The synthetic patch remains only as the startup fallback before DEM data
   * is available or after it is explicitly cleared.
   */
  setDemTerrainMesh(
    mesh: THREE.Mesh | null,
    sampling?: TerrainNavigationSampling | null,
  ): void {
    const collisionMesh = mesh ?? this.terrainMesh;
    if (!collisionMesh) return;
    this.sampler.setBaseTerrain(collisionMesh, sampling);
  }

  /** Keep a moving high-detail DEM chunk over the persistent wide mesh. */
  setStreamingDemTerrainMesh(
    mesh: THREE.Mesh | null,
    sampling?: TerrainNavigationSampling | null,
  ): void {
    this.sampler.setDetailTerrain(mesh, sampling);
  }

  /** Keep collision aligned with every DEM detail chunk retained by render. */
  setStreamingDemTerrainMeshes(layers: readonly TerrainDetailLayer[]): void {
    this.sampler.setDetailTerrains(layers);
  }

  metrics(): {
    readonly pbrMaterialBuildCount: number;
    readonly technicalPresentationVisible: boolean;
  } {
    return {
      pbrMaterialBuildCount: this.materialPolicy.metrics().materialBuildCount,
      technicalPresentationVisible: this.technicalPresentationVisible,
    };
  }

  /**
   * Keep the synthetic mesh available to the navigation sampler without
   * presenting it as scientific terrain once a DEM-backed horizon is active.
   */
  setTechnicalPresentationVisible(visible: boolean): void {
    if (this.technicalPresentationVisible === visible) return;
    this.technicalPresentationVisible = visible;
    this.terrainGroup.visible = visible;
    this.referenceObjects.visible = visible;
    console.info(
      `${LOG_PREFIX} [setTechnicalPresentationVisible] `
      + `[Presentació tècnica ${visible ? "visible" : "oculta; perfil DEM actiu"}]`,
    );
  }

  /**
   * Build the technical terrain and reference objects.
   * Attaches them to the provided worldRoot group.
   */
  prepare(worldRoot: THREE.Group): void {
    if (this.disposed) return;
    this.setReadiness("loading");
    console.info(`${LOG_PREFIX} [prepare] [Construint terreny tècnic]`);

    try {
      this.buildTerrain();
      this.buildReferenceObjects();
      this.buildBoundsIndicator();

      worldRoot.add(this.terrainGroup);
      worldRoot.add(this.referenceObjects);
      if (this.boundsIndicator) worldRoot.add(this.boundsIndicator);

      this.setReadiness("world_ready");

      // Wire the sampler to the mesh
      if (this.terrainMesh) {
        this.sampler.setBaseTerrain(this.terrainMesh);
        this.setReadiness("collision_ready");
        this.setReadiness("navigation_ready");
        console.info(`${LOG_PREFIX} [prepare] [Zona navegable preparada generation=${this._envelope.generation}]`);
      }
    } catch (err) {
      console.error(`${LOG_PREFIX} [prepare] [Error construint terreny]`, err);
      this.setReadiness("error");
    }
  }

  /** Check if a position is within the navigable bounds. */
  isWithinBounds(eastM: number, northM: number, upM: number): boolean {
    const distSq = eastM * eastM + northM * northM;
    const radiusSq = BOUNDS_RADIUS * BOUNDS_RADIUS;
    return distSq <= radiusSq && upM >= 0 && upM <= MAX_ALTITUDE;
  }

  /** Clamp a position to within bounds. Returns clamped values. */
  clampToBounds(
    eastM: number,
    northM: number,
    upM: number,
  ): { eastM: number; northM: number; upM: number; clamped: boolean } {
    let clamped = false;
    const dist = Math.sqrt(eastM * eastM + northM * northM);
    let e = eastM;
    let n = northM;
    let u = upM;

    if (dist > BOUNDS_RADIUS && dist > 0) {
      const scale = BOUNDS_RADIUS / dist;
      e = eastM * scale;
      n = northM * scale;
      clamped = true;
    }

    if (u < 0) { u = 0; clamped = true; }
    if (u > MAX_ALTITUDE) { u = MAX_ALTITUDE; clamped = true; }

    return { eastM: e, northM: n, upM: u, clamped };
  }

  dispose(): void {
    if (this.disposed) return;
    this.disposed = true;

    this.terrainGroup.traverse((obj) => {
      if (obj instanceof THREE.Mesh) {
        obj.geometry.dispose();
      }
    });
    this.referenceObjects.traverse((obj) => {
      if (obj instanceof THREE.Mesh) {
        obj.geometry.dispose();
      }
    });
    if (this.boundsIndicator) {
      this.boundsIndicator.geometry.dispose();
      (this.boundsIndicator.material as THREE.Material).dispose();
    }

    this.terrainGroup.removeFromParent();
    this.referenceObjects.removeFromParent();
    this.boundsIndicator?.removeFromParent();
    this.materialPolicy.dispose();
  }

  // ─── Private: Terrain ──────────────────────────────────────────────

  private buildTerrain(): void {
    const geo = new THREE.PlaneGeometry(
      TERRAIN_SIZE * 2,
      TERRAIN_SIZE * 2,
      TERRAIN_SEGMENTS,
      TERRAIN_SEGMENTS,
    );

    // Rotate to XZ plane (Y = up)
    geo.rotateX(-Math.PI / 2);

    const positions = geo.attributes.position;
    if (positions) {
      const count = positions.count;

      for (let i = 0; i < count; i++) {
        const x = positions.getX(i);
        const z = positions.getZ(i);

        // Generate interesting topography with multiple octaves
        const height = this.terrainHeight(x, -z); // -z because Three.js Z is south
        positions.setY(i, height);
      }
    }

    geo.computeVertexNormals();

    this.terrainMesh = new THREE.Mesh(geo, this.materialPolicy.terrain);
    this.terrainMesh.name = "technical_terrain_mesh";
    this.terrainMesh.receiveShadow = true;

    this.terrainGroup.add(this.terrainMesh);
  }

  /**
   * Height function with multiple octaves of sinusoidal terrain.
   * Produces hills, valleys, ridges, and flat areas.
   * @param eastM  East coordinate (Three.js +X)
   * @param northM North coordinate (ENU north)
   */
  private terrainHeight(eastM: number, northM: number): number {
    // Large rolling hills
    let h = 12 * Math.sin(eastM * 0.008) * Math.cos(northM * 0.006);

    // Medium undulations
    h += 6 * Math.sin(eastM * 0.025 + 1.3) * Math.sin(northM * 0.02 - 0.7);

    // Ridge line running roughly NE-SW
    h += 8 * Math.exp(-0.0001 * Math.pow(eastM - northM * 0.5, 2));

    // Valley
    h -= 5 * Math.exp(-0.0002 * (eastM + 100) * (eastM + 100) - 0.0002 * northM * northM);

    // Small noise
    h += 1.5 * Math.sin(eastM * 0.07 + 2.1) * Math.cos(northM * 0.09 - 0.3);
    h += 0.8 * Math.sin(eastM * 0.15 - 1.2) * Math.sin(northM * 0.13 + 0.9);

    // Steep cliff area around east=200
    if (eastM > 180 && eastM < 220) {
      const cliffFactor = 1 - Math.abs(eastM - 200) / 20;
      h += 25 * cliffFactor;
    }

    // Ensure origin area is relatively flat for comfortable starting
    const distFromOrigin = Math.sqrt(eastM * eastM + northM * northM);
    if (distFromOrigin < 30) {
      const flatFactor = 1 - distFromOrigin / 30;
      h = h * (1 - flatFactor * 0.8);
    }

    return h;
  }

  // ─── Private: Reference Objects ────────────────────────────────────

  private buildReferenceObjects(): void {
    const cubeMat = this.materialPolicy.referenceBlue;
    const columnMat = this.materialPolicy.referenceOrange;

    // Near objects (10–30m)
    this.addCube(8, 0, -15, 1.5, cubeMat);
    this.addCube(-12, 0, -20, 2.0, cubeMat);

    // Mid-range objects (50–150m)
    this.addColumn(50, -80, 4, 15, columnMat);
    this.addColumn(-70, -50, 3, 12, columnMat);
    this.addCube(100, 0, -120, 5, cubeMat);

    // Far objects (200–400m)
    this.addColumn(250, -200, 8, 30, columnMat);
    this.addColumn(-300, -150, 6, 25, columnMat);
    this.addCube(200, 0, -350, 10, cubeMat);
  }

  private addCube(
    eastM: number,
    _unused: number,
    zThree: number,
    size: number,
    material: THREE.Material,
  ): void {
    // Get the terrain height at this position for proper placement
    const northM = -zThree;
    const groundH = this.terrainHeight(eastM, northM);
    const geo = new THREE.BoxGeometry(size, size, size);
    const mesh = new THREE.Mesh(geo, material);
    mesh.name = "localReferenceCube";
    mesh.position.set(eastM, groundH + size / 2, zThree);
    mesh.castShadow = true;
    this.referenceObjects.add(mesh);
  }

  private addColumn(
    eastM: number,
    zThree: number,
    radius: number,
    height: number,
    material: THREE.Material,
  ): void {
    const northM = -zThree;
    const groundH = this.terrainHeight(eastM, northM);
    const geo = new THREE.CylinderGeometry(radius, radius, height, 12);
    const mesh = new THREE.Mesh(geo, material);
    mesh.name = "localReferenceColumn";
    mesh.position.set(eastM, groundH + height / 2, zThree);
    mesh.castShadow = true;
    this.referenceObjects.add(mesh);
  }

  // ─── Private: Bounds Indicator ─────────────────────────────────────

  private buildBoundsIndicator(): void {
    const segments = 128;
    const verts = new Float32Array((segments + 1) * 3);
    for (let i = 0; i <= segments; i++) {
      const theta = (i / segments) * Math.PI * 2;
      const eastM = Math.sin(theta) * BOUNDS_RADIUS;
      const northM = Math.cos(theta) * BOUNDS_RADIUS;
      const groundH = this.terrainHeight(eastM, northM);
      verts[i * 3] = eastM;
      verts[i * 3 + 1] = groundH + 0.5; // Follows local terrain height + 0.5m
      verts[i * 3 + 2] = -northM;
    }
    const geo = new THREE.BufferGeometry();
    geo.setAttribute("position", new THREE.BufferAttribute(verts, 3));
    const mat = new THREE.LineBasicMaterial({
      color: 0xff4444,
      transparent: true,
      opacity: 0.3,
    });
    this.boundsIndicator = new THREE.LineLoop(geo, mat);
    this.boundsIndicator.name = "navigationBounds";
    this.boundsIndicator.visible = false;
  }

  setBoundsVisible(visible: boolean): void {
    if (this.boundsIndicator) {
      this.boundsIndicator.visible = visible;
    }
  }

  // ─── Private: Readiness ────────────────────────────────────────────

  private setReadiness(readiness: NavigationReadiness): void {
    this._envelope = { ...this._envelope, readiness, generation: this._envelope.generation + 1 };
  }
}
