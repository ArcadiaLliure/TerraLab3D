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
  present(field: InstrumentFieldSnapshot | null, visualHorizontalFovDeg: number, aspect: number): void;
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
    uniforms: { uHalfSize: { value: new THREE.Vector2(0.5, 0.5) } },
    vertexShader: `varying vec2 vUv; void main(){vUv=uv;gl_Position=vec4(position.xy,0.0,1.0);}`,
    fragmentShader: `
      varying vec2 vUv; uniform vec2 uHalfSize;
      void main(){
        vec2 p=abs(vUv*2.0-1.0);
        float edge=max(p.x/max(uHalfSize.x,1e-6),p.y/max(uHalfSize.y,1e-6));
        float line=1.0-smoothstep(0.0,0.018,abs(edge-1.0));
        float outside=smoothstep(0.995,1.005,edge);
        gl_FragColor=vec4(vec3(0.78,0.68,0.30),line*0.9)+vec4(0.0,0.0,0.0,outside*0.38);
      }`,
  });
  private readonly mesh = new THREE.Mesh(this.geometry, this.material);
  private visible = false;
  readonly metrics = { geometryBuildCount: 1, renderCount: 0, restoreCount: 0 };

  constructor() {
    this.mesh.frustumCulled = false;
    this.scene.add(this.mesh);
  }

  present(field: InstrumentFieldSnapshot | null, visualHorizontalFovDeg: number, aspect: number): void {
    if (!field || field.shape !== "rectangle") return;
    const [halfX, halfY] = cameraOverlayHalfSize(
      field.widthDeg, field.heightDeg, visualHorizontalFovDeg, aspect,
    );
    (this.material.uniforms["uHalfSize"]!.value as THREE.Vector2).set(halfX, halfY);
    this.material.uniformsNeedUpdate = true;
  }

  setVisible(visible: boolean): void { this.visible = visible; }
  render(renderer: THREE.WebGLRenderer): void {
    if (!this.visible) return;
    renderer.render(this.scene, this.camera);
    this.metrics.renderCount++;
  }
  restoreResources(): void { this.material.needsUpdate = true; this.metrics.restoreCount++; }
  dispose(): void { this.geometry.dispose(); this.material.dispose(); this.scene.clear(); }
}
