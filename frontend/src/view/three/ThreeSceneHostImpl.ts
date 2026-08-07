/**
 * Concrete Three.js scene host with technical horizon and cardinal points.
 *
 * World conventions:
 *   Y = up (Three.js native)
 *   North = -Z,  East = +X,  South = +Z,  West = -X
 *
 * Creates:
 *   - Scene with dark background (#02040a)
 *   - PerspectiveCamera (managed by CameraRigImpl)
 *   - WebGLRenderer with antialias, device pixel ratio
 *   - Technical horizon ring at Y=0
 *   - Cardinal labels (N, E, S, W) as CSS-styled DOM elements
 *   - Zenith marker
 *   - Diagnostic wireframe sphere
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

    // Camera (initial values; CameraRigImpl manages pose)
    this.camera = new THREE.PerspectiveCamera(60, 1, 0.01, 1000);

    // Renderer
    this.renderer = new THREE.WebGLRenderer({ antialias: true });
    this.renderer.setPixelRatio(window.devicePixelRatio);

    // Label container (CSS overlay for cardinal labels)
    this.labelContainer = document.createElement("div");
    this.labelContainer.style.cssText =
      "position:absolute;top:0;left:0;width:100%;height:100%;pointer-events:none;overflow:hidden;";

    // ─── Horizon ring ────────────────────────────────────────────────
    const horizonGeo = new THREE.BufferGeometry();
    const horizonVerts = new Float32Array((HORIZON_SEGMENTS + 1) * 3);
    for (let i = 0; i <= HORIZON_SEGMENTS; i++) {
      const theta = (i / HORIZON_SEGMENTS) * Math.PI * 2;
      horizonVerts[i * 3] = Math.sin(theta) * HORIZON_RADIUS;
      horizonVerts[i * 3 + 1] = 0;
      horizonVerts[i * 3 + 2] = Math.cos(theta) * HORIZON_RADIUS;
    }
    horizonGeo.setAttribute(
      "position",
      new THREE.BufferAttribute(horizonVerts, 3),
    );
    const horizonMat = new THREE.LineBasicMaterial({
      color: 0x445566,
      linewidth: 1,
    });
    this.horizonLine = new THREE.LineLoop(horizonGeo, horizonMat);
    this.scene.add(this.horizonLine);

    // ─── Ground plane (subtle grid below horizon) ────────────────────
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
    this.scene.add(ground);

    // ─── Zenith marker ───────────────────────────────────────────────
    const zenithGeo = new THREE.SphereGeometry(0.5, 12, 8);
    const zenithMat = new THREE.MeshBasicMaterial({ color: 0xf1cd88 });
    this.zenithMarker = new THREE.Mesh(zenithGeo, zenithMat);
    this.zenithMarker.position.set(0, HORIZON_RADIUS * 0.95, 0);
    this.scene.add(this.zenithMarker);

    // ─── Diagnostic wireframe sphere ─────────────────────────────────
    const diagGeo = new THREE.SphereGeometry(HORIZON_RADIUS * 0.98, 24, 16);
    const diagEdges = new THREE.EdgesGeometry(diagGeo);
    const diagMat = new THREE.LineBasicMaterial({
      color: 0x223344,
      transparent: true,
      opacity: 0.15,
    });
    this.diagnosticSphere = new THREE.LineSegments(diagEdges, diagMat);
    this.scene.add(this.diagnosticSphere);

    // ─── Altitude circles (30° and 60°) ──────────────────────────────
    this.addAltitudeCircle(30, 0x334455, 0.3);
    this.addAltitudeCircle(60, 0x334455, 0.3);

    // ─── Celestial Sphere (Equatorial Reference) ─────────────────────
    this.celestialSphere = new THREE.Group();
    this.scene.add(this.celestialSphere);
    
    // Add some reference meridians to the celestial sphere to see it rotate
    const meridianMat = new THREE.LineBasicMaterial({ color: 0x556677, transparent: true, opacity: 0.2 });
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

    // Cardinal tick lines on the horizon
    this.addCardinalTick(0, -1); // North (-Z)
    this.addCardinalTick(1, 0); // East (+X)
    this.addCardinalTick(0, 1); // South (+Z)
    this.addCardinalTick(-1, 0); // West (-X)
  }

  resize(widthPx: number, heightPx: number): void {
    this.renderer.setSize(widthPx, heightPx);
    this.renderer.setPixelRatio(window.devicePixelRatio);
  }

  render(timestampMs: number): void {
    if (this.disposed) return;
    
    // Simple interpolation for smooth celestial rotation
    const diff = this.targetLstRad - this.currentLstRad;
    // Normalize diff to -PI, PI
    let shortest = diff % (Math.PI * 2);
    if (shortest > Math.PI) shortest -= Math.PI * 2;
    if (shortest < -Math.PI) shortest += Math.PI * 2;
    
    this.currentLstRad += shortest * 0.1; // lerp
    // Rotate the celestial sphere (simple Y rotation for visual effect)
    // A true equatorial mount would tilt by the observer's latitude.
    this.celestialSphere.rotation.y = -this.currentLstRad;

    this.updateCardinalLabels();
    this.renderer.render(this.scene, this.camera);
  }

  setSiderealTime(lstDeg: number): void {
    this.targetLstRad = THREE.MathUtils.degToRad(lstDeg);
  }

  dispose(): void {
    if (this.disposed) return;
    this.disposed = true;

    // Remove cardinal labels
    for (const label of this.cardinalLabels) {
      label.element.remove();
    }
    this.cardinalLabels.length = 0;

    // Dispose Three.js objects
    this.scene.traverse((obj) => {
      if (obj instanceof THREE.Mesh || obj instanceof THREE.LineSegments || obj instanceof THREE.LineLoop) {
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

  private addAltitudeCircle(
    altDeg: number,
    color: number,
    opacity: number,
  ): void {
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
    const mat = new THREE.LineBasicMaterial({
      color,
      transparent: true,
      opacity,
    });
    const line = new THREE.LineLoop(geo, mat);
    this.scene.add(line);
  }

  private addCardinalTick(x: number, z: number): void {
    const inner = HORIZON_RADIUS * 0.96;
    const outer = HORIZON_RADIUS * 1.04;
    const geo = new THREE.BufferGeometry();
    const verts = new Float32Array([
      x * inner,
      0,
      z * inner,
      x * outer,
      0,
      z * outer,
    ]);
    geo.setAttribute("position", new THREE.BufferAttribute(verts, 3));
    const mat = new THREE.LineBasicMaterial({ color: 0xf1cd88 });
    const line = new THREE.LineSegments(geo, mat);
    this.scene.add(line);
  }

  private createCardinalLabel(
    text: string,
    x: number,
    y: number,
    z: number,
    color: string,
  ): void {
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

      // Behind the camera?
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
