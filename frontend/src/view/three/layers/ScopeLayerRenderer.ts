import * as THREE from "three";
import type { InstrumentFieldSnapshot } from "../../../contracts/observation_contracts";

export function telescopeOverlayRadiusY(
  trueFovDeg: number,
  visualHorizontalFovDeg: number,
  aspect: number,
): number {
  const visualH = THREE.MathUtils.degToRad(visualHorizontalFovDeg);
  const visualV = 2 * Math.atan(Math.tan(visualH / 2) / Math.max(aspect, 1e-6));
  return Math.tan(THREE.MathUtils.degToRad(trueFovDeg) / 2) / Math.tan(visualV / 2);
}

export interface ScopeLayerRenderer {
  present(field: InstrumentFieldSnapshot | null, visualHorizontalFovDeg: number, aspect: number): void;
  setVisible(visible: boolean): void;
  render(renderer: THREE.WebGLRenderer): void;
  restoreResources(): void;
  dispose(): void;
}

export class ScopeLayerRendererImpl implements ScopeLayerRenderer {
  private readonly scene = new THREE.Scene();
  private readonly camera = new THREE.OrthographicCamera(-1, 1, 1, -1, 0, 1);
  private readonly geometry = new THREE.PlaneGeometry(2, 2);
  private readonly material = new THREE.ShaderMaterial({
    transparent: true,
    depthTest: false,
    depthWrite: false,
    uniforms: {
      uRadiusY: { value: 0.4 },
      uAspect: { value: 1.0 },
    },
    vertexShader: `varying vec2 vUv; void main(){vUv=uv;gl_Position=vec4(position.xy,0.0,1.0);}`,
    fragmentShader: `
      varying vec2 vUv; uniform float uRadiusY; uniform float uAspect;
      void main(){
        vec2 p=vUv*2.0-1.0; vec2 pixelSpace=vec2(p.x*uAspect,p.y);
        float d=length(pixelSpace); float border=1.0-smoothstep(uRadiusY-0.006,uRadiusY+0.006,d);
        float ring=1.0-smoothstep(0.0,0.012,abs(d-uRadiusY));
        float crossX=(1.0-smoothstep(0.0,0.0025,abs(pixelSpace.x)))*step(d,uRadiusY*0.22);
        float crossY=(1.0-smoothstep(0.0,0.0025,abs(pixelSpace.y)))*step(d,uRadiusY*0.22);
        float outside=1.0-border;
        gl_FragColor=vec4(vec3(0.82,0.72,0.35),max(ring,max(crossX,crossY))*0.92)+vec4(0.0,0.0,0.0,outside*0.52);
      }`,
  });
  private readonly mesh = new THREE.Mesh(this.geometry, this.material);
  private visible = false;
  readonly metrics = { geometryBuildCount: 1, renderCount: 0, restoreCount: 0 };

  constructor() { this.mesh.frustumCulled = false; this.scene.add(this.mesh); }
  present(field: InstrumentFieldSnapshot | null, visualHorizontalFovDeg: number, aspect: number): void {
    if (!field || field.shape !== "circle") return;
    const radiusY = telescopeOverlayRadiusY(field.widthDeg, visualHorizontalFovDeg, aspect);
    this.material.uniforms["uRadiusY"]!.value = radiusY;
    this.material.uniforms["uAspect"]!.value = aspect;
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
