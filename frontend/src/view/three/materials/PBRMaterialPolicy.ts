import * as THREE from "three";

export interface PBRMaterialPolicyMetrics {
  readonly materialBuildCount: number;
}

export interface PBRSurfaceMaps {
  readonly albedo?: THREE.Texture | null;
  readonly normal?: THREE.Texture | null;
  readonly roughness?: THREE.Texture | null;
  readonly metalness?: THREE.Texture | null;
  readonly ambientOcclusion?: THREE.Texture | null;
}

/**
 * Reusable material policy for local-world terrain and reference surfaces.
 *
 * Defaults are explicitly visual until DEM/orthophoto products provide real
 * surface parameters. Colour textures are sRGB; all material-data textures are
 * kept in NoColorSpace.
 */
export class PBRMaterialPolicy {
  readonly terrain: THREE.MeshStandardMaterial;
  readonly referenceBlue: THREE.MeshStandardMaterial;
  readonly referenceOrange: THREE.MeshStandardMaterial;
  private disposed = false;

  constructor() {
    this.terrain = new THREE.MeshStandardMaterial({
      color: 0x1a2a20,
      metalness: 0,
      roughness: 0.92,
      side: THREE.DoubleSide,
    });
    this.terrain.name = "technicalTerrainPBR";
    this.referenceBlue = new THREE.MeshStandardMaterial({
      color: 0x4488aa,
      metalness: 0,
      roughness: 0.62,
    });
    this.referenceBlue.name = "localReferenceBluePBR";
    this.referenceOrange = new THREE.MeshStandardMaterial({
      color: 0xcc8844,
      metalness: 0,
      roughness: 0.72,
    });
    this.referenceOrange.name = "localReferenceOrangePBR";
  }

  applyTerrainMaps(maps: PBRSurfaceMaps): void {
    this.terrain.map = markColorTexture(maps.albedo ?? null);
    this.terrain.normalMap = markDataTexture(maps.normal ?? null);
    this.terrain.roughnessMap = markDataTexture(maps.roughness ?? null);
    this.terrain.metalnessMap = markDataTexture(maps.metalness ?? null);
    this.terrain.aoMap = markDataTexture(maps.ambientOcclusion ?? null);
    this.terrain.needsUpdate = true;
  }

  metrics(): PBRMaterialPolicyMetrics {
    return { materialBuildCount: 3 };
  }

  dispose(): void {
    if (this.disposed) return;
    this.disposed = true;
    this.terrain.dispose();
    this.referenceBlue.dispose();
    this.referenceOrange.dispose();
  }
}

export function markColorTexture(texture: THREE.Texture | null): THREE.Texture | null {
  if (texture !== null) texture.colorSpace = THREE.SRGBColorSpace;
  return texture;
}

export function markDataTexture(texture: THREE.Texture | null): THREE.Texture | null {
  if (texture !== null) texture.colorSpace = THREE.NoColorSpace;
  return texture;
}

/** CPU-side validation helper matching the diffuse orientation used by PBR. */
export function pbrDiffuseResponse(
  normalENU: readonly [number, number, number],
  directionToSourceENU: readonly [number, number, number],
): number {
  const normalLength = Math.hypot(...normalENU);
  const lightLength = Math.hypot(...directionToSourceENU);
  if (normalLength <= Number.EPSILON || lightLength <= Number.EPSILON) return 0;
  const dot = normalENU.reduce(
    (sum, component, index) => sum + component * directionToSourceENU[index]!,
    0,
  );
  return Math.max(0, dot / (normalLength * lightLength));
}
