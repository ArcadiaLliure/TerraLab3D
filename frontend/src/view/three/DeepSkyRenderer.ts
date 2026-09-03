/**
 * Renderitzador del catàleg de cel profund (NGC/IC) per a Three.js.
 */
import * as THREE from "three";
import type { CelestialTransformState } from "./CelestialTransformState";
import type { SkyVisibilityState } from "../../contracts/sky_environment_contracts";
import { DEFAULT_SKY_VISIBILITY } from "../../contracts/sky_visibility_defaults";
import { DeepSkyLabels } from "./DeepSkyLabels";
import type { HorizonOcclusionState } from "./HorizonOcclusionState";
import { CELESTIAL_SCENE_RADIUS } from "./celestialScenePolicy";
import {
  HORIZON_GLSL_FUNCTIONS,
  HORIZON_GLSL_UNIFORMS,
} from "./shaders/horizonOcclusionShader";

const VERTEX_SHADER = `
  precision highp float;
  uniform mat3 u_equatorialToENUMatrix;
  uniform float u_radius;
  ${HORIZON_GLSL_UNIFORMS}
  
  attribute vec3 equatorialDirection;
  attribute vec3 northTangent;
  attribute vec3 eastTangent;
  attribute float majorAxisArcmin;
  attribute float minorAxisArcmin;
  attribute float positionAngleDeg;
  attribute float magnitude;
  attribute float surfaceBrightness;
  attribute float familyCode;
  attribute float flags;
  attribute float catalogIndex;

  // The local quad coordinates: -0.5 to 0.5
  varying vec2 vUv;
  varying float vFamily;
  varying float vMagnitude;
  varying float vSurfBr;
  varying float vFlags;
  ${HORIZON_GLSL_FUNCTIONS}
  
  void main() {
    vUv = position.xy;
    vFamily = familyCode;
    vMagnitude = magnitude;
    vSurfBr = surfaceBrightness;
    vFlags = flags;
    
    // Convert arcminutes to radians
    // 1 arcmin = 1/60 deg = pi / 10800 rad
    float radPerArcmin = 3.14159265359 / 10800.0;
    
    // Default size if major/minor missing: say 2 arcmin
    float maj = majorAxisArcmin > 0.0 ? majorAxisArcmin : 5.0;
    float min = minorAxisArcmin > 0.0 ? minorAxisArcmin : maj;
    
    // (Removed minimum size forcing per user request)
    
    // The quad size in radians on the sphere
    // We multiply by 1.2 to give some padding for rendering
    float wRad = min * radPerArcmin * 1.2;
    float hRad = maj * radPerArcmin * 1.2;
    
    // Position angle (measured East of North). PA is given in degrees.
    // If it's NaN (not greater than or equal to 0, nor less than 0), default to 0.0
    float paVal = (positionAngleDeg >= 0.0 || positionAngleDeg < 0.0) ? positionAngleDeg : 0.0;
    float paRad = paVal * 3.14159265359 / 180.0;
    
    // Rotate the local quad vertices by PA
    float cosPA = cos(paRad);
    float sinPA = sin(paRad);
    
    // Local coords (x is East-ish, y is North-ish)
    // Actually PA is from North (y) towards East (x), so:
    // x' = x*cosPA + y*sinPA
    // y' = -x*sinPA + y*cosPA
    vec2 localPos = position.xy; // -0.5 to 0.5
    float lx = localPos.x * wRad;
    float ly = localPos.y * hRad;
    
    float rx = lx * cosPA + ly * sinPA;
    float ry = -lx * sinPA + ly * cosPA;
    
    // Compute the 3D direction on the unit sphere
    vec3 dir = equatorialDirection + rx * eastTangent + ry * northTangent;
    dir = normalize(dir);
    
    // Transform to ENU using the same matrix as stars
    vec3 enuDir = u_equatorialToENUMatrix * dir;
    float altitudeDeg = degrees(asin(clamp(enuDir.y, -1.0, 1.0)));
    if (altitudeDeg < horizonElevationAtDirection(enuDir)) {
      gl_Position = vec4(2.0, 2.0, 2.0, 1.0);
      return;
    }
    
    // Project to the sky sphere
    vec3 finalPos = enuDir * u_radius;
    
    gl_Position = projectionMatrix * modelViewMatrix * vec4(finalPos, 1.0);
  }
`;

const FRAGMENT_SHADER = `
  precision highp float;
  
  varying vec2 vUv;
  varying float vFamily;
  varying float vMagnitude;
  varying float vSurfBr;
  varying float vFlags;
  
  uniform float u_zenithMagnitudeLimit;
  uniform float u_extinctionCoefficient;
  uniform float u_twilightSuppression;
  uniform float u_fadeWidthMag;
  
  void main() {
    // Distance from center of the quad (-1 to 1)
    vec2 st = vUv * 2.0;
    float d = length(st);
    
    if (d > 1.0) discard;
    
    float fade = 1.0 - u_twilightSuppression;
    if (fade <= 0.01) discard;

    vec3 color = vec3(0.36, 0.70, 1.0); // default galaxy blue
    
    // Distinct vibrant color per deep sky family (matching E:\\Desarrollo\\TerraLab)
    if (vFamily < 0.5) {
      // 0: Galaxy -> Light Blue / Cyan
      color = vec3(0.36, 0.70, 1.0);
    } else if (vFamily < 1.5) {
      // 1: Nebula -> Emerald Green / Teal
      color = vec3(0.30, 0.71, 0.67);
    } else if (vFamily < 2.5) {
      // 2: Open Cluster -> Bright Gold / Yellow
      color = vec3(1.0, 0.83, 0.31);
    } else if (vFamily < 3.5) {
      // 3: Globular Cluster -> Amber / Warm Orange
      color = vec3(1.0, 0.71, 0.30);
    } else if (vFamily < 4.5) {
      // 4: Cluster + Nebula -> Cyan / Green
      color = vec3(0.30, 0.81, 0.88);
    } else {
      // 5-6: Association / Other -> Soft Purple
      color = vec3(0.80, 0.57, 0.85);
    }
    
    // Línea simple y fina (rodoneta)
    // d va de 0 al centro a 1 en el borde exterior.
    // Trazamos la línea en d = 0.95
    float distToLine = abs(d - 0.95);
    
    // Un grosor muy fino para que sea una línea simple sin rellenos ni glows
    float thickness = 0.03;
    float alpha = smoothstep(thickness, 0.0, distToLine);
    
    gl_FragColor = vec4(color, alpha * fade);
  }
`;

export class DeepSkyRenderer {
  private readonly rootGroup = new THREE.Group();
  private isVisible = true;
  private transformState: CelestialTransformState | null = null;
  private appliedTransformRevision = -1;
  private currentVisibilityState: SkyVisibilityState | null = null;
  private readonly horizonUnsubscribe: (() => void) | null;

  private mesh: THREE.Mesh | null = null;
  private material: THREE.ShaderMaterial | null = null;
  private geometry: THREE.InstancedBufferGeometry | null = null;

  public metadata: any = null;
  public payloadBuffer: ArrayBuffer | null = null;
  public readonly catalogIndexToBufferIndex = new Map<number, number>();

  public readonly labels: DeepSkyLabels;

  constructor(private readonly horizonState: HorizonOcclusionState | null = null) {
    this.rootGroup.name = "deepSkyRoot";
    this.labels = new DeepSkyLabels(horizonState);
    this.horizonUnsubscribe = horizonState?.subscribe(() => this.syncHorizonUniforms()) ?? null;
  }

  public setTransformState(state: CelestialTransformState): void {
    this.transformState = state;
    this.appliedTransformRevision = -1;
  }

  public attachToParent(parentGroup: THREE.Group, overlayParent?: HTMLElement): void {
    parentGroup.add(this.rootGroup);
    if (overlayParent) {
      this.labels.mount(overlayParent);
    }
  }

  public detachFromParent(): void {
    this.rootGroup.removeFromParent();
  }

  public setVisible(visible: boolean): void {
    this.isVisible = visible;
    this.rootGroup.visible = visible;
    this.labels.setVisible(visible);
    console.log(`MGP: [DeepSkyRenderer] setVisible: ${visible} (rootGroup.visible = ${this.rootGroup.visible})`);
  }

  public get visible(): boolean {
    return this.isVisible;
  }

  public updateVisibilityUniforms(state: SkyVisibilityState): void {
    this.currentVisibilityState = state;
    this.labels.updateVisibilityUniforms(state);
    if (this.material) {
      this.material.uniforms["u_zenithMagnitudeLimit"]!.value = state.zenithMagnitudeLimit;
      this.material.uniforms["u_extinctionCoefficient"]!.value = state.extinctionCoefficient;
      this.material.uniforms["u_twilightSuppression"]!.value = state.twilightSuppression;
      this.material.uniforms["u_fadeWidthMag"]!.value = state.fadeWidthMag;
      this.material.uniformsNeedUpdate = true;
    }
  }

  public updateCelestialTransform(generation: number, matrix3x3: number[]): void {
    if (!this.material || !matrix3x3 || matrix3x3.length !== 9) return;

    if (this.transformState) {
      this.transformState.update(generation, matrix3x3);
    } else {
      const mat3 = this.material.uniforms["u_equatorialToENUMatrix"]!.value as THREE.Matrix3;
      mat3.set(
        matrix3x3[0]!, matrix3x3[1]!, matrix3x3[2]!,
        matrix3x3[3]!, matrix3x3[4]!, matrix3x3[5]!,
        matrix3x3[6]!, matrix3x3[7]!, matrix3x3[8]!,
      );
      this.material.uniformsNeedUpdate = true;
    }
  }

  public getTransformMatrix(): THREE.Matrix3 | null {
    if (!this.material) return null;
    return this.material.uniforms["u_equatorialToENUMatrix"]!.value as THREE.Matrix3;
  }

  /** Consume the shared transform after its owner has advanced it for this frame. */
  public syncTransform(): boolean {
    if (!this.transformState || !this.transformState.isValid || !this.material) return false;
    if (this.appliedTransformRevision === this.transformState.visualRevision) return false;

    const mat3 = this.material.uniforms["u_equatorialToENUMatrix"]!.value as THREE.Matrix3;
    mat3.copy(this.transformState.equatorialToThree);
    this.material.uniformsNeedUpdate = true;
    this.appliedTransformRevision = this.transformState.visualRevision;
    return true;
  }

  public registerBinaryResource(metadata: any, payloadBuffer: ArrayBuffer): void {
    if (this.mesh) {
      this.disposeResource();
    }

    const layout = metadata.bufferLayout;
    const count = metadata.renderableCount ?? metadata.recordCount;
    // Silence log

    const eqDirs = new Float32Array(payloadBuffer!, layout.equatorialDirections!.offset, count * 3);
    const nTans = new Float32Array(payloadBuffer, layout.northTangents.offset, count * 3);
    const eTans = new Float32Array(payloadBuffer, layout.eastTangents.offset, count * 3);
    const majAx = new Float32Array(payloadBuffer, layout.majorAxisArcmin!.offset, count);
    const minAx = new Float32Array(payloadBuffer, layout.minorAxisArcmin!.offset, count);
    const paDeg = new Float32Array(payloadBuffer, layout.positionAngleDeg!.offset, count);
    const mags = new Float32Array(payloadBuffer, layout.magnitude!.offset, count);
    const surfBr = new Float32Array(payloadBuffer, layout.surfaceBrightness!.offset, count);
    const families = new Float32Array(count);
    const flags = new Float32Array(count);
    const catIndex = new Float32Array(count);

    const famU32 = new Uint32Array(payloadBuffer, layout.familyCode!.offset, count);
    const flU32 = new Uint32Array(payloadBuffer, layout.flags!.offset, count);
    const idxU32 = new Uint32Array(payloadBuffer, layout.catalogIndex!.offset, count);

    this.catalogIndexToBufferIndex.clear();
    for (let i = 0; i < count; i++) {
      families[i] = famU32[i]!;
      flags[i] = flU32[i]!;
      const catalogIdx = idxU32[i]!;
      catIndex[i] = catalogIdx;
      this.catalogIndexToBufferIndex.set(catalogIdx, i);
    }

    this.geometry = new THREE.InstancedBufferGeometry();
    this.geometry.instanceCount = count;
    // A simple quad
    const baseGeometry = new THREE.PlaneGeometry(1, 1);
    this.geometry.index = baseGeometry.index;
    this.geometry.attributes.position = baseGeometry.attributes.position as THREE.BufferAttribute;

    this.geometry.setAttribute("equatorialDirection", new THREE.InstancedBufferAttribute(eqDirs as any, 3));
    this.geometry.setAttribute("northTangent", new THREE.InstancedBufferAttribute(nTans, 3));
    this.geometry.setAttribute("eastTangent", new THREE.InstancedBufferAttribute(eTans, 3));
    this.geometry.setAttribute("majorAxisArcmin", new THREE.InstancedBufferAttribute(majAx as any, 1));
    this.geometry.setAttribute("minorAxisArcmin", new THREE.InstancedBufferAttribute(minAx as any, 1));
    this.geometry.setAttribute("positionAngleDeg", new THREE.InstancedBufferAttribute(paDeg as any, 1));
    this.geometry.setAttribute("magnitude", new THREE.InstancedBufferAttribute(mags as any, 1));
    this.geometry.setAttribute("surfaceBrightness", new THREE.InstancedBufferAttribute(surfBr as any, 1));
    this.geometry.setAttribute("familyCode", new THREE.InstancedBufferAttribute(families as any, 1));
    this.geometry.setAttribute("flags", new THREE.InstancedBufferAttribute(flags as any, 1));
    this.geometry.setAttribute("catalogIndex", new THREE.InstancedBufferAttribute(catIndex as any, 1));

    const mat3 = new THREE.Matrix3();
    if (this.transformState && this.transformState.isValid) {
      mat3.copy(this.transformState.equatorialToThree);
    }

    this.material = new THREE.ShaderMaterial({
      vertexShader: VERTEX_SHADER,
      fragmentShader: FRAGMENT_SHADER,
      uniforms: {
        u_equatorialToENUMatrix: { value: mat3 },
        u_radius: { value: CELESTIAL_SCENE_RADIUS.distantSky },
        u_horizonTexture: { value: this.horizonState?.gpuUniformValues().texture ?? null },
        u_horizonSampleCount: { value: this.horizonState?.gpuUniformValues().sampleCount ?? 0 },
        u_horizonTextureWidth: { value: this.horizonState?.gpuUniformValues().textureWidth ?? 1 },
        u_horizonTextureHeight: { value: this.horizonState?.gpuUniformValues().textureHeight ?? 1 },
        u_horizonEnabled: { value: this.horizonState?.gpuUniformValues().enabled ?? 0 },
        u_zenithMagnitudeLimit: { value: this.currentVisibilityState?.zenithMagnitudeLimit ?? DEFAULT_SKY_VISIBILITY.zenithMagnitudeLimit },
        u_extinctionCoefficient: { value: this.currentVisibilityState?.extinctionCoefficient ?? DEFAULT_SKY_VISIBILITY.extinctionCoefficient },
        u_twilightSuppression: { value: this.currentVisibilityState?.twilightSuppression ?? DEFAULT_SKY_VISIBILITY.twilightSuppression },
        u_fadeWidthMag: { value: this.currentVisibilityState?.fadeWidthMag ?? DEFAULT_SKY_VISIBILITY.fadeWidthMag },
      },
      transparent: true,
      depthWrite: false,
      depthTest: true,
      blending: THREE.AdditiveBlending,
      side: THREE.DoubleSide,
    });

    this.mesh = new THREE.Mesh(this.geometry, this.material);
    this.mesh.name = "deepSkyInstancedMesh";
    this.mesh.frustumCulled = false;

    this.rootGroup.add(this.mesh);
    

    this.metadata = metadata;
    this.payloadBuffer = payloadBuffer;
    this.labels.registerLabels(metadata, payloadBuffer);
  }

  public disposeResource(): void {
    this.catalogIndexToBufferIndex.clear();
    if (this.mesh) {
      this.mesh.removeFromParent();
      this.mesh = null;
    }
    if (this.geometry) {
      this.geometry.dispose();
      this.geometry = null;
    }
    if (this.material) {
      this.material.dispose();
      this.material = null;
    }
  }

  public dispose(): void {
    this.horizonUnsubscribe?.();
    this.disposeResource();
    this.rootGroup.removeFromParent();
    this.labels.dispose();
  }

  private syncHorizonUniforms(): void {
    if (!this.material || this.horizonState === null) return;
    const values = this.horizonState.gpuUniformValues();
    this.material.uniforms["u_horizonTexture"]!.value = values.texture;
    this.material.uniforms["u_horizonSampleCount"]!.value = values.sampleCount;
    this.material.uniforms["u_horizonTextureWidth"]!.value = values.textureWidth;
    this.material.uniforms["u_horizonTextureHeight"]!.value = values.textureHeight;
    this.material.uniforms["u_horizonEnabled"]!.value = values.enabled;
    this.material.uniformsNeedUpdate = true;
  }
}
