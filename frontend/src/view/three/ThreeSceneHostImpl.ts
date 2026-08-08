/**
 * Concrete Three.js scene host with celestialRoot / worldRoot / overlayRoot
 * separation for correct parallax behaviour (Phase 3.5 + Phase 4).
 *
 * World conventions:
 *   Y = up (Three.js native)
 *   North = -Z,  East = +X,  South = +Z,  West = -X
 *
 * Scene tree:
 *   scene
 *   ├── celestialRoot  (recentred to camera position → no translational parallax)
 *   │   ├── horizontalGridRoot   (azimut-altitud grid, fixed in ENU)
 *   │   ├── equatorialReferenceRoot (celestial equator, rotates with LST)
 *   │   └── celestialSphere      (meridians, rotates with LST — legacy)
 *   ├── worldRoot      (stays at origin → real parallax for terrain/objects)
 *   │   ├── terrain     (from NavigationWorld)
 *   │   ├── horizon
 *   │   ├── ground
 *   │   └── localReferenceObjects (from NavigationWorld)
 *   └── cameraRig / camera (managed by CameraRigImpl)
 *
 * Phase 4 additions:
 *   - HorizontalGrid with LOD (replaces old diagnostic sphere + altitude circles)
 *   - CelestialLabels (replaces old cardinal HTML labels)
 *   - CelestialEquator (TerraLab's equator curve)
 *   - Toggle API for grid/compass/labels
 *   - Metrics tracking
 */

import * as THREE from "three";
import { HorizontalGrid } from "./HorizontalGrid";
import { CelestialLabels } from "./CelestialLabels";
import { CelestialEquator } from "./CelestialEquator";
import { StarFieldRenderer } from "./StarFieldRenderer";

const LOG_PREFIX = "MGP: [ThreeSceneHost]";

const HORIZON_RADIUS = 100;
const HORIZON_SEGMENTS = 256;
const BACKGROUND_COLOR = 0x02040a;

/** Visibility state for overlay toggles. */
export interface OverlayVisibility {
  grid: boolean;
  compass: boolean;
  labels: boolean;
  equator: boolean;
  bounds: boolean;
  stars: boolean;
}

export class ThreeSceneHostImpl {
  readonly scene: THREE.Scene;
  readonly camera: THREE.PerspectiveCamera;
  readonly renderer: THREE.WebGLRenderer;

  // ─── Scene tree roots ──────────────────────────────────────────────
  private readonly celestialRoot: THREE.Group;
  private readonly worldRoot: THREE.Group;

  // ─── Phase 4 components ────────────────────────────────────────────
  private readonly horizontalGrid: HorizontalGrid;
  private readonly celestialLabels: CelestialLabels;
  private readonly celestialEquator: CelestialEquator;
  private readonly starFieldRenderer: StarFieldRenderer;

  // ─── Legacy celestial sphere (meridians that rotate with LST) ──────
  private readonly celestialSphere: THREE.Group;
  private targetLstRad = 0;
  private currentLstRad = 0;

  // ─── State ─────────────────────────────────────────────────────────
  private container: HTMLElement | null = null;
  private disposed = false;
  private currentFovDeg = 60;

  private navigationWorld: { setBoundsVisible(visible: boolean): void } | null = null;

  // ─── Overlay visibility ────────────────────────────────────────────
  private overlayVisibility: OverlayVisibility = {
    grid: true,
    compass: true,
    labels: true,
    equator: true,
    bounds: false,
    stars: true,
  };

  // ─── Metrics ───────────────────────────────────────────────────────
  private _transformUpdateCount = 0;
  get transformUpdateCount(): number { return this._transformUpdateCount; }

  constructor() {
    // Scene
    this.scene = new THREE.Scene();
    this.scene.background = new THREE.Color(BACKGROUND_COLOR);

    // ─── Scene tree roots ────────────────────────────────────────────
    this.celestialRoot = new THREE.Group();
    this.celestialRoot.name = "celestialRoot";
    this.scene.add(this.celestialRoot);

    this.worldRoot = new THREE.Group();
    this.worldRoot.name = "worldRoot";
    this.scene.add(this.worldRoot);

    // Camera (initial values; CameraRigImpl manages pose)
    this.camera = new THREE.PerspectiveCamera(60, 1, 0.01, 2000000);

    // Renderer
    this.renderer = new THREE.WebGLRenderer({ antialias: true });
    this.renderer.setPixelRatio(window.devicePixelRatio);

    // ─── Phase 5: Star Field Renderer ────────────────────────────────
    this.starFieldRenderer = new StarFieldRenderer();
    this.starFieldRenderer.attachToParent(this.celestialRoot);

    // ─── Phase 4: Horizontal Grid ────────────────────────────────────
    this.horizontalGrid = new HorizontalGrid();
    this.celestialRoot.add(this.horizontalGrid.root);

    // ─── Phase 4: Celestial Equator ──────────────────────────────────
    this.celestialEquator = new CelestialEquator();
    this.celestialRoot.add(this.celestialEquator.root);

    // ─── Phase 4: Celestial Labels ───────────────────────────────────
    this.celestialLabels = new CelestialLabels();

    // Phase 4: Horizontal grid (celestialRoot) replaces legacy horizon/ground rings

    // ─── Celestial Sphere (rotates with LST — legacy reference meridians) ──
    this.celestialSphere = new THREE.Group();
    this.celestialSphere.name = "celestialSphere_lstRotating";
    this.celestialRoot.add(this.celestialSphere);

    const meridianMat = new THREE.LineBasicMaterial({
      color: 0x556677,
      transparent: true,
      opacity: 0.15,
    });
    for (let i = 0; i < 12; i++) {
      const angle = (i / 12) * Math.PI;
      const geo = new THREE.BufferGeometry();
      const verts = new Float32Array((HORIZON_SEGMENTS + 1) * 3);
      for (let j = 0; j <= HORIZON_SEGMENTS; j++) {
        const theta = (j / HORIZON_SEGMENTS) * Math.PI * 2;
        verts[j * 3] = Math.cos(theta) * HORIZON_RADIUS * Math.cos(angle);
        verts[j * 3 + 1] = Math.sin(theta) * HORIZON_RADIUS;
        verts[j * 3 + 2] = Math.cos(theta) * HORIZON_RADIUS * Math.sin(angle);
      }
      geo.setAttribute("position", new THREE.BufferAttribute(verts, 3));
      this.celestialSphere.add(new THREE.LineLoop(geo, meridianMat));
    }

    console.info(`${LOG_PREFIX} [constructor] [Escena inicialitzada amb grid horitzontal, equador celeste i etiquetes]`);
  }

  // ─── Public access to roots ────────────────────────────────────────

  /** World root for terrain, objects, navigation bounds (shows parallax). */
  getWorldRoot(): THREE.Group {
    return this.worldRoot;
  }

  /** Celestial root for sky objects (no translational parallax). */
  getCelestialRoot(): THREE.Group {
    return this.celestialRoot;
  }

  /** Access the persistent star field renderer. */
  getStarFieldRenderer(): StarFieldRenderer {
    return this.starFieldRenderer;
  }

  mount(container: HTMLElement): void {
    this.container = container;
    const rect = container.getBoundingClientRect();
    this.renderer.setSize(rect.width, rect.height);
    container.appendChild(this.renderer.domElement);

    // Phase 4: Mount celestial labels
    this.celestialLabels.mount(container);
  }

  resize(widthPx: number, heightPx: number): void {
    this.renderer.setSize(widthPx, heightPx);
    this.renderer.setPixelRatio(window.devicePixelRatio);
    this.starFieldRenderer.updateViewport(window.devicePixelRatio);
  }

  render(timestampMs: number): void {
    if (this.disposed) return;

    // ─── Celestial rotation (legacy LST sphere) ──────────────────────
    const diff = this.targetLstRad - this.currentLstRad;
    let shortest = diff % (Math.PI * 2);
    if (shortest > Math.PI) shortest -= Math.PI * 2;
    if (shortest < -Math.PI) shortest += Math.PI * 2;
    this.currentLstRad += shortest * 0.1;
    this.celestialSphere.rotation.y = -this.currentLstRad;

    // ─── Recentre celestialRoot to camera position ───────────────────
    // This eliminates translational parallax for sky objects.
    this.celestialRoot.position.copy(this.camera.position);
    
    // Ancorar la línia de l'horitzó al terra (Y=0)
    this.horizontalGrid.root.position.y = -this.camera.position.y;
    
    // Ampliar dinàmicament el grid segons l'alçada perquè mantingui la dimensió visual
    const baseHeight = 50.0;
    const scale = Math.max(1.0, this.camera.position.y / baseHeight);
    this.horizontalGrid.root.scale.set(scale, scale, scale);
    
    this._transformUpdateCount++;

    // ─── Phase 4: LOD update based on current FOV ────────────────────
    this.horizontalGrid.updateLOD(this.currentFovDeg);

    // ─── Phase 4: Celestial equator update ───────────────────────────
    this.celestialEquator.update();

    // ─── Render ──────────────────────────────────────────────────────
    this.renderer.render(this.scene, this.camera);
  }

  /**
   * Update labels. Called at ~4 Hz from the render loop, not every frame.
   */
  updateLabels(): void {
    if (this.disposed) return;
    this.celestialLabels.update(this.camera, this.camera.position);
  }

  setSiderealTime(lstDeg: number): void {
    this.targetLstRad = THREE.MathUtils.degToRad(lstDeg);
    // Also update celestial equator
    this.celestialEquator.setLST(lstDeg);
  }

  /** Set observer latitude for celestial equator calculation. */
  setObserverLatitude(latDeg: number): void {
    this.celestialEquator.setLatitude(latDeg);
  }

  /** Called from CameraRig when FOV changes. */
  setCurrentFov(fovDeg: number): void {
    this.currentFovDeg = fovDeg;
  }

  setNavigationWorld(world: { setBoundsVisible(visible: boolean): void }): void {
    this.navigationWorld = world;
  }

  // ─── Phase 4: Overlay Toggles ──────────────────────────────────────

  setOverlayVisibility(key: keyof OverlayVisibility, visible: boolean): void {
    this.overlayVisibility[key] = visible;

    switch (key) {
      case "grid":
        this.horizontalGrid.setVisible(visible);
        break;
      case "compass":
        this.celestialLabels.setCardinalVisible(visible);
        break;
      case "labels":
        this.celestialLabels.setTicksVisible(visible);
        break;
      case "equator":
        this.celestialEquator.setVisible(visible);
        break;
      case "bounds":
        this.navigationWorld?.setBoundsVisible(visible);
        break;
      case "stars":
        this.starFieldRenderer.setVisible(visible);
        break;
    }

    console.info(`${LOG_PREFIX} [setOverlayVisibility] [${key}=${visible}]`);
  }

  getOverlayVisibility(): Readonly<OverlayVisibility> {
    return { ...this.overlayVisibility };
  }

  // ─── Phase 4: Metrics ──────────────────────────────────────────────

  getGridMetrics(): {
    geometryBuildCount: number;
    lodSwitchCount: number;
    bufferUploadBytes: number;
    activeLOD: string;
    labelTotal: number;
    labelVisible: number;
    labelCulled: number;
    equatorBuildCount: number;
  } {
    const labelCounts = this.celestialLabels.getCounts();
    return {
      geometryBuildCount: this.horizontalGrid.geometryBuildCount,
      lodSwitchCount: this.horizontalGrid.lodSwitchCount,
      bufferUploadBytes: this.horizontalGrid.bufferUploadBytes,
      activeLOD: this.horizontalGrid.getActiveLOD(),
      labelTotal: labelCounts.total,
      labelVisible: labelCounts.visible,
      labelCulled: labelCounts.culled,
      equatorBuildCount: this.celestialEquator.geometryBuildCount,
    };
  }

  dispose(): void {
    if (this.disposed) return;
    this.disposed = true;

    // Phase 4 & Phase 5: Dispose components
    this.horizontalGrid.dispose();
    this.celestialLabels.dispose();
    this.celestialEquator.dispose();
    this.starFieldRenderer.dispose();

    this.scene.traverse((obj) => {
      if (
        obj instanceof THREE.Mesh ||
        obj instanceof THREE.LineSegments ||
        obj instanceof THREE.LineLoop ||
        obj instanceof THREE.Line
      ) {
        obj.geometry.dispose();
        if (Array.isArray(obj.material)) {
          obj.material.forEach((m) => m.dispose());
        } else {
          obj.material.dispose();
        }
      }
    });

    this.renderer.dispose();
    this.renderer.domElement.remove();

    console.info(`${LOG_PREFIX} [dispose] [Escena alliberada]`);
  }
}
