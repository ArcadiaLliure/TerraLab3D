/**
 * Renderitzador del camp estel·lar cel·lar per a Three.js.
 *
 * Responsabilitats:
 * - Rep buffers binaris GPU-ready (`positions`, `magnitudes`, `colors`, `catalogIndices`).
 * - Manté els recursos persistents en memòria GPU (ZERO recàlcul de buffers per frame/moviment).
 * - S'afegix a `celestialRoot` (recentrat a càmera → zero paral·laxi local).
 * - Aplica la matriu de transformació equatorial→ENU `u_equatorialToENUMatrix` a tots els materials.
 * - Suporta toggles i limits de magnitud sense tocar la GPU.
 */

import * as THREE from "three";
import { STAR_FRAGMENT_SHADER, STAR_VERTEX_SHADER } from "./shaders/starShader";

export interface StarResourceEntry {
  readonly resourceId: string;
  readonly role: string;
  readonly starCount: number;
  readonly points: THREE.Points;
  readonly geometry: THREE.BufferGeometry;
  readonly material: THREE.ShaderMaterial;
}

export class StarFieldRenderer {
  private readonly rootGroup = new THREE.Group();
  private readonly resources = new Map<string, StarResourceEntry>();
  private currentMatrix3x3: number[] = [
    1, 0, 0,
    0, 1, 0,
    0, 0, 1,
  ];
  private magnitudeLimit = 8.0;
  private pointScale = 1.0;
  private isVisible = true;

  constructor() {
    this.rootGroup.name = "starFieldRoot";
  }

  public attachToParent(parentGroup: THREE.Group): void {
    parentGroup.add(this.rootGroup);
  }

  public detachFromParent(): void {
    this.rootGroup.removeFromParent();
  }

  public setVisible(visible: boolean): void {
    this.isVisible = visible;
    this.rootGroup.visible = visible;
  }

  public get visible(): boolean {
    return this.isVisible;
  }

  public setMagnitudeLimit(limit: number): void {
    this.magnitudeLimit = limit;
    for (const entry of this.resources.values()) {
      entry.material.uniforms.u_magnitudeLimit.value = limit;
      entry.material.uniformsNeedUpdate = true;
    }
  }

  public updateCelestialTransform(generation: number, matrix3x3: number[]): void {
    if (!matrix3x3 || matrix3x3.length !== 9) return;
    this.currentMatrix3x3 = [...matrix3x3];

    // Actualitzar la matriu uniform en tots els materials residents
    for (const entry of this.resources.values()) {
      const mat3 = entry.material.uniforms.u_equatorialToENUMatrix.value as THREE.Matrix3;
      // Matrix3.set pren els 9 elements row-major
      mat3.set(
        matrix3x3[0], matrix3x3[1], matrix3x3[2],
        matrix3x3[3], matrix3x3[4], matrix3x3[5],
        matrix3x3[6], matrix3x3[7], matrix3x3[8],
      );
      entry.material.uniformsNeedUpdate = true;
    }
  }

  public registerBinaryResource(metadata: any, payloadBuffer: ArrayBuffer): void {
    const resourceId = metadata.resourceId as string;
    const role = metadata.role as string;
    const starCount = metadata.starCount as number;
    const layout = metadata.bufferLayout;

    if (!resourceId || !starCount || !layout) {
      console.error("[StarFieldRenderer] Metadata binària invàlida:", metadata);
      return;
    }

    // Si ja existia una versió anterior d'aquest recurs, reemplaçar-la netament
    if (this.resources.has(resourceId)) {
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

    // Color: convertir uint8 [0..255] a Float32Array [0..1]
    const u8Colors = new Uint8Array(payloadBuffer, colOffset, colLen);
    const floatColors = new Float32Array(starCount * 3);
    for (let i = 0; i < u8Colors.length; i++) {
      floatColors[i] = u8Colors[i] / 255.0;
    }

    // Catalog indices: uint32 -> Float32Array (per compatibilitat WebGL1/2)
    const u32Indices = new Uint32Array(payloadBuffer, idxOffset, idxLen / 4);
    const floatIndices = new Float32Array(starCount);
    for (let i = 0; i < u32Indices.length; i++) {
      floatIndices[i] = u32Indices[i];
    }

    // Crear BufferGeometry
    const geometry = new THREE.BufferGeometry();
    geometry.setAttribute("position", new THREE.BufferAttribute(positions, 3));
    geometry.setAttribute("magnitude", new THREE.BufferAttribute(magnitudes, 1));
    geometry.setAttribute("color", new THREE.BufferAttribute(floatColors, 3));
    geometry.setAttribute("catalogIndex", new THREE.BufferAttribute(floatIndices, 1));

    // Crear Matriu 3x3 inicial
    const mat3 = new THREE.Matrix3();
    mat3.set(
      this.currentMatrix3x3[0], this.currentMatrix3x3[1], this.currentMatrix3x3[2],
      this.currentMatrix3x3[3], this.currentMatrix3x3[4], this.currentMatrix3x3[5],
      this.currentMatrix3x3[6], this.currentMatrix3x3[7], this.currentMatrix3x3[8],
    );

    // Crear ShaderMaterial
    const material = new THREE.ShaderMaterial({
      vertexShader: STAR_VERTEX_SHADER,
      fragmentShader: STAR_FRAGMENT_SHADER,
      uniforms: {
        u_equatorialToENUMatrix: { value: mat3 },
        u_magnitudeLimit: { value: this.magnitudeLimit },
        u_pointScale: { value: this.pointScale },
        u_devicePixelRatio: { value: window.devicePixelRatio || 1.0 },
        u_radius: { value: 950.0 }, // Esfera cel·lar recentrada a 950m
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

    const entry: StarResourceEntry = {
      resourceId,
      role,
      starCount,
      points,
      geometry,
      material,
    };
    this.resources.set(resourceId, entry);

    console.log(
      `[StarFieldRenderer] Recurs estel·lar registrat a VRAM: ${resourceId} (${starCount} estrelles, role=${role})`,
    );
  }

  public updateViewport(dpr: number): void {
    for (const entry of this.resources.values()) {
      entry.material.uniforms.u_devicePixelRatio.value = dpr;
      entry.material.uniformsNeedUpdate = true;
    }
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
}
