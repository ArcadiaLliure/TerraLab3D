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
import type { TerrainSampler } from "../../contracts/TerrainSampler";
import type { NavigationEnvelope, NavigationReadiness } from "../../contracts/navigation";
import { TechnicalTerrainSampler } from "./TechnicalTerrainSampler";

const TERRAIN_SIZE = 500;        // ±500m → 1000×1000m total
const TERRAIN_SEGMENTS = 128;    // 128×128 grid
const BOUNDS_RADIUS = 500;       // metres horizontal
const MAX_ALTITUDE = 500;        // metres vertical

const LOG_PREFIX = "MGP: [NavigationWorld]";

export class NavigationWorld {
  private readonly sampler: TechnicalTerrainSampler;
  private terrainMesh: THREE.Mesh | null = null;
  private terrainGroup: THREE.Group;
  private referenceObjects: THREE.Group;
  private boundsIndicator: THREE.LineLoop | null = null;
  private _envelope: NavigationEnvelope;
  private disposed = false;

  constructor() {
    this.sampler = new TechnicalTerrainSampler();
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
        this.sampler.setTerrainMesh(this.terrainMesh);
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
        if (Array.isArray(obj.material)) {
          obj.material.forEach((m) => m.dispose());
        } else {
          obj.material.dispose();
        }
      }
    });
    this.referenceObjects.traverse((obj) => {
      if (obj instanceof THREE.Mesh) {
        obj.geometry.dispose();
        if (Array.isArray(obj.material)) {
          obj.material.forEach((m) => m.dispose());
        } else {
          obj.material.dispose();
        }
      }
    });
    if (this.boundsIndicator) {
      this.boundsIndicator.geometry.dispose();
      (this.boundsIndicator.material as THREE.Material).dispose();
    }

    this.terrainGroup.removeFromParent();
    this.referenceObjects.removeFromParent();
    this.boundsIndicator?.removeFromParent();
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
    const count = positions.count;

    for (let i = 0; i < count; i++) {
      const x = positions.getX(i);
      const z = positions.getZ(i);

      // Generate interesting topography with multiple octaves
      const height = this.terrainHeight(x, -z); // -z because Three.js Z is south
      positions.setY(i, height);
    }

    geo.computeVertexNormals();

    const mat = new THREE.MeshStandardMaterial({
      color: 0x1a2a20,
      roughness: 0.9,
      metalness: 0.0,
      flatShading: true,
      side: THREE.DoubleSide,
    });

    this.terrainMesh = new THREE.Mesh(geo, mat);
    this.terrainMesh.name = "technical_terrain_mesh";
    this.terrainMesh.receiveShadow = true;

    // Simple ambient + directional light for the terrain
    const ambient = new THREE.AmbientLight(0x334455, 0.6);
    const directional = new THREE.DirectionalLight(0xffeedd, 0.8);
    directional.position.set(100, 200, -100);

    this.terrainGroup.add(this.terrainMesh);
    this.terrainGroup.add(ambient);
    this.terrainGroup.add(directional);
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
    const cubeMat = new THREE.MeshStandardMaterial({
      color: 0x4488aa,
      roughness: 0.4,
      metalness: 0.2,
    });
    const columnMat = new THREE.MeshStandardMaterial({
      color: 0xcc8844,
      roughness: 0.6,
      metalness: 0.1,
    });

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
      verts[i * 3] = Math.sin(theta) * BOUNDS_RADIUS;
      verts[i * 3 + 1] = 0.5; // Slightly above ground
      verts[i * 3 + 2] = Math.cos(theta) * BOUNDS_RADIUS;
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
  }

  // ─── Private: Readiness ────────────────────────────────────────────

  private setReadiness(readiness: NavigationReadiness): void {
    this._envelope = { ...this._envelope, readiness, generation: this._envelope.generation + 1 };
  }
}
