import * as THREE from "three";
import type { TerrainNavigationSampling } from "../terrain/TechnicalTerrainSampler";
import { LandCoverTextureManager } from "../terrain/LandCoverTextureManager";

export const DEM_TERRAIN_RENDER_ORDER = -900;
export const DEM_COVERAGE_FOG_RENDER_ORDER = -899;

export interface DemTerrainLayerMetrics {
  readonly geometryBuildCount: number;
  readonly geometryUploadBytes: number;
  readonly vertexCount: number;
  readonly triangleCount: number;
  readonly activeMeshCount: number;
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
}

const DEFAULT_STREAMING_MESH_COUNT = 12;
const DEFAULT_STREAMING_GPU_BYTES = 256 * 1024 * 1024;

/**
 * Persistent Three.js presentation of the observer-relative DEM mesh.
 *
 * BufferGeometry is geometry only: position, normal and index. Surface
 * appearance is resolved in the fragment shader from independent categorical
 * texture layers, so changing land cover never rebuilds terrain geometry.
 */
export class DemTerrainLayerRenderer {
  readonly root = new THREE.Group();
  public readonly landCoverManager = new LandCoverTextureManager();

  private readonly surfaceUniforms = {
    landCoverTex: { value: this.landCoverManager.emptyCoverageTexture as THREE.Texture },
    landCoverLUT: { value: this.landCoverManager.emptyPaletteTexture as THREE.Texture },
    landCoverBounds: { value: new THREE.Vector4(0, 0, 0, 0) },
    landCoverTileWorldSize: { value: new THREE.Vector2(1, 1) },
    hasLandCover: { value: 0 },
    terrainRadiusM: { value: 150_000.0 },
  };

  private readonly material: THREE.MeshStandardMaterial;
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
  private readonly maxStreamingMeshCount: number;
  private readonly maxStreamingGpuBytes: number;
  private streamingGpuBytes = 0;
  private disposed = false;
  private geometryBuildCount = 0;
  private geometryUploadBytes = 0;
  private vertexCount = 0;
  private triangleCount = 0;

  constructor(parent: THREE.Object3D, cache: DemTerrainStreamingCacheOptions = {}) {
    this.material = this.createTerrainMaterial(false);
    this.landCoverManager.setChangeCallback(() => this.updateShaderUniforms());
    this.maxStreamingMeshCount = positiveInteger(cache.maxMeshCount, DEFAULT_STREAMING_MESH_COUNT);
    this.maxStreamingGpuBytes = positiveInteger(cache.maxGpuBytes, DEFAULT_STREAMING_GPU_BYTES);
    this.root.name = "demTerrainRoot";
    parent.add(this.root);
  }

  /** Update shared uniforms only; no BufferGeometry or material rebuild. */
  public updateShaderUniforms(): void {
    const coverage = this.landCoverManager.activeCoverageTexture;
    if (coverage !== null) {
      this.surfaceUniforms.landCoverTex.value = coverage;
      this.surfaceUniforms.landCoverLUT.value = this.landCoverManager.paletteTexture;
      this.surfaceUniforms.landCoverBounds.value.copy(this.landCoverManager.activeBounds);
      this.surfaceUniforms.landCoverTileWorldSize.value.copy(this.landCoverManager.tileWorldSize);
      this.surfaceUniforms.hasLandCover.value = 1;
    } else {
      this.surfaceUniforms.landCoverTex.value = this.landCoverManager.emptyCoverageTexture;
      this.surfaceUniforms.landCoverLUT.value = this.landCoverManager.emptyPaletteTexture;
      this.surfaceUniforms.landCoverBounds.value.set(0, 0, 0, 0);
      this.surfaceUniforms.landCoverTileWorldSize.value.set(1, 1);
      this.surfaceUniforms.hasLandCover.value = 0;
    }
  }

  applyBinaryResource(metadata: any, payload: ArrayBuffer): boolean {
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
    ) return false;
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
      const index = viewUint32(payload, layout.index, indexCount);
      const geometry = new THREE.BufferGeometry();
      geometry.setAttribute("position", new THREE.BufferAttribute(position, 3));
      geometry.setAttribute("normal", new THREE.BufferAttribute(normal, 3));
      geometry.setIndex(new THREE.BufferAttribute(index, 1));
      geometry.computeBoundingSphere();

      const replacement = new THREE.Mesh(
        geometry,
        isStreamingChunk ? this.createTerrainMaterial(true) : this.material,
      );
      replacement.name = isStreamingChunk ? "demTerrainStreamChunk" : "demTerrainMeshV3";
      replacement.frustumCulled = false;
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
        this.surfaceUniforms.terrainRadiusM.value = terrainRadiusFrom(
          navigationSampling,
          geometry.boundingSphere?.radius,
        );
        // A resident-world replacement changes the terrain anchor. Old moving
        // overlays are no longer safe to retain or sample.
        this.clearStreaming();
        this.rebuildCoverageFog(geometry, navigationSampling);
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
      this.geometryUploadBytes += payload.byteLength;
      this.geometryBuildCount++;
      return true;
    } catch (error) {
      console.warn("[DemTerrainLayerRenderer] invalid terrain mesh resource", error);
      return false;
    }
  }

  metrics(): DemTerrainLayerMetrics {
    let streamingVertices = 0;
    let streamingTriangles = 0;
    for (const entry of this.streamingMeshes.values()) {
      streamingVertices += entry.mesh.geometry.getAttribute("position")?.count ?? 0;
      streamingTriangles += Math.floor((entry.mesh.geometry.getIndex()?.count ?? 0) / 3);
    }
    return {
      geometryBuildCount: this.geometryBuildCount,
      geometryUploadBytes: this.geometryUploadBytes,
      vertexCount: this.vertexCount + streamingVertices,
      triangleCount: this.triangleCount + streamingTriangles,
      activeMeshCount: Number(this.mesh !== null) + this.streamingMeshes.size,
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
    this.material.dispose();
    this.coverageFogMaterial.dispose();
    this.landCoverManager.setChangeCallback(null);
    this.landCoverManager.dispose();
    this.root.removeFromParent();
  }

  private createTerrainMaterial(streaming: boolean): THREE.MeshStandardMaterial {
    const material = new THREE.MeshStandardMaterial({
      vertexColors: false,
      roughness: 1,
      metalness: 0,
      emissive: new THREE.Color(0x07111a),
      emissiveIntensity: 0.055,
      side: THREE.FrontSide,
      polygonOffset: streaming,
      polygonOffsetFactor: streaming ? -1 : 0,
      polygonOffsetUnits: streaming ? -1 : 0,
    });
    material.onBeforeCompile = (shader) => this.patchTerrainShader(shader);
    material.customProgramCacheKey = () => "terralab3d-terrain-land-cover-v3";
    return material;
  }

  private patchTerrainShader(shader: THREE.Shader): void {
    shader.uniforms.landCoverTex = this.surfaceUniforms.landCoverTex;
    shader.uniforms.landCoverLUT = this.surfaceUniforms.landCoverLUT;
    shader.uniforms.landCoverBounds = this.surfaceUniforms.landCoverBounds;
    shader.uniforms.landCoverTileWorldSize = this.surfaceUniforms.landCoverTileWorldSize;
    shader.uniforms.hasLandCover = this.surfaceUniforms.hasLandCover;
    shader.uniforms.terrainRadiusM = this.surfaceUniforms.terrainRadiusM;

    shader.vertexShader = shader.vertexShader.replace(
      "#include <common>",
      `
      #include <common>
      varying vec3 vTerraLabWorldPosition;
      `,
    );
    shader.vertexShader = shader.vertexShader.replace(
      "#include <worldpos_vertex>",
      `
      #include <worldpos_vertex>
      vTerraLabWorldPosition = (modelMatrix * vec4(transformed, 1.0)).xyz;
      `,
    );

    shader.fragmentShader = shader.fragmentShader.replace(
      "#include <common>",
      `
      #include <common>
      varying vec3 vTerraLabWorldPosition;
      uniform highp usampler2DArray landCoverTex;
      uniform sampler2D landCoverLUT;
      uniform vec4 landCoverBounds;
      uniform vec2 landCoverTileWorldSize;
      uniform int hasLandCover;
      uniform float terrainRadiusM;

      vec3 terraLabSrgbToLinear(vec3 value) {
        bvec3 cutoff = lessThanEqual(value, vec3(0.04045));
        vec3 lower = value / 12.92;
        vec3 higher = pow((value + 0.055) / 1.055, vec3(2.4));
        return mix(higher, lower, cutoff);
      }

      vec3 terraLabBaseTerrainColor(float distanceM) {
        float normalized = sqrt(clamp(1.0 - distanceM / max(1.0, terrainRadiusM), 0.0, 1.0));
        float scaled = normalized * 4.0;
        int segment = min(int(floor(scaled)), 3);
        float fraction = scaled - float(segment);
        vec3 a;
        vec3 b;
        if (segment == 0) {
          a = vec3(178.0, 194.0, 210.0) / 255.0;
          b = vec3(152.0, 172.0, 186.0) / 255.0;
        } else if (segment == 1) {
          a = vec3(152.0, 172.0, 186.0) / 255.0;
          b = vec3(116.0, 138.0, 132.0) / 255.0;
        } else if (segment == 2) {
          a = vec3(116.0, 138.0, 132.0) / 255.0;
          b = vec3(82.0, 108.0, 86.0) / 255.0;
        } else {
          a = vec3(82.0, 108.0, 86.0) / 255.0;
          b = vec3(62.0, 86.0, 64.0) / 255.0;
        }
        return terraLabSrgbToLinear(mix(a, b, fraction));
      }
      `,
    );

    shader.fragmentShader = shader.fragmentShader.replace(
      "#include <color_fragment>",
      `
      #include <color_fragment>

      // Pas 16 base palette, evaluated per fragment instead of stored per vertex.
      diffuseColor.rgb = terraLabBaseTerrainColor(length(vTerraLabWorldPosition.xz));

      if (hasLandCover == 1) {
        float minX = landCoverBounds.x;
        float minY = landCoverBounds.y;
        float maxX = landCoverBounds.z;
        float maxY = landCoverBounds.w;
        float geoX = vTerraLabWorldPosition.x;
        float geoY = -vTerraLabWorldPosition.z;

        if (maxX > minX && maxY > minY
            && landCoverTileWorldSize.x > 0.0 && landCoverTileWorldSize.y > 0.0
            && geoX >= minX && geoX <= maxX
            && geoY >= minY && geoY <= maxY) {
          ivec3 coverageSize = textureSize(landCoverTex, 0);
          int gridColumns = max(1, int(round((maxX - minX) / landCoverTileWorldSize.x)));
          int gridRows = max(1, int(round((maxY - minY) / landCoverTileWorldSize.y)));
          int column = clamp(
            int(floor((geoX - minX) / landCoverTileWorldSize.x)),
            0,
            gridColumns - 1
          );
          int row = clamp(
            int(floor((maxY - geoY) / landCoverTileWorldSize.y)),
            0,
            gridRows - 1
          );
          int layer = row * gridColumns + column;

          if (layer >= 0 && layer < coverageSize.z) {
            float tileMinX = minX + float(column) * landCoverTileWorldSize.x;
            float tileMaxY = maxY - float(row) * landCoverTileWorldSize.y;
            float localU = clamp(
              (geoX - tileMinX) / landCoverTileWorldSize.x,
              0.0,
              0.99999994
            );
            float localV = clamp(
              (tileMaxY - geoY) / landCoverTileWorldSize.y,
              0.0,
              0.99999994
            );
            ivec2 coveragePixel = ivec2(
              min(int(floor(localU * float(coverageSize.x))), coverageSize.x - 1),
              min(int(floor(localV * float(coverageSize.y))), coverageSize.y - 1)
            );
            uint classId = texelFetch(landCoverTex, ivec3(coveragePixel, layer), 0).r;
            if (classId != 0u) {
              ivec2 lutPixel = ivec2(
                int(classId & 255u),
                int((classId >> 8u) & 255u)
              );
              vec4 lutColor = texelFetch(landCoverLUT, lutPixel, 0);
              if (lutColor.a > 0.0) {
                diffuseColor.rgb = terraLabSrgbToLinear(lutColor.rgb);
              }
            }
          }
        }
      }
      `,
    );
  }

  private clear(): void {
    this.clearCoverageFog();
    this.mesh?.removeFromParent();
    this.mesh?.geometry.dispose();
    this.mesh = null;
    this.navigationSampling = null;
    this.activeVersion = -1;
    this.activeContentKey = "";
    this.vertexCount = 0;
    this.triangleCount = 0;
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
  if (polarVertexCount <= 0 || ringCount <= 0 || polarVertexCount % ringCount !== 0) return null;
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
  if (
    !Number.isSafeInteger(offset)
    || !Number.isSafeInteger(length)
    || offset < 0
    || length < expectedLength
  ) {
    throw new Error("Terrain buffer layout is invalid");
  }
  return offset;
}

function viewFloat32(buffer: ArrayBuffer, layout: any, count: number): Float32Array {
  const offset = checkedLayout(layout, count * Float32Array.BYTES_PER_ELEMENT);
  return new Float32Array(buffer, offset, count);
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

function terrainRadiusFrom(
  sampling: TerrainNavigationSampling | null,
  boundingRadius: number | undefined,
): number {
  const distances = sampling?.polarDistanceM;
  if (distances && distances.length > 0) {
    const value = Number(distances[distances.length - 1]);
    if (Number.isFinite(value) && value > 0) return value;
  }
  if (boundingRadius !== undefined && Number.isFinite(boundingRadius) && boundingRadius > 0) {
    return boundingRadius;
  }
  return 150_000.0;
}
