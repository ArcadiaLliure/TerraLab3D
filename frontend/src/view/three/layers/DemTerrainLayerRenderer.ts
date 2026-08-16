import * as THREE from "three";
import type { TerrainNavigationSampling } from "../terrain/TechnicalTerrainSampler";
import { TerrainDistanceFog } from "../terrain/TerrainDistanceFog";

export const DEM_TERRAIN_RENDER_ORDER = -900;
export const DEM_COVERAGE_FOG_RENDER_ORDER = -899;

export type SurfacePresentationMode = "base" | "categorical_original";

export interface DemTerrainLayerMetrics {
  readonly geometryBuildCount: number;
  readonly geometryUploadBytes: number;
  readonly vertexCount: number;
  readonly triangleCount: number;
  readonly activeMeshCount: number;
  readonly semanticAttributeBytes: number;
  // Surface metrics (Pas 17)
  readonly surfaceResourceApplyCount: number;
  readonly surfaceStaleResourceCount: number;
  readonly surfaceActiveResourceCount: number;
  readonly surfaceModeSwitchCount: number;
  readonly surfaceGeometryRebuildsCausedByStyle: 0;
  readonly surfacePaletteUploadBytes: number;
}

export interface DemTerrainNavigationLayer {
  readonly contentKey: string;
  readonly mesh: THREE.Mesh;
  readonly sampling: TerrainNavigationSampling | null;
}

export interface DemTerrainStreamingCacheOptions {
  readonly maxMeshCount?: number;
  readonly maxGpuBytes?: number;
}

interface StreamingMeshEntry extends DemTerrainNavigationLayer {
  readonly version: number;
  readonly gpuBytes: number;
  surfaceVersion?: number;
}

const DEFAULT_STREAMING_MESH_COUNT = 12;
const DEFAULT_STREAMING_GPU_BYTES = 256 * 1024 * 1024;
const MAX_PALETTE_SIZE = 256;

export interface SurfacePaletteItem {
  readonly paletteIndex: number;
  readonly classId: number;
  readonly rgba: readonly [number, number, number, number];
}

/**
 * Persistent Three.js presentation of the real observer-relative DEM mesh.
 *
 * Implements custom shader palette lookup for categorical land cover styles
 * and terrain-only distance fog without modifying DEM geometry or global scene.fog.
 */
export class DemTerrainLayerRenderer {
  readonly root = new THREE.Group();
  private readonly distanceFog = new TerrainDistanceFog();
  private currentSurfaceMode: SurfacePresentationMode = "categorical_original";



  private readonly sharedShaderUniforms = {
    uSurfaceMode: { value: 1 }, // 0 = base, 1 = categorical_original
    ...this.distanceFog.uniforms,
  };

  private readonly material: THREE.MeshStandardMaterial;
  private readonly streamingMaterial: THREE.MeshStandardMaterial;

  private readonly coverageFogMaterial = new THREE.MeshBasicMaterial({
    color: 0x9db2c9,
    side: THREE.DoubleSide,
    transparent: true,
    opacity: 0.42,
    depthTest: true,
    depthWrite: false,
  });

  private mesh: THREE.Mesh<THREE.BufferGeometry, THREE.MeshStandardMaterial> | null = null;
  private readonly streamingMeshes = new Map<string, StreamingMeshEntry>();
  private coverageFog: THREE.Mesh<THREE.BufferGeometry, THREE.MeshBasicMaterial> | null = null;
  private coverageFogTopOffsets: Uint32Array<ArrayBufferLike> = new Uint32Array(0);
  private coverageFogBottomHeights: Float32Array<ArrayBufferLike> = new Float32Array(0);
  private coverageFogTopY = Number.NaN;
  private navigationSampling: TerrainNavigationSampling | null = null;
  private activeVersion = -1;
  private activeContentKey = "";
  private activeSurfaceVersion = -1;
  private readonly maxStreamingMeshCount: number;
  private readonly maxStreamingGpuBytes: number;
  private streamingGpuBytes = 0;
  private disposed = false;

  // Metrics
  private geometryBuildCount = 0;
  private geometryUploadBytes = 0;
  private vertexCount = 0;
  private triangleCount = 0;
  private semanticAttributeBytes = 0;
  private surfaceResourceApplyCount = 0;
  private surfaceStaleResourceCount = 0;
  private surfaceModeSwitchCount = 0;
  private surfacePaletteUploadBytes = 0;

  constructor(parent: THREE.Object3D, cache: DemTerrainStreamingCacheOptions = {}) {
    this.maxStreamingMeshCount = positiveInteger(cache.maxMeshCount, DEFAULT_STREAMING_MESH_COUNT);
    this.maxStreamingGpuBytes = positiveInteger(cache.maxGpuBytes, DEFAULT_STREAMING_GPU_BYTES);


    this.material = this.createTerrainMaterial(false);
    this.streamingMaterial = this.createTerrainMaterial(true);

    this.root.name = "demTerrainRoot";
    parent.add(this.root);
  }

  getDistanceFog(): TerrainDistanceFog {
    return this.distanceFog;
  }

  getSurfaceMode(): SurfacePresentationMode {
    return this.currentSurfaceMode;
  }

  /**
   * Switch visual style between BASE and CATEGORICAL_ORIGINAL without
   * touching or rebuilding geometry, position, normal or index buffers.
   */
  setSurfaceMode(mode: SurfacePresentationMode): void {
    this.currentSurfaceMode = mode;
    this.sharedShaderUniforms.uSurfaceMode.value = mode === "categorical_original" ? 1 : 0;
    this.surfaceModeSwitchCount++;
  }

  /**
   * Apply DEM terrain mesh binary resource.
   */
  applyBinaryResource(metadata: any, payload: ArrayBuffer): boolean {
    if (metadata?.role === "surface_resource") {
      return this.applySurfaceResource(metadata, payload);
    }
    const isStreamingChunk = metadata?.role === "terrain_stream_chunk";
    if (this.disposed || (!isStreamingChunk && metadata?.role !== "terrain_mesh")) return false;
    if (metadata.cleared === true) {
      if (isStreamingChunk) this.clearStreaming();
      else this.clear();
      return true;
    }
    const version = Number(metadata.version);
    const contentKey = String(metadata.contentKey ?? "");
    const vertexCount = Number(metadata.vertexCount);
    const indexCount = Number(metadata.indexCount);
    const navigationSampling = parseNavigationSampling(metadata.navigationSampling);
    if (
      !Number.isSafeInteger(version)
      || !Number.isSafeInteger(vertexCount)
      || !Number.isSafeInteger(indexCount)
      || vertexCount <= 0
      || indexCount <= 0
      || !metadata.bufferLayout
    ) {
      return false;
    }
    if (isStreamingChunk && contentKey.length === 0) return false;
    const activeStream = isStreamingChunk ? this.streamingMeshes.get(contentKey) : undefined;
    if (activeStream && version < activeStream.version) return false;
    if (activeStream && version === activeStream.version) return true;
    if (!isStreamingChunk && version < this.activeVersion) return false;
    if (!isStreamingChunk && version === this.activeVersion && contentKey === this.activeContentKey) return true;

    const layout = metadata.bufferLayout;
    try {
      const position = viewFloat32(payload, layout.position, vertexCount * 3);
      const normal = viewFloat32(payload, layout.normal, vertexCount * 3);
      const color = viewUint8(payload, layout.color, vertexCount * 4);
      const index = viewUint32(payload, layout.index, indexCount);

      const geometry = new THREE.BufferGeometry();
      geometry.setAttribute("position", new THREE.BufferAttribute(position, 3));
      geometry.setAttribute("normal", new THREE.BufferAttribute(normal, 3));
      geometry.setAttribute("color", new THREE.BufferAttribute(color, 4, true));
      // UV initialization required by shader, will be updated by surface resource layer
      geometry.setAttribute("landcoverUV", new THREE.BufferAttribute(new Float32Array(vertexCount * 2), 2, false));
      geometry.setIndex(new THREE.BufferAttribute(index, 1));
      geometry.computeBoundingSphere();
      geometry.computeBoundingBox();

      const replacement = new THREE.Mesh(
        geometry,
        isStreamingChunk ? this.streamingMaterial.clone() : this.material,
      );
      replacement.name = isStreamingChunk ? "demTerrainStreamChunk" : "demTerrainMeshV3";
      // Streaming detail chunks benefit from frustum culling
      replacement.frustumCulled = isStreamingChunk;
      replacement.receiveShadow = true;
      replacement.castShadow = false;
      replacement.renderOrder = DEM_TERRAIN_RENDER_ORDER + Number(isStreamingChunk);

      const previous = isStreamingChunk ? activeStream?.mesh ?? null : this.mesh;
      if (isStreamingChunk) {
        if (activeStream) {
          this.streamingMeshes.delete(contentKey);
          this.streamingGpuBytes -= activeStream.gpuBytes;
        }
        this.streamingMeshes.set(contentKey, {
          contentKey,
          version,
          mesh: replacement,
          sampling: navigationSampling,
          gpuBytes: payload.byteLength,
        });
        this.streamingGpuBytes += payload.byteLength;
      } else {
        this.mesh = replacement;
        this.navigationSampling = navigationSampling;
        this.activeVersion = version;
        this.activeContentKey = contentKey;
        this.clearStreaming();
        this.rebuildCoverageFog(geometry, navigationSampling);
        if (this.lastSurfaceResource) {
          this.applySurfaceResource(this.lastSurfaceResource.metadata, this.lastSurfaceResource.payload);
        }
      }
      this.root.add(replacement);
      previous?.removeFromParent();
      previous?.geometry.dispose();
      if (isStreamingChunk) {
        if (previous) disposeStreamingMaterial(previous);
        this.trimStreamingCache(contentKey);
        this.refreshStreamingDepthBias();
      }
      this.vertexCount = this.mesh?.geometry.getAttribute("position")?.count ?? 0;
      this.triangleCount = Math.floor((this.mesh?.geometry.getIndex()?.count ?? 0) / 3);
      this.semanticAttributeBytes = semanticBytes(this.mesh);
      this.geometryUploadBytes += payload.byteLength;
      this.geometryBuildCount++;
      return true;
    } catch (error) {
      console.warn("[DemTerrainLayerRenderer] invalid terrain mesh resource", error);
      return false;
    }
  }

  /**
   * Apply companion categorical surface binary resource.
   * Updates only semantic class attributes and palette without touching geometry.
   */
  private lastSurfaceResource: { metadata: any; payload: ArrayBuffer } | null = null;

  private applySurfaceResource(metadata: any, payload: ArrayBuffer): boolean {
    const version = Number(metadata.version ?? metadata.generation ?? metadata.compatibleTerrainVersion ?? 0);
    const contentKey = String(metadata.terrainContentKey ?? metadata.contentKey ?? "");
    const vertexCount = Number(metadata.vertexCount);
    if (!Number.isSafeInteger(version) || !Number.isSafeInteger(vertexCount) || vertexCount <= 0) {
      this.surfaceStaleResourceCount++;
      return false;
    }

    this.lastSurfaceResource = { metadata, payload };

    // Locate target mesh (either base mesh or streaming chunk)
    let targetMesh: THREE.Mesh<THREE.BufferGeometry> | null = null;
    if (this.mesh && (this.activeContentKey === contentKey || contentKey === "")) {
      if (version < this.activeSurfaceVersion) {
        this.surfaceStaleResourceCount++;
        return false;
      }
      this.activeSurfaceVersion = version;
      targetMesh = this.mesh;
    } else {
      const entry = this.streamingMeshes.get(contentKey);
      if (entry) {
        if (entry.surfaceVersion && version < entry.surfaceVersion) {
          this.surfaceStaleResourceCount++;
          return false;
        }
        entry.surfaceVersion = version;
        targetMesh = entry.mesh;
      }
    }

    if (!targetMesh) {
      this.surfaceStaleResourceCount++;
      return false;
    }

    const layout = metadata.bufferLayout;
    if (!layout?.classId || !layout?.colorRgba) {
      console.warn("[DemTerrainLayerRenderer] Mismatched layout: ", layout);
      return false;
    }

    try {
      const classIds = viewUint16(payload, layout.classId, vertexCount);
      const sourceIds = viewInt16(payload, layout.sourceId, vertexCount);
      const colorsRgba = viewUint8(payload, layout.colorRgba, vertexCount * 4);

      console.log(`[DemTerrainLayerRenderer] Aplicant colors per ${vertexCount} vèrtexs!`);

      const geometry = targetMesh.geometry;

      geometry.setAttribute("terrainClassId", new THREE.BufferAttribute(classIds, 1, false));
      geometry.setAttribute("terrainSourceId", new THREE.BufferAttribute(sourceIds, 1, false));
      geometry.setAttribute("customColor", new THREE.BufferAttribute(colorsRgba, 4, true));

      const material = targetMesh.material as THREE.MeshStandardMaterial;
      if (material.map) {
         material.map = null;
         material.needsUpdate = true;
      }

      this.surfaceResourceApplyCount++;
      return true;
    } catch (error) {
      console.warn("[DemTerrainLayerRenderer] invalid surface resource", error);
      return false;
    }
  }

  private updatePaletteData(palette: readonly SurfacePaletteItem[]): void {
     // Obsolete amb el CustomColor local
  }

  private createTerrainMaterial(isStreaming: boolean): THREE.MeshStandardMaterial {
    const mat = new THREE.MeshStandardMaterial({
      vertexColors: true,
      roughness: 1,
      metalness: 0,
      emissive: new THREE.Color(0x07111a),
      emissiveIntensity: 0.055,
      side: THREE.FrontSide,
      ...(isStreaming
        ? {
            polygonOffset: true,
            polygonOffsetFactor: -1,
            polygonOffsetUnits: -1,
          }
        : {}),
    });

    mat.customProgramCacheKey = () => (isStreaming ? "dem_terrain_stream_v1" : "dem_terrain_main_v1");

    const uniforms = this.sharedShaderUniforms;

    mat.onBeforeCompile = (shader) => {
      // Connect shared uniforms
      Object.assign(shader.uniforms, uniforms);

      // Vertex shader modifications
      shader.vertexShader = shader.vertexShader.replace(
        "#include <common>",
        `
        #include <common>
        attribute vec4 customColor;
        flat varying vec4 vCustomColor;
        varying float vWorldDistance;
        `,
      );

      shader.vertexShader = shader.vertexShader.replace(
        "#include <begin_vertex>",
        `
        #include <begin_vertex>
        vCustomColor = customColor;
        vec4 worldPos = modelMatrix * vec4(transformed, 1.0);
        vWorldDistance = length(worldPos.xyz - cameraPosition);
        `,
      );

      // Fragment shader modifications
      shader.fragmentShader = shader.fragmentShader.replace(
        "#include <common>",
        `
        #include <common>
        uniform int uSurfaceMode;
        uniform int uTerrainFogEnabled;
        uniform vec3 uTerrainFogColor;
        uniform float uTerrainFogNear;
        uniform float uTerrainFogFar;
        flat varying vec4 vCustomColor;
        varying float vWorldDistance;
        `,
      );

      shader.fragmentShader = shader.fragmentShader.replace(
        "#include <color_fragment>",
        `
        #include <color_fragment>
        if (uSurfaceMode == 1) {
            // Mode categòric: usar el color del vertex si és vàlid
            if (vCustomColor.a > 0.0) {
                diffuseColor.rgb = vCustomColor.rgb;
            } else {
                // Vèrtex sense classe assignada → verd fallback
                diffuseColor.rgb = vec3(0.15, 0.35, 0.12);
            }
        } else {
            // Mode BASE (relleu): SEMPRE verd, ignorant qualsevol color residual
            diffuseColor.rgb = vec3(0.15, 0.35, 0.12);
        }
        `,
      );

      // Apply terrain-only distance fog at the end of fragment shader
      shader.fragmentShader = shader.fragmentShader.replace(
        "#include <dithering_fragment>",
        `
        #include <dithering_fragment>
        if (uTerrainFogEnabled == 1 && vWorldDistance > uTerrainFogNear) {
          float fogFactor = clamp((vWorldDistance - uTerrainFogNear) / max(1.0, (uTerrainFogFar - uTerrainFogNear)), 0.0, 1.0);
          gl_FragColor.rgb = mix(gl_FragColor.rgb, uTerrainFogColor, fogFactor * 0.85);
        }
        `,
      );
    };

    return mat;
  }

  metrics(): DemTerrainLayerMetrics {
    let streamingVertices = 0;
    let streamingTriangles = 0;
    let streamingSemanticBytes = 0;
    for (const entry of this.streamingMeshes.values()) {
      streamingVertices += entry.mesh.geometry.getAttribute("position")?.count ?? 0;
      streamingTriangles += Math.floor((entry.mesh.geometry.getIndex()?.count ?? 0) / 3);
      streamingSemanticBytes += semanticBytes(entry.mesh);
    }
    return {
      geometryBuildCount: this.geometryBuildCount,
      geometryUploadBytes: this.geometryUploadBytes,
      vertexCount: this.vertexCount + streamingVertices,
      triangleCount: this.triangleCount + streamingTriangles,
      activeMeshCount: Number(this.mesh !== null) + this.streamingMeshes.size,
      semanticAttributeBytes: this.semanticAttributeBytes + streamingSemanticBytes,
      surfaceResourceApplyCount: this.surfaceResourceApplyCount,
      surfaceStaleResourceCount: this.surfaceStaleResourceCount,
      surfaceActiveResourceCount: Number(this.mesh !== null) + this.streamingMeshes.size,
      surfaceModeSwitchCount: this.surfaceModeSwitchCount,
      surfaceGeometryRebuildsCausedByStyle: 0,
      surfacePaletteUploadBytes: this.surfacePaletteUploadBytes,
    };
  }

  getNavigationMesh(): THREE.Mesh | null {
    return this.mesh;
  }

  getNavigationSampling(): TerrainNavigationSampling | null {
    return this.navigationSampling;
  }

  getStreamingNavigationMesh(): THREE.Mesh | null {
    return this.latestStreamingEntry()?.mesh ?? null;
  }

  getStreamingNavigationSampling(): TerrainNavigationSampling | null {
    return this.latestStreamingEntry()?.sampling ?? null;
  }

  getStreamingNavigationLayers(): readonly DemTerrainNavigationLayer[] {
    return Array.from(this.streamingMeshes.values(), ({ contentKey, mesh, sampling }) => ({
      contentKey,
      mesh,
      sampling,
    }));
  }

  getGotoTargetMeshes(): readonly THREE.Mesh[] {
    const meshes: THREE.Mesh[] = [];
    if (this.mesh) meshes.push(this.mesh);
    for (const entry of this.streamingMeshes.values()) meshes.push(entry.mesh);
    return meshes;
  }

  updateCoverageFogTop(cameraUpM: number): void {
    const fog = this.coverageFog;
    if (!fog || !Number.isFinite(cameraUpM) || Math.abs(cameraUpM - this.coverageFogTopY) < 0.05) return;
    const position = fog.geometry.getAttribute("position") as THREE.BufferAttribute | undefined;
    if (!position) return;
    const values = position.array as Float32Array;
    for (let index = 0; index < this.coverageFogTopOffsets.length; index++) {
      values[this.coverageFogTopOffsets[index]!] = Math.max(
        cameraUpM,
        this.coverageFogBottomHeights[index]! + 2.0,
      );
    }
    position.needsUpdate = true;
    this.coverageFogTopY = cameraUpM;
  }

  dispose(): void {
    if (this.disposed) return;
    this.disposed = true;
    this.clear();
    this.paletteTexture.dispose();
    this.material.dispose();
    this.streamingMaterial.dispose();
    this.coverageFogMaterial.dispose();
    this.root.removeFromParent();
  }

  private clear(): void {
    this.clearCoverageFog();
    this.mesh?.removeFromParent();
    this.mesh?.geometry.dispose();
    this.mesh = null;
    this.navigationSampling = null;
    this.activeVersion = -1;
    this.activeContentKey = "";
    this.activeSurfaceVersion = -1;
    this.vertexCount = 0;
    this.triangleCount = 0;
    this.semanticAttributeBytes = 0;
    this.clearStreaming();
  }

  private clearStreaming(): void {
    for (const entry of this.streamingMeshes.values()) {
      entry.mesh.removeFromParent();
      entry.mesh.geometry.dispose();
      disposeStreamingMaterial(entry.mesh);
    }
    this.streamingMeshes.clear();
    this.streamingGpuBytes = 0;
  }

  private latestStreamingEntry(): StreamingMeshEntry | null {
    let latest: StreamingMeshEntry | null = null;
    for (const entry of this.streamingMeshes.values()) latest = entry;
    return latest;
  }

  private trimStreamingCache(protectedContentKey: string): void {
    while (
      this.streamingMeshes.size > this.maxStreamingMeshCount
      || this.streamingGpuBytes > this.maxStreamingGpuBytes
    ) {
      if (this.streamingMeshes.size <= 1) return;
      const oldest = this.streamingMeshes.entries().next().value as
        | [string, StreamingMeshEntry]
        | undefined;
      if (!oldest) return;
      const [contentKey, entry] = oldest;
      if (contentKey === protectedContentKey && this.streamingMeshes.size === 1) return;
      this.streamingMeshes.delete(contentKey);
      this.streamingGpuBytes -= entry.gpuBytes;
      entry.mesh.removeFromParent();
      entry.mesh.geometry.dispose();
      disposeStreamingMaterial(entry.mesh);
    }
  }

  private refreshStreamingDepthBias(): void {
    let age = 1;
    for (const entry of this.streamingMeshes.values()) {
      const material = entry.mesh.material as THREE.MeshStandardMaterial;
      material.polygonOffsetFactor = -age;
      material.polygonOffsetUnits = -age;
      entry.mesh.renderOrder = DEM_TERRAIN_RENDER_ORDER + age;
      age++;
    }
  }

  private rebuildCoverageFog(
    geometry: THREE.BufferGeometry,
    sampling: TerrainNavigationSampling | null,
  ): void {
    this.clearCoverageFog();
    if (!sampling) return;
    const boundary = buildCoverageFogBoundary(geometry, sampling);
    if (!boundary) return;
    this.coverageFog = new THREE.Mesh(boundary.geometry, this.coverageFogMaterial);
    this.coverageFog.name = "demCoverageFogBoundary";
    this.coverageFog.frustumCulled = false;
    this.coverageFog.renderOrder = DEM_COVERAGE_FOG_RENDER_ORDER;
    this.coverageFogTopOffsets = boundary.topOffsets;
    this.coverageFogBottomHeights = boundary.bottomHeights;
    this.coverageFogTopY = Number.NaN;
    this.root.add(this.coverageFog);
  }

  private clearCoverageFog(): void {
    this.coverageFog?.removeFromParent();
    this.coverageFog?.geometry.dispose();
    this.coverageFog = null;
    this.coverageFogTopOffsets = new Uint32Array(0);
    this.coverageFogBottomHeights = new Float32Array(0);
    this.coverageFogTopY = Number.NaN;
  }
}

interface CoverageFogBoundary {
  readonly geometry: THREE.BufferGeometry;
  readonly topOffsets: Uint32Array<ArrayBufferLike>;
  readonly bottomHeights: Float32Array<ArrayBufferLike>;
}

function buildCoverageFogBoundary(
  geometry: THREE.BufferGeometry,
  sampling: TerrainNavigationSampling,
): CoverageFogBoundary | null {
  const position = geometry.getAttribute("position") as THREE.BufferAttribute | undefined;
  if (!position || position.itemSize !== 3) return null;
  const nearVertexCount = sampling.nearAxisM.length * sampling.nearAxisM.length;
  const polarVertexCount = position.count - nearVertexCount;
  const ringCount = sampling.polarDistanceM.length;
  if (polarVertexCount <= 0 || polarVertexCount % ringCount !== 0) return null;
  const azimuthCount = polarVertexCount / ringCount;
  if (azimuthCount < 3) return null;

  const validVertices = indexedVertexMask(geometry, position.count);
  const boundaryRingByAzimuth = new Int32Array(azimuthCount).fill(-1);
  for (let azimuth = 0; azimuth < azimuthCount; azimuth++) {
    const nextAzimuth = (azimuth + 1) % azimuthCount;
    for (let ring = 0; ring < ringCount - 1; ring++) {
      const inner = nearVertexCount + ring * azimuthCount;
      const outer = inner + azimuthCount;
      if (
        validVertices[inner + azimuth] !== 1
        || validVertices[inner + nextAzimuth] !== 1
        || validVertices[outer + azimuth] !== 1
        || validVertices[outer + nextAzimuth] !== 1
      ) break;
      boundaryRingByAzimuth[azimuth] = ring + 1;
    }
  }

  const source = position.array as Float32Array;
  const vertices: number[] = [];
  const indices: number[] = [];
  const topOffsets: number[] = [];
  const bottomHeights: number[] = [];
  for (let azimuth = 0; azimuth < azimuthCount; azimuth++) {
    const nextAzimuth = (azimuth + 1) % azimuthCount;
    const firstBoundaryRing = boundaryRingByAzimuth[azimuth]!;
    const secondBoundaryRing = boundaryRingByAzimuth[nextAzimuth]!;
    if (firstBoundaryRing < 0 || secondBoundaryRing < 0) continue;
    const firstVertex = nearVertexCount + firstBoundaryRing * azimuthCount + azimuth;
    const secondVertex = nearVertexCount + secondBoundaryRing * azimuthCount + nextAzimuth;
    const firstOffset = firstVertex * 3;
    const secondOffset = secondVertex * 3;
    const vertexOffset = vertices.length / 3;
    const firstHeight = source[firstOffset + 1]!;
    const secondHeight = source[secondOffset + 1]!;
    vertices.push(
      source[firstOffset]!, firstHeight, source[firstOffset + 2]!,
      source[secondOffset]!, secondHeight, source[secondOffset + 2]!,
      source[firstOffset]!, firstHeight + 2.0, source[firstOffset + 2]!,
      source[secondOffset]!, secondHeight + 2.0, source[secondOffset + 2]!,
    );
    topOffsets.push(vertexOffset * 3 + 7, vertexOffset * 3 + 10);
    bottomHeights.push(firstHeight, secondHeight);
    indices.push(
      vertexOffset, vertexOffset + 1, vertexOffset + 2,
      vertexOffset + 2, vertexOffset + 1, vertexOffset + 3,
    );
  }
  if (indices.length === 0) return null;
  const fogGeometry = new THREE.BufferGeometry();
  fogGeometry.setAttribute("position", new THREE.BufferAttribute(new Float32Array(vertices), 3));
  fogGeometry.setIndex(new THREE.BufferAttribute(new Uint32Array(indices), 1));
  fogGeometry.computeBoundingSphere();
  return {
    geometry: fogGeometry,
    topOffsets: new Uint32Array(topOffsets),
    bottomHeights: new Float32Array(bottomHeights),
  };
}

function indexedVertexMask(geometry: THREE.BufferGeometry, vertexCount: number): Uint8Array {
  const mask = new Uint8Array(vertexCount);
  const index = geometry.getIndex();
  if (!index) {
    mask.fill(1);
    return mask;
  }
  for (let offset = 0; offset < index.count; offset++) {
    const vertex = index.getX(offset);
    if (vertex >= 0 && vertex < vertexCount) mask[vertex] = 1;
  }
  return mask;
}

function semanticBytes(mesh: THREE.Mesh<THREE.BufferGeometry> | null): number {
  if (!mesh) return 0;
  return (
    (mesh.geometry.getAttribute("terrainClassId")?.array.byteLength ?? 0)
    + (mesh.geometry.getAttribute("terrainSourceId")?.array.byteLength ?? 0)
    + (mesh.geometry.getAttribute("paletteIndex")?.array.byteLength ?? 0)
  );
}

function disposeStreamingMaterial(mesh: THREE.Mesh): void {
  const materials = Array.isArray(mesh.material) ? mesh.material : [mesh.material];
  for (const material of materials) material.dispose();
}

function positiveInteger(value: number | undefined, fallback: number): number {
  return Number.isSafeInteger(value) && value! > 0 ? value! : fallback;
}

function checkedLayout(layout: any, expectedLength: number): number {
  const offset = Number(layout?.offset);
  const length = Number(layout?.length);
  if (!Number.isSafeInteger(offset) || !Number.isSafeInteger(length) || offset < 0 || length < expectedLength) {
    throw new Error("Terrain buffer layout is invalid");
  }
  return offset;
}

function viewFloat32(buffer: ArrayBuffer, layout: any, count: number): Float32Array {
  const offset = checkedLayout(layout, count * Float32Array.BYTES_PER_ELEMENT);
  return new Float32Array(buffer, offset, count);
}

function viewUint8(buffer: ArrayBuffer, layout: any, count: number): Uint8Array {
  const offset = checkedLayout(layout, count);
  return new Uint8Array(buffer, offset, count);
}

function viewUint16(buffer: ArrayBuffer, layout: any, count: number): Uint16Array {
  const offset = checkedLayout(layout, count * Uint16Array.BYTES_PER_ELEMENT);
  return new Uint16Array(buffer, offset, count);
}

function viewInt16(buffer: ArrayBuffer, layout: any, count: number): Int16Array {
  const offset = checkedLayout(layout, count * Int16Array.BYTES_PER_ELEMENT);
  return new Int16Array(buffer, offset, count);
}

function viewUint32(buffer: ArrayBuffer, layout: any, count: number): Uint32Array {
  const offset = checkedLayout(layout, count * Uint32Array.BYTES_PER_ELEMENT);
  return new Uint32Array(buffer, offset, count);
}

function parseNavigationSampling(value: unknown): TerrainNavigationSampling | null {
  if (!value || typeof value !== "object") return null;
  const raw = value as {
    nearAxisM?: unknown;
    polarDistanceM?: unknown;
    polarAzimuthStepDeg?: unknown;
    centerEastM?: unknown;
    centerNorthM?: unknown;
  };
  if (!Array.isArray(raw.nearAxisM) || !Array.isArray(raw.polarDistanceM)) return null;
  const nearAxisM = Float32Array.from(raw.nearAxisM.map(Number));
  const polarDistanceM = Float32Array.from(raw.polarDistanceM.map(Number));
  const polarAzimuthStepDeg = Number(raw.polarAzimuthStepDeg);
  const centerEastM = Number(raw.centerEastM ?? 0);
  const centerNorthM = Number(raw.centerNorthM ?? 0);
  if (
    nearAxisM.length < 2
    || polarDistanceM.length < 2
    || !Number.isFinite(polarAzimuthStepDeg)
    || polarAzimuthStepDeg <= 0
    || !Number.isFinite(centerEastM)
    || !Number.isFinite(centerNorthM)
    || !strictlyIncreasing(nearAxisM)
    || !strictlyIncreasing(polarDistanceM)
  ) return null;
  return { nearAxisM, polarDistanceM, polarAzimuthStepDeg, centerEastM, centerNorthM };
}

function strictlyIncreasing(values: Float32Array): boolean {
  for (let index = 1; index < values.length; index++) {
    if (!(values[index]! > values[index - 1]!)) return false;
  }
  return true;
}
