/**
 * Concrete Three.js scene host with celestialRoot / worldRoot / overlayRoot
 * separation for correct parallax behaviour (Phase 3.5).
 *
 * World conventions:
 *   Y = up (Three.js native)
 *   North = -Z,  East = +X,  South = +Z,  West = -X
 *
 * Scene tree:
 *   scene
 *   ├── celestialRoot  (recentred to camera position → no translational parallax)
 *   │   ├── diagnosticSphere
 *   │   ├── altitudeCircles
 *   │   ├── zenithMarker
 *   │   └── celestialSphere (meridians, rotates with LST)
 *   ├── worldRoot      (stays at origin → real parallax for terrain/objects)
 *   │   ├── terrain     (from NavigationWorld)
 *   │   ├── horizon
 *   │   ├── ground
 *   │   └── localReferenceObjects (from NavigationWorld)
 *   └── cameraRig / camera (managed by CameraRigImpl)
 */

import * as THREE from "three";

const HORIZON_RADIUS = 100;
const HORIZON_SEGMENTS = 256;
const BACKGROUND_COLOR = 0x02040a;
const LABEL_DISTANCE = 95;

interface CardinalLabel {
  element: HTMLDivElement;
  worldPos: THREE.Vector3;
}

export class ThreeSceneHostImpl {
  readonly scene: THREE.Scene;
  readonly camera: THREE.PerspectiveCamera;
  readonly renderer: THREE.WebGLRenderer;

  // ─── Scene tree roots ──────────────────────────────────────────────
  private readonly celestialRoot: THREE.Group;
  private readonly worldRoot: THREE.Group;

  private container: HTMLElement | null = null;
  private readonly horizonLine: THREE.LineLoop;
  private readonly zenithMarker: THREE.Mesh;
  private readonly diagnosticSphere: THREE.LineSegments;
  private readonly cardinalLabels: CardinalLabel[] = [];
  private readonly labelContainer: HTMLDivElement;
  private readonly celestialSphere: THREE.Group;
  private targetLstRad = 0;
  private currentLstRad = 0;
  private disposed = false;

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
    this.camera = new THREE.PerspectiveCamera(60, 1, 0.01, 2000);

    // Renderer
    this.renderer = new THREE.WebGLRenderer({ antialias: true });
    this.renderer.setPixelRatio(window.devicePixelRatio);

    // Label container (CSS overlay for cardinal labels)
    this.labelContainer = document.createElement("div");
    this.labelContainer.style.cssText =
      "position:absolute;top:0;left:0;width:100%;height:100%;pointer-events:none;overflow:hidden;";

    // ─── Horizon ring (worldRoot — shows parallax) ───────────────────
    const horizonGeo = new THREE.BufferGeometry();
    const horizonVerts = new Float32Array((HORIZON_SEGMENTS + 1) * 3);
    for (let i = 0; i <= HORIZON_SEGMENTS; i++) {
      const theta = (i / HORIZON_SEGMENTS) * Math.PI * 2;
      horizonVerts[i * 3] = Math.sin(theta) * HORIZON_RADIUS;
      horizonVerts[i * 3 + 1] = 0;
      horizonVerts[i * 3 + 2] = Math.cos(theta) * HORIZON_RADIUS;
    }
    horizonGeo.setAttribute("position", new THREE.BufferAttribute(horizonVerts, 3));
    const horizonMat = new THREE.LineBasicMaterial({ color: 0x445566, linewidth: 1 });
    this.horizonLine = new THREE.LineLoop(horizonGeo, horizonMat);
    this.worldRoot.add(this.horizonLine);

    // ─── Ground plane (worldRoot) ────────────────────────────────────
    const groundGeo = new THREE.CircleGeometry(HORIZON_RADIUS, 64);
    const groundMat = new THREE.MeshBasicMaterial({
      color: 0x0a1520,
      side: THREE.DoubleSide,
      transparent: true,
      opacity: 0.4,
    });
    const ground = new THREE.Mesh(groundGeo, groundMat);
    ground.rotation.x = -Math.PI / 2;
    ground.position.y = -0.01;
    this.worldRoot.add(ground);

    // ─── Zenith marker (celestialRoot — no parallax) ─────────────────
    const zenithGeo = new THREE.SphereGeometry(0.5, 12, 8);
    const zenithMat = new THREE.MeshBasicMaterial({ color: 0xf1cd88 });
    this.zenithMarker = new THREE.Mesh(zenithGeo, zenithMat);
    this.zenithMarker.position.set(0, HORIZON_RADIUS * 0.95, 0);
    this.celestialRoot.add(this.zenithMarker);

    // ─── Diagnostic wireframe sphere (celestialRoot) ─────────────────
    const diagGeo = new THREE.SphereGeometry(HORIZON_RADIUS * 0.98, 24, 16);
    const diagEdges = new THREE.EdgesGeometry(diagGeo);
    const diagMat = new THREE.LineBasicMaterial({
      color: 0x223344,
      transparent: true,
      opacity: 0.15,
    });
    this.diagnosticSphere = new THREE.LineSegments(diagEdges, diagMat);
    this.celestialRoot.add(this.diagnosticSphere);

    // ─── Altitude circles (celestialRoot) ────────────────────────────
    this.addAltitudeCircle(30, 0x334455, 0.3);
    this.addAltitudeCircle(60, 0x334455, 0.3);

    // ─── Celestial Sphere (celestialRoot — rotates with LST) ─────────
    this.celestialSphere = new THREE.Group();
    this.celestialRoot.add(this.celestialSphere);

    const meridianMat = new THREE.LineBasicMaterial({
      color: 0x556677,
      transparent: true,
      opacity: 0.2,
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

  mount(container: HTMLElement): void {
    this.container = container;
    const rect = container.getBoundingClientRect();
    this.renderer.setSize(rect.width, rect.height);
    container.appendChild(this.renderer.domElement);
    container.appendChild(this.labelContainer);

    // Create cardinal labels
    this.createCardinalLabel("N", 0, 0, -LABEL_DISTANCE, "#f1cd88");
    this.createCardinalLabel("E", LABEL_DISTANCE, 0, 0, "#88bbff");
    this.createCardinalLabel("S", 0, 0, LABEL_DISTANCE, "#88bbff");
    this.createCardinalLabel("W", -LABEL_DISTANCE, 0, 0, "#88bbff");

    // Cardinal tick lines on the horizon (worldRoot)
    this.addCardinalTick(0, -1);
    this.addCardinalTick(1, 0);
    this.addCardinalTick(0, 1);
    this.addCardinalTick(-1, 0);
  }

  resize(widthPx: number, heightPx: number): void {
    this.renderer.setSize(widthPx, heightPx);
    this.renderer.setPixelRatio(window.devicePixelRatio);
  }

  render(timestampMs: number): void {
    if (this.disposed) return;

    // ─── Celestial rotation ──────────────────────────────────────────
    const diff = this.targetLstRad - this.currentLstRad;
    let shortest = diff % (Math.PI * 2);
    if (shortest > Math.PI) shortest -= Math.PI * 2;
    if (shortest < -Math.PI) shortest += Math.PI * 2;
    this.currentLstRad += shortest * 0.1;
    this.celestialSphere.rotation.y = -this.currentLstRad;

    // ─── Recentre celestialRoot to camera position ───────────────────
    // This eliminates translational parallax for sky objects.
    // The celestial root moves with the camera so distant objects
    // (stars, grid, zenith) appear at infinite distance.
    this.celestialRoot.position.copy(this.camera.position);

    this.updateCardinalLabels();
    this.renderer.render(this.scene, this.camera);
  }

  setSiderealTime(lstDeg: number): void {
    this.targetLstRad = THREE.MathUtils.degToRad(lstDeg);
  }

  dispose(): void {
    if (this.disposed) return;
    this.disposed = true;

    for (const label of this.cardinalLabels) {
      label.element.remove();
    }
    this.cardinalLabels.length = 0;

    this.scene.traverse((obj) => {
      if (
        obj instanceof THREE.Mesh ||
        obj instanceof THREE.LineSegments ||
        obj instanceof THREE.LineLoop
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
    this.labelContainer.remove();
  }

  // ─── Private ───────────────────────────────────────────────────────

  private addAltitudeCircle(altDeg: number, color: number, opacity: number): void {
    const r = HORIZON_RADIUS * Math.cos((altDeg * Math.PI) / 180);
    const y = HORIZON_RADIUS * Math.sin((altDeg * Math.PI) / 180);
    const geo = new THREE.BufferGeometry();
    const verts = new Float32Array((HORIZON_SEGMENTS + 1) * 3);
    for (let i = 0; i <= HORIZON_SEGMENTS; i++) {
      const theta = (i / HORIZON_SEGMENTS) * Math.PI * 2;
      verts[i * 3] = Math.sin(theta) * r;
      verts[i * 3 + 1] = y;
      verts[i * 3 + 2] = Math.cos(theta) * r;
    }
    geo.setAttribute("position", new THREE.BufferAttribute(verts, 3));
    const mat = new THREE.LineBasicMaterial({ color, transparent: true, opacity });
    const line = new THREE.LineLoop(geo, mat);
    this.celestialRoot.add(line);
  }

  private addCardinalTick(x: number, z: number): void {
    const inner = HORIZON_RADIUS * 0.96;
    const outer = HORIZON_RADIUS * 1.04;
    const geo = new THREE.BufferGeometry();
    const verts = new Float32Array([
      x * inner, 0, z * inner,
      x * outer, 0, z * outer,
    ]);
    geo.setAttribute("position", new THREE.BufferAttribute(verts, 3));
    const mat = new THREE.LineBasicMaterial({ color: 0xf1cd88 });
    const line = new THREE.LineSegments(geo, mat);
    this.worldRoot.add(line);
  }

  private createCardinalLabel(text: string, x: number, y: number, z: number, color: string): void {
    const el = document.createElement("div");
    el.textContent = text;
    el.style.cssText = `
      position: absolute;
      color: ${color};
      font-family: 'Inter', 'Roboto', sans-serif;
      font-size: 14px;
      font-weight: 700;
      text-shadow: 0 0 6px rgba(0,0,0,0.8);
      pointer-events: none;
      user-select: none;
      transform: translate(-50%, -50%);
    `;
    this.labelContainer.appendChild(el);
    this.cardinalLabels.push({
      element: el,
      worldPos: new THREE.Vector3(x, y, z),
    });
  }

  private readonly _projVec = new THREE.Vector3();

  private updateCardinalLabels(): void {
    if (!this.container) return;
    const rect = this.container.getBoundingClientRect();
    const halfW = rect.width / 2;
    const halfH = rect.height / 2;

    for (const label of this.cardinalLabels) {
      this._projVec.copy(label.worldPos);
      this._projVec.project(this.camera);

      if (this._projVec.z > 1) {
        label.element.style.display = "none";
        continue;
      }

      const sx = this._projVec.x * halfW + halfW;
      const sy = -this._projVec.y * halfH + halfH;

      label.element.style.display = "";
      label.element.style.left = `${sx}px`;
      label.element.style.top = `${sy}px`;
    }
  }
}
