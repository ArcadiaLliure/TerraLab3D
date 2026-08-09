import * as THREE from "three";

export const RENDERER_COLOR_POLICY = {
  outputColorSpace: THREE.SRGBColorSpace,
  toneMapping: THREE.NoToneMapping,
  toneMappingExposure: 1.0,
} as const;

/** Explicit Pas 8.7 baseline; photographic auto-exposure remains out of scope. */
export function applyRendererColorPolicy(renderer: THREE.WebGLRenderer): void {
  THREE.ColorManagement.enabled = true;
  renderer.outputColorSpace = RENDERER_COLOR_POLICY.outputColorSpace;
  renderer.toneMapping = RENDERER_COLOR_POLICY.toneMapping;
  renderer.toneMappingExposure = RENDERER_COLOR_POLICY.toneMappingExposure;
}
