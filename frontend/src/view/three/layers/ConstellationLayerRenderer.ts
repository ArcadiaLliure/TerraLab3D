import * as THREE from "three";
import { Line2 } from "three/addons/lines/Line2.js";
import { LineGeometry } from "three/addons/lines/LineGeometry.js";
import type {
  ConstellationCatalogEntrySnapshot,
  ConstellationCatalogSnapshot,
  ConstellationDocumentSnapshot,
  EquatorialPoint,
  UserConstellationSnapshot,
} from "../../../contracts/constellation_contracts";
import { CELESTIAL_SCENE_RADIUS } from "../celestialScenePolicy";
import {
  createOverlayLineMaterials,
  disposeOverlayLineMaterials,
  OVERLAY_LINE_PROFILES,
  setOverlayResolution,
  type OverlayLineMaterials,
} from "../materials/OverlayLineStyle";

interface RetainedEntity {
  readonly root: THREE.Group;
  readonly version: number;
}

export interface ConstellationRendererMetrics {
  readonly catalogBuildCount: number;
  readonly userBuildCount: number;
  readonly disposeCount: number;
  readonly catalogEntities: number;
  readonly userEntities: number;
  readonly activeMaterialCount: number;
}

export interface ConstellationGeometryHit {
  readonly entry: ConstellationCatalogEntrySnapshot;
  readonly screenXCssPx: number;
  readonly screenYCssPx: number;
  readonly screenDistanceCssPx: number;
  readonly hitRadiusCssPx: number;
}

/** Renderer retingut; no calcula astronomia ni reconstrueix geometria als ticks. */
export class ConstellationLayerRendererImpl {
  readonly root = new THREE.Group();
  private readonly catalogRoot = new THREE.Group();
  private readonly userRoot = new THREE.Group();
  private readonly catalogMaterials = createOverlayLineMaterials(OVERLAY_LINE_PROFILES.constellationCatalog);
  private readonly selectedMaterials = createOverlayLineMaterials(OVERLAY_LINE_PROFILES.constellationSelected);
  private readonly userMaterials = createOverlayLineMaterials(OVERLAY_LINE_PROFILES.constellationUser);
  private readonly catalogEntities = new Map<string, RetainedEntity>();
  private readonly catalogEntries = new Map<string, ConstellationCatalogEntrySnapshot>();
  private readonly userEntities = new Map<string, RetainedEntity>();
  private catalogVersion: string | null = null;
  private showAll = false;
  private selectedCatalogId: string | null = null;
  private _catalogBuildCount = 0;
  private _userBuildCount = 0;
  private _disposeCount = 0;

  constructor(parent: THREE.Object3D) {
    this.root.name = "constellations";
    this.catalogRoot.name = "constellations:catalog";
    this.userRoot.name = "constellations:user";
    this.root.add(this.catalogRoot, this.userRoot);
    parent.add(this.root);
  }

  presentCatalog(snapshot: ConstellationCatalogSnapshot): void {
    if (this.catalogVersion === snapshot.catalogVersion) return;
    for (const retained of this.catalogEntities.values()) this.disposeEntity(retained.root);
    this.catalogEntities.clear();
    this.catalogEntries.clear();
    this.catalogRoot.clear();
    for (const entry of snapshot.constellations) {
      const entity = this.buildCatalogEntity(entry);
      this.catalogEntities.set(entry.id, { root: entity, version: 1 });
      this.catalogEntries.set(entry.id, entry);
      this.catalogRoot.add(entity);
      this._catalogBuildCount++;
    }
    this.catalogVersion = snapshot.catalogVersion;
    this.syncCatalogVisibility();
  }

  presentDocument(snapshot: ConstellationDocumentSnapshot): void {
    const active = new Set(snapshot.constellations.map(item => item.constellationId));
    for (const [id, retained] of this.userEntities) {
      if (!active.has(id)) {
        this.userEntities.delete(id);
        retained.root.removeFromParent();
        this.disposeEntity(retained.root);
      }
    }
    for (const item of snapshot.constellations) {
      const retained = this.userEntities.get(item.constellationId);
      if (retained?.version === item.entityVersion) continue;
      if (retained) {
        retained.root.removeFromParent();
        this.disposeEntity(retained.root);
      }
      const root = this.buildUserEntity(item);
      this.userEntities.set(item.constellationId, { root, version: item.entityVersion });
      this.userRoot.add(root);
      this._userBuildCount++;
    }
  }

  setShowAll(visible: boolean): void {
    this.showAll = visible;
    this.syncCatalogVisibility();
  }

  setSelectedCatalog(constellationId: string | null): void {
    this.selectedCatalogId = constellationId;
    this.syncCatalogVisibility();
  }

  setVisible(visible: boolean): void { this.root.visible = visible; }

  pickCatalog(
    clientX: number,
    clientY: number,
    camera: THREE.PerspectiveCamera,
    viewport: DOMRect,
    hitRadiusCssPx = 10,
  ): ConstellationGeometryHit | null {
    if (!this.root.visible || viewport.width <= 0 || viewport.height <= 0) return null;
    camera.updateMatrixWorld(true);
    this.root.updateWorldMatrix(true, true);
    const ndc = new THREE.Vector2(
      ((clientX - viewport.left) / viewport.width) * 2 - 1,
      -((clientY - viewport.top) / viewport.height) * 2 + 1,
    );
    const raycaster = new THREE.Raycaster();
    raycaster.setFromCamera(ndc, camera);
    for (const materials of [this.catalogMaterials, this.selectedMaterials, this.userMaterials]) {
      setOverlayResolution(materials, viewport.width, viewport.height);
    }
    (raycaster.params as THREE.RaycasterParameters & { Line2?: { threshold: number } }).Line2 = {
      threshold: hitRadiusCssPx * 2,
    };
    const distance = Math.max(1, camera.position.distanceTo(this.root.getWorldPosition(new THREE.Vector3())) + CELESTIAL_SCENE_RADIUS.distantSky);
    raycaster.params.Line = {
      threshold: 2 * distance * Math.tan(THREE.MathUtils.degToRad(camera.fov) / 2) * hitRadiusCssPx / viewport.height,
    };
    const visibleLines: Line2[] = [];
    for (const retained of this.catalogEntities.values()) {
      if (!retained.root.visible) continue;
      retained.root.traverse(object => {
        if (object instanceof Line2) visibleLines.push(object);
      });
    }
    const hit = raycaster.intersectObjects(visibleLines, false)[0];
    if (!hit) return null;
    let owner: THREE.Object3D | null = hit.object;
    while (owner && typeof owner.userData.constellationId !== "string") owner = owner.parent;
    const entry = owner ? this.catalogEntries.get(String(owner.userData.constellationId)) : undefined;
    if (!entry) return null;
    const projected = hit.point.clone().project(camera);
    const screenXCssPx = (projected.x + 1) * viewport.width / 2;
    const screenYCssPx = (1 - projected.y) * viewport.height / 2;
    return {
      entry,
      screenXCssPx,
      screenYCssPx,
      screenDistanceCssPx: Math.hypot(
        clientX - viewport.left - screenXCssPx,
        clientY - viewport.top - screenYCssPx,
      ),
      hitRadiusCssPx,
    };
  }

  reprojectCatalog(
    constellationId: string,
    camera: THREE.Camera,
    viewport: DOMRect,
  ): { x: number; y: number } | null {
    const entry = this.catalogEntries.get(constellationId);
    const retained = this.catalogEntities.get(constellationId);
    if (!entry || !retained?.root.visible || viewport.width <= 0 || viewport.height <= 0) return null;
    camera.updateMatrixWorld(true);
    this.root.updateWorldMatrix(true, true);
    const point = this.position(entry.center[0], entry.center[1], CELESTIAL_SCENE_RADIUS.distantSky * 0.985)
      .applyMatrix4(this.root.matrixWorld)
      .project(camera);
    if (point.z < -1 || point.z > 1) return null;
    return {
      x: (point.x + 1) * viewport.width / 2,
      y: (1 - point.y) * viewport.height / 2,
    };
  }

  metrics(): ConstellationRendererMetrics {
    return {
      catalogBuildCount: this._catalogBuildCount,
      userBuildCount: this._userBuildCount,
      disposeCount: this._disposeCount,
      catalogEntities: this.catalogEntities.size,
      userEntities: this.userEntities.size,
      activeMaterialCount: 6,
    };
  }

  dispose(): void {
    for (const retained of this.catalogEntities.values()) this.disposeEntity(retained.root);
    for (const retained of this.userEntities.values()) this.disposeEntity(retained.root);
    this.catalogEntities.clear();
    this.catalogEntries.clear();
    this.userEntities.clear();
    disposeOverlayLineMaterials(this.catalogMaterials);
    disposeOverlayLineMaterials(this.selectedMaterials);
    disposeOverlayLineMaterials(this.userMaterials);
    this.root.removeFromParent();
  }

  private buildCatalogEntity(entry: ConstellationCatalogEntrySnapshot): THREE.Group {
    const root = new THREE.Group();
    root.name = `constellation:catalog:${entry.id}`;
    root.userData.constellationId = entry.id;
    for (const component of entry.visualComponents) {
      for (const stroke of component.strokes) {
        if (stroke.length < 2) continue;
        root.add(this.line(stroke.map(point => ({ raDeg: point[0], decDeg: point[1] })), this.catalogMaterials));
      }
    }
    const label = this.buildLabel(entry.name, entry.center[0], entry.center[1], "#a9bde8");
    if (label) root.add(label);
    return root;
  }

  private buildUserEntity(entry: UserConstellationSnapshot): THREE.Group {
    const root = new THREE.Group();
    root.name = `constellation:user:${entry.constellationId}`;
    root.userData.constellationId = entry.constellationId;
    for (const stroke of entry.strokes) {
      if (stroke.length >= 2) root.add(this.line(stroke, this.userMaterials));
    }
    const points = entry.strokes.flat();
    if (points.length > 0) {
      const direction = points.reduce(
        (sum, point) => sum.add(this.position(point.raDeg, point.decDeg, 1)),
        new THREE.Vector3(),
      ).normalize();
      const raDeg = THREE.MathUtils.radToDeg(Math.atan2(direction.y, direction.x) + Math.PI * 2) % 360;
      const decDeg = THREE.MathUtils.radToDeg(Math.asin(THREE.MathUtils.clamp(direction.z, -1, 1)));
      const label = this.buildLabel(entry.name, raDeg, decDeg, "#74d7c4");
      if (label) root.add(label);
    }
    return root;
  }

  private line(points: readonly EquatorialPoint[], materials: OverlayLineMaterials): THREE.Group {
    const values = new Float32Array(points.length * 3);
    points.forEach((point, index) => {
      const radius = CELESTIAL_SCENE_RADIUS.distantSky * 0.985;
      const position = this.position(point.raDeg, point.decDeg, radius);
      values[index * 3] = position.x;
      values[index * 3 + 1] = position.y;
      values[index * 3 + 2] = position.z;
    });
    const geometry = new LineGeometry();
    geometry.setPositions(values);
    const halo = new Line2(geometry, materials.halo);
    halo.name = "constellation:stroke:halo";
    halo.userData.overlayLineLayer = "halo";
    halo.frustumCulled = false;
    halo.renderOrder = -621;
    const core = new Line2(geometry, materials.core);
    core.name = "constellation:stroke:core";
    core.userData.overlayLineLayer = "core";
    core.frustumCulled = false;
    core.renderOrder = -620;
    const visual = new THREE.Group();
    visual.name = "constellation:stroke";
    visual.add(halo, core);
    return visual;
  }

  private position(raDeg: number, decDeg: number, radius: number): THREE.Vector3 {
    const ra = THREE.MathUtils.degToRad(raDeg);
    const dec = THREE.MathUtils.degToRad(decDeg);
    return new THREE.Vector3(
      Math.cos(dec) * Math.cos(ra) * radius,
      Math.cos(dec) * Math.sin(ra) * radius,
      Math.sin(dec) * radius,
    );
  }

  private buildLabel(text: string, raDeg: number, decDeg: number, color: string): THREE.Sprite | null {
    if (typeof document === "undefined") return null;
    const canvas = document.createElement("canvas");
    canvas.width = 384;
    canvas.height = 72;
    const context = canvas.getContext("2d");
    if (!context) return null;
    context.clearRect(0, 0, canvas.width, canvas.height);
    context.font = "500 30px system-ui, sans-serif";
    context.textAlign = "center";
    context.textBaseline = "middle";
    context.lineWidth = 6;
    context.strokeStyle = "rgba(2, 4, 10, 0.92)";
    context.strokeText(text, canvas.width / 2, canvas.height / 2);
    context.fillStyle = color;
    context.fillText(text, canvas.width / 2, canvas.height / 2);
    const texture = new THREE.CanvasTexture(canvas);
    texture.colorSpace = THREE.SRGBColorSpace;
    texture.minFilter = THREE.LinearFilter;
    const material = new THREE.SpriteMaterial({
      map: texture,
      transparent: true,
      depthTest: false,
      depthWrite: false,
      sizeAttenuation: false,
    });
    const sprite = new THREE.Sprite(material);
    sprite.name = "constellation:label";
    sprite.position.copy(this.position(raDeg, decDeg, CELESTIAL_SCENE_RADIUS.distantSky * 0.975));
    sprite.scale.set(0.22, 0.04125, 1);
    sprite.renderOrder = -610;
    return sprite;
  }

  private syncCatalogVisibility(): void {
    for (const [id, retained] of this.catalogEntities) {
      const selected = id === this.selectedCatalogId;
      retained.root.visible = this.showAll || selected;
      const materials = selected ? this.selectedMaterials : this.catalogMaterials;
      retained.root.traverse(object => {
        if (!(object instanceof Line2)) return;
        object.material = object.userData.overlayLineLayer === "halo" ? materials.halo : materials.core;
      });
    }
  }

  private disposeEntity(root: THREE.Object3D): void {
    const geometries = new Set<THREE.BufferGeometry>();
    root.traverse(object => {
      if (object instanceof Line2 && !geometries.has(object.geometry)) {
        geometries.add(object.geometry);
        object.geometry.dispose();
        this._disposeCount++;
      } else if (object instanceof THREE.Sprite) {
        const materials = Array.isArray(object.material) ? object.material : [object.material];
        for (const material of materials) {
          material.map?.dispose();
          material.dispose();
          this._disposeCount++;
        }
      }
    });
  }
}
