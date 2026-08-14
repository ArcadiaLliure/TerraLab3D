/**
 * Renderitzador del camp estel·lar cel·lar per a Three.js.
 *
 * Responsabilitats:
 * - Rep buffers binaris GPU-ready (`positions`, `magnitudes`, `colors`, `catalogIndices`).
 * - Manté els recursos persistents en memòria GPU (ZERO recàlcul de buffers per frame/moviment).
 * - S'afegix a `celestialRoot` (recentrat a càmera → zero paral·laxi local).
 * - Aplica la matriu de transformació equatorial→ENU `u_equatorialToENUMatrix` a tots els materials.
 * - Suporta toggles i limits de magnitud sense tocar la GPU.
 *
 * Pas 6 additions:
 * - `StarResourceEntry` ara inclou `version`, `catalogIndices` (Uint32Array canònic),
 *   `magnitudesArray` i `equatorialPositions` per al picking.
 * - Metadata tipada via `StarResourceMetadata`.
 * - Delegació de la matriu de transformació a `CelestialTransformState`.
 */

import * as THREE from "three";
import { STAR_FRAGMENT_SHADER, STAR_VERTEX_SHADER } from "./shaders/starShader";
import type { StarResourceMetadata } from "../../contracts/star_picking_contracts";
import type { SkyVisibilityState } from "../../contracts/sky_environment_contracts";
import { DEFAULT_SKY_VISIBILITY } from "../../contracts/sky_visibility_defaults";
import type { CelestialTransformState } from "./CelestialTransformState";

export interface StarResourceEntry {
  readonly resourceId: string;
  readonly version: string;
  readonly role: string;
  readonly starCount: number;
  readonly points: THREE.Points;
  readonly geometry: THREE.BufferGeometry;
  readonly material: THREE.ShaderMaterial;
  /** Uint32Array canònic — identitat de picking, NEVER float. */
  readonly catalogIndices: Uint32Array;
  /** Float32Array de magnituds — per al càlcul de mida al picker. */
  readonly magnitudesArray: Float32Array;
  /** Float32Array[N*3] de posicions equatorials — per al spatial index. */
  readonly equatorialPositions: Float32Array;
}

export class StarFieldRenderer {
  private readonly rootGroup = new THREE.Group();
  private readonly resources = new Map<string, StarResourceEntry>();
  private magnitudeLimit = 8.0;
  private pointScale = 1.0;
  private isVisible = true;
  private trailSuppressed = false;

  /** Shared celestial transform and visibility state. */
  private transformState: CelestialTransformState | null = null;
  private currentVisibilityState: SkyVisibilityState | null = null;

  constructor() {
    this.rootGroup.name = "starFieldRoot";
  }

  /** Connecta l'estat de transformació celeste compartit. */
  public setTransformState(state: CelestialTransformState): void {
    this.transformState = state;
  }

  public attachToParent(parentGroup: THREE.Group): void {
    parentGroup.add(this.rootGroup);
  }

  public detachFromParent(): void {
    this.rootGroup.removeFromParent();
  }

  public setVisible(visible: boolean): void {
    this.isVisible = visible;
    this.syncVisibility();
  }

  /** Keep catalog/picking state alive while trails own the stellar appearance. */
  public setTrailSuppressed(suppressed: boolean): void {
    this.trailSuppressed = suppressed;
    this.syncVisibility();
  }

  public get visible(): boolean {
    return this.isVisible;
  }

  public getMagnitudeLimit(): number {
    return this.magnitudeLimit;
  }

  public getPointScale(): number {
    return this.pointScale;
  }

  public setMagnitudeLimit(limit: number): void {
    this.magnitudeLimit = limit;
    // Ara aquest límit actua com a "límit dur" (hard cutoff)
    // El límit efectiu (LP + extinció) es controla via u_zenithMagnitudeLimit
    for (const entry of this.resources.values()) {
      uniform<number>(entry.material, "u_magnitudeLimit").value = limit;
      entry.material.uniformsNeedUpdate = true;
    }
  }

  /** Actualitza els paràmetres de visibilitat atmosfèrica i contaminació lumínica. */
  public updateVisibilityUniforms(state: SkyVisibilityState): void {
    this.currentVisibilityState = state;
    for (const entry of this.resources.values()) {
      uniform<number>(entry.material, "u_zenithMagnitudeLimit").value = state.zenithMagnitudeLimit;
      uniform<number>(entry.material, "u_extinctionCoefficient").value = state.extinctionCoefficient;
      uniform<number>(entry.material, "u_twilightSuppression").value = state.twilightSuppression;
      uniform<number>(entry.material, "u_fadeWidthMag").value = state.fadeWidthMag;
      entry.material.uniformsNeedUpdate = true;
    }
  }

  public updateCelestialTransform(generation: number, matrix3x3: number[]): void {
    if (!matrix3x3 || matrix3x3.length !== 9) return;

    // Si tenim transformState compartit, delegar-hi l'update
    if (this.transformState) {
      this.transformState.update(generation, matrix3x3);
    } else {
      // Si no tenim transformState compartit, fer-ho manualment (només usat en tests)
      for (const entry of this.resources.values()) {
        const mat3 = uniform<THREE.Matrix3>(entry.material, "u_equatorialToENUMatrix").value;
        const matrix = matrix3x3 as [number, number, number, number, number, number, number, number, number];
        mat3.set(
          matrix[0], matrix[1], matrix[2],
          matrix[3], matrix[4], matrix[5],
          matrix[6], matrix[7], matrix[8],
        );
        entry.material.uniformsNeedUpdate = true;
      }
    }
  }

  public interpolate(timestampMs: number): void {
    if (!this.transformState || !this.transformState.isValid) return;

    this.transformState.interpolate(timestampMs);

    const mArray = this.transformState.getMatrix3x3Array();
    for (const entry of this.resources.values()) {
      const mat3 = uniform<THREE.Matrix3>(entry.material, "u_equatorialToENUMatrix").value;
      mat3.set(
        mArray[0]!, mArray[1]!, mArray[2]!,
        mArray[3]!, mArray[4]!, mArray[5]!,
        mArray[6]!, mArray[7]!, mArray[8]!,
      );
      entry.material.uniformsNeedUpdate = true;
    }
  }

  public registerBinaryResource(metadata: StarResourceMetadata | any, payloadBuffer: ArrayBuffer): void {
    const resourceId = metadata.resourceId as string;
    const version = (metadata.version ?? "") as string;
    const role = metadata.role as string;
    const starCount = metadata.starCount as number;
    const layout = metadata.bufferLayout;

    if (!resourceId || !starCount || !layout) {
      console.error("MGP: [StarFieldRenderer] [registerBinaryResource] [Metadata binària invàlida]", metadata);
      return;
    }

    // Si ja existia una versió anterior d'aquest recurs, reemplaçar-la netament
    if (this.resources.has(resourceId)) {
      const existing = this.resources.get(resourceId)!;
      if (existing.version === version) {
        // Mateixa versió — registre idempotent, no reupload
        console.log(
          `MGP: [StarFieldRenderer] [registerBinaryResource] [Recurs ${resourceId} v${version} ja registrat — idempotent]`,
        );
        return;
      }
      this.disposeResource(resourceId);
    }

    // Desglossar buffers des de l'ArrayBuffer segons el layout
    const posOffset = layout.positions.offset;
    const posLen = layout.positions.length;
    const magOffset = layout.magnitudes.offset;
    const magLen = layout.magnitudes.length;
    const colOffset = layout.colors.offset;
    const colLen = layout.colors.length;
    const idxOffset = layout.catalogIndices.offset;
    const idxLen = layout.catalogIndices.length;

    const positions = new Float32Array(payloadBuffer, posOffset, posLen / 4);
    const magnitudes = new Float32Array(payloadBuffer, magOffset, magLen / 4);

    // Color del catàleg arriba en sRGB uint8. Convertim una sola vegada a
    // linear-sRGB perquè el shader faci exactament una codificació de sortida.
    const u8Colors = new Uint8Array(payloadBuffer, colOffset, colLen);
    const floatColors = new Float32Array(starCount * 3);
    for (let i = 0; i < u8Colors.length; i++) {
      floatColors[i] = srgbChannelToLinear(u8Colors[i]! / 255.0);
    }

    // Catalog indices: conservar Uint32Array canònic per al picking
    const u32Indices = new Uint32Array(payloadBuffer, idxOffset, idxLen / 4);

    // Float32 per a GPU (WebGL attribute) — NOMÉS per render, no per identitat
    const floatIndices = new Float32Array(starCount);
    for (let i = 0; i < u32Indices.length; i++) {
      floatIndices[i] = u32Indices[i]!;
    }

    // Crear BufferGeometry
    const geometry = new THREE.BufferGeometry();
    geometry.setAttribute("position", new THREE.BufferAttribute(positions, 3));
    geometry.setAttribute("magnitude", new THREE.BufferAttribute(magnitudes, 1));
    geometry.setAttribute("color", new THREE.BufferAttribute(floatColors, 3));
    geometry.setAttribute("catalogIndex", new THREE.BufferAttribute(floatIndices, 1));

    // Crear Matriu 3x3 inicial des de CelestialTransformState o identitat
    const mat3 = new THREE.Matrix3();
    if (this.transformState && this.transformState.isValid) {
      mat3.copy(this.transformState.equatorialToThree);
    }

    // Crear ShaderMaterial
    const material = new THREE.ShaderMaterial({
      vertexShader: STAR_VERTEX_SHADER,
      fragmentShader: STAR_FRAGMENT_SHADER,
      uniforms: {
        u_equatorialToENUMatrix: { value: mat3 },
        u_magnitudeLimit: { value: this.magnitudeLimit },
        u_pointScale: { value: this.pointScale },
        u_devicePixelRatio: { value: window.devicePixelRatio || 1.0 },
        u_radius: { value: 1000000.0 }, // Esfera cel·lar a l'infinit (1000km)
        u_cameraHeight: { value: 0.0 },
        // Visibilitat (Pas 7) - valors per defecte o l'últim rebut
        u_zenithMagnitudeLimit: { value: this.currentVisibilityState?.zenithMagnitudeLimit ?? DEFAULT_SKY_VISIBILITY.zenithMagnitudeLimit },
        u_extinctionCoefficient: { value: this.currentVisibilityState?.extinctionCoefficient ?? DEFAULT_SKY_VISIBILITY.extinctionCoefficient },
        u_twilightSuppression: { value: this.currentVisibilityState?.twilightSuppression ?? DEFAULT_SKY_VISIBILITY.twilightSuppression },
        u_fadeWidthMag: { value: this.currentVisibilityState?.fadeWidthMag ?? DEFAULT_SKY_VISIBILITY.fadeWidthMag },
      },
      transparent: true,
      depthWrite: false,
      depthTest: true,
      blending: THREE.AdditiveBlending,
    });

    const points = new THREE.Points(geometry, material);
    points.name = `starPoints_${resourceId}`;
    points.frustumCulled = false; // No cullar a nivell d'objecte; el shader retalla

    this.rootGroup.add(points);

    // Conservar Uint32Array canònic, magnituds i posicions per al picking
    const catalogIndicesCopy = new Uint32Array(u32Indices);
    const magnitudesCopy = new Float32Array(magnitudes);
    const positionsCopy = new Float32Array(positions);

    const entry: StarResourceEntry = {
      resourceId,
      version,
      role,
      starCount,
      points,
      geometry,
      material,
      catalogIndices: catalogIndicesCopy,
      magnitudesArray: magnitudesCopy,
      equatorialPositions: positionsCopy,
    };
    this.resources.set(resourceId, entry);

    console.log(
      `MGP: [StarFieldRenderer] [registerBinaryResource] [Recurs registrat a VRAM: ${resourceId} v${version} (${starCount} estrelles, role=${role})]`,
    );
  }

  public updateViewport(dpr: number): void {
    for (const entry of this.resources.values()) {
      uniform<number>(entry.material, "u_devicePixelRatio").value = dpr;
      entry.material.uniformsNeedUpdate = true;
    }
  }

  public updateCameraHeight(height: number): void {
    for (const entry of this.resources.values()) {
      uniform<number>(entry.material, "u_cameraHeight").value = height;
      entry.material.uniformsNeedUpdate = true;
    }
  }

  /** Retorna tots els recursos registrats (lectura). */
  public getResources(): ReadonlyMap<string, StarResourceEntry> {
    return this.resources;
  }

  /** Retorna un recurs per ID, o undefined. */
  public getResource(resourceId: string): StarResourceEntry | undefined {
    return this.resources.get(resourceId);
  }

  public disposeResource(resourceId: string): void {
    const entry = this.resources.get(resourceId);
    if (!entry) return;

    entry.points.removeFromParent();
    entry.geometry.dispose();
    entry.material.dispose();
    this.resources.delete(resourceId);
  }

  public dispose(): void {
    for (const resourceId of Array.from(this.resources.keys())) {
      this.disposeResource(resourceId);
    }
    this.rootGroup.removeFromParent();
  }

  private syncVisibility(): void {
    this.rootGroup.visible = this.isVisible && !this.trailSuppressed;
  }
}

function uniform<T>(material: THREE.ShaderMaterial, name: string): THREE.IUniform<T> {
  const value = material.uniforms[name];
  if (value === undefined) throw new Error(`Missing star shader uniform: ${name}`);
  return value as THREE.IUniform<T>;
}

export function srgbChannelToLinear(value: number): number {
  return value <= 0.04045
    ? value / 12.92
    : Math.pow((value + 0.055) / 1.055, 2.4);
}
