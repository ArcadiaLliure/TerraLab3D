import * as THREE from "three";
import type { InstrumentFieldSnapshot } from "../../../contracts/observation_contracts";

export function cameraOverlayHalfSize(
  fieldWidthDeg: number,
  fieldHeightDeg: number,
  visualHorizontalFovDeg: number,
  aspect: number,
): readonly [number, number] {
  const visualH = THREE.MathUtils.degToRad(visualHorizontalFovDeg);
  const visualV = 2 * Math.atan(Math.tan(visualH / 2) / Math.max(aspect, 1e-6));
  return [
    Math.tan(THREE.MathUtils.degToRad(fieldWidthDeg) / 2) / Math.tan(visualH / 2),
    Math.tan(THREE.MathUtils.degToRad(fieldHeightDeg) / 2) / Math.tan(visualV / 2),
  ];
}

export interface ImagingPreviewLayerRenderer {
  present(field: InstrumentFieldSnapshot | null, visualHorizontalFovDeg: number, aspect: number, rotationDeg: number): void;
  attachRotationInteraction(canvas: HTMLCanvasElement, onCommit: (rotationDeg: number) => void): void;
  detachRotationInteraction(): void;
  setVisible(visible: boolean): void;
  render(renderer: THREE.WebGLRenderer): void;
  restoreResources(): void;
  dispose(): void;
}

export class ImagingPreviewLayerRendererImpl implements ImagingPreviewLayerRenderer {
  private readonly scene = new THREE.Scene();
  private readonly camera = new THREE.OrthographicCamera(-1, 1, 1, -1, 0, 1);
  private readonly geometry = new THREE.PlaneGeometry(2, 2);
  private readonly material = new THREE.ShaderMaterial({
    transparent: true,
    depthTest: false,
    depthWrite: false,
    uniforms: {
      uHalfSize: { value: new THREE.Vector2(0.5, 0.5) },
      uRotationRad: { value: 0.0 },
      uViewportPx: { value: new THREE.Vector2(1, 1) },
    },
    vertexShader: `varying vec2 vUv; void main(){vUv=uv;gl_Position=vec4(position.xy,0.0,1.0);}`,
    fragmentShader: `
      varying vec2 vUv; uniform vec2 uHalfSize; uniform float uRotationRad; uniform vec2 uViewportPx;
      void main(){
        vec2 screenP=vUv*2.0-1.0;
        float c=cos(uRotationRad), s=sin(uRotationRad);
        vec2 p=abs(mat2(c,-s,s,c)*screenP);
        float edge=max(p.x/max(uHalfSize.x,1e-6),p.y/max(uHalfSize.y,1e-6));
        float line=1.0-smoothstep(0.0,0.018,abs(edge-1.0));
        float outside=smoothstep(0.995,1.005,edge);
        vec2 corner=mat2(c,s,-s,c)*uHalfSize;
        float handleDistance=length((screenP-corner)*uViewportPx*0.5);
        float handle=1.0-smoothstep(7.0,10.0,handleDistance);
        gl_FragColor=vec4(vec3(0.78,0.68,0.30),max(line*0.9,handle))+vec4(0.0,0.0,0.0,outside*0.38);
      }`,
  });
  private readonly mesh = new THREE.Mesh(this.geometry, this.material);
  private visible = false;
  private halfX = 0.5;
  private halfY = 0.5;
  private rotationDeg = 0;
  private canvas: HTMLCanvasElement | null = null;
  private onRotationCommit: ((rotationDeg: number) => void) | null = null;
  private rotatingPointerId: number | null = null;
  readonly metrics = { geometryBuildCount: 1, renderCount: 0, restoreCount: 0 };

  constructor() {
    this.mesh.frustumCulled = false;
    this.scene.add(this.mesh);
  }

  present(field: InstrumentFieldSnapshot | null, visualHorizontalFovDeg: number, aspect: number, rotationDeg: number): void {
    if (!field || field.shape !== "rectangle") return;
    const [halfX, halfY] = cameraOverlayHalfSize(
      field.widthDeg, field.heightDeg, visualHorizontalFovDeg, aspect,
    );
    this.halfX = halfX;
    this.halfY = halfY;
    this.rotationDeg = normalizeRotationDeg(rotationDeg);
    (this.material.uniforms["uHalfSize"]!.value as THREE.Vector2).set(halfX, halfY);
    this.material.uniforms["uRotationRad"]!.value = THREE.MathUtils.degToRad(this.rotationDeg);
    this.material.uniformsNeedUpdate = true;
  }

  attachRotationInteraction(canvas: HTMLCanvasElement, onCommit: (rotationDeg: number) => void): void {
    this.detachRotationInteraction();
    this.canvas = canvas;
    this.onRotationCommit = onCommit;
    canvas.addEventListener("pointerdown", this.onPointerDown, true);
    canvas.addEventListener("pointermove", this.onPointerMove, true);
    canvas.addEventListener("pointerup", this.onPointerUp, true);
    canvas.addEventListener("pointercancel", this.onPointerUp, true);
  }

  detachRotationInteraction(): void {
    if (!this.canvas) return;
    this.canvas.removeEventListener("pointerdown", this.onPointerDown, true);
    this.canvas.removeEventListener("pointermove", this.onPointerMove, true);
    this.canvas.removeEventListener("pointerup", this.onPointerUp, true);
    this.canvas.removeEventListener("pointercancel", this.onPointerUp, true);
    this.canvas = null;
    this.onRotationCommit = null;
    this.rotatingPointerId = null;
  }

  setVisible(visible: boolean): void { this.visible = visible; }
  render(renderer: THREE.WebGLRenderer): void {
    if (!this.visible) return;
    renderer.getDrawingBufferSize(this.material.uniforms["uViewportPx"]!.value as THREE.Vector2);
    renderer.render(this.scene, this.camera);
    this.metrics.renderCount++;
  }
  restoreResources(): void { this.material.needsUpdate = true; this.metrics.restoreCount++; }
  dispose(): void {
    this.detachRotationInteraction();
    this.geometry.dispose();
    this.material.dispose();
    this.scene.clear();
  }

  private readonly onPointerDown = (event: PointerEvent): void => {
    if (!this.visible || !this.canvas || !this.isNearRotationHandle(event)) return;
    this.rotatingPointerId = event.pointerId;
    this.canvas.setPointerCapture(event.pointerId);
    event.preventDefault();
    event.stopImmediatePropagation();
  };

  private readonly onPointerMove = (event: PointerEvent): void => {
    if (event.pointerId !== this.rotatingPointerId || !this.canvas) return;
    const rect = this.canvas.getBoundingClientRect();
    const x = 2 * (event.clientX - rect.left) / Math.max(rect.width, 1) - 1;
    const y = 1 - 2 * (event.clientY - rect.top) / Math.max(rect.height, 1);
    const cornerAngle = Math.atan2(this.halfY, this.halfX);
    this.rotationDeg = normalizeRotationDeg(THREE.MathUtils.radToDeg(Math.atan2(y, x) - cornerAngle));
    this.material.uniforms["uRotationRad"]!.value = THREE.MathUtils.degToRad(this.rotationDeg);
    this.material.uniformsNeedUpdate = true;
    event.preventDefault();
    event.stopImmediatePropagation();
  };

  private readonly onPointerUp = (event: PointerEvent): void => {
    if (event.pointerId !== this.rotatingPointerId || !this.canvas) return;
    this.rotatingPointerId = null;
    if (this.canvas.hasPointerCapture(event.pointerId)) this.canvas.releasePointerCapture(event.pointerId);
    this.onRotationCommit?.(this.rotationDeg);
    event.preventDefault();
    event.stopImmediatePropagation();
  };

  private isNearRotationHandle(event: PointerEvent): boolean {
    if (!this.canvas) return false;
    const rect = this.canvas.getBoundingClientRect();
    const angle = THREE.MathUtils.degToRad(this.rotationDeg);
    const cornerX = Math.cos(angle) * this.halfX - Math.sin(angle) * this.halfY;
    const cornerY = Math.sin(angle) * this.halfX + Math.cos(angle) * this.halfY;
    const handleX = rect.left + (cornerX + 1) * rect.width / 2;
    const handleY = rect.top + (1 - cornerY) * rect.height / 2;
    return Math.hypot(event.clientX - handleX, event.clientY - handleY) <= 14;
  }
}

export function normalizeRotationDeg(value: number): number {
  return ((value + 180) % 360 + 360) % 360 - 180;
}
