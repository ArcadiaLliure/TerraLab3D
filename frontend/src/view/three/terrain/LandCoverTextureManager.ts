import * as THREE from "three";

export interface LandCoverTileData {
  readonly tileKey: string;
  readonly bounds: [number, number, number, number];
  readonly width: number;
  readonly height: number;
  readonly nodataValue: number;
  readonly data: Uint16Array;
}

export interface LandCoverLegendData {
  readonly legendId: string;
  readonly entries: Array<{
    classId: number;
    colorRgba: [number, number, number, number];
  }>;
}

/**
 * Retained GPU representation of categorical land-cover tiles.
 *
 * Each world-aligned tile occupies one layer of an R16UI DataArrayTexture.
 * Streaming a tile therefore updates exactly one GPU layer; it never rebuilds
 * DEM geometry and never re-uploads a giant stitched 2D atlas.
 *
 * Row 0 is geographic North from Rasterio to texelFetch. flipY stays false.
 */
export class LandCoverTextureManager {
  public readonly activeBounds = new THREE.Vector4(0, 0, 0, 0);
  public readonly tileWorldSize = new THREE.Vector2(1, 1);

  public readonly emptyCoverageTexture: THREE.DataArrayTexture;
  public readonly emptyPaletteTexture: THREE.DataTexture;
  public paletteTexture: THREE.DataTexture;
  public activeCoverageTexture: THREE.DataArrayTexture | null = null;

  // Compatibility/diagnostic fields used by the current frontend integration.
  public globalResolution = 0;
  public globalWidth = 0;
  public globalHeight = 0;

  private requestedBounds: [number, number, number, number] | null = null;
  private requestedResolution = 0;
  private classData: Uint16Array | null = null;
  private layerWidth = 0;
  private layerHeight = 0;
  private gridColumns = 0;
  private gridRows = 0;
  private pendingTiles: LandCoverTileData[] = [];
  private changeCallback: (() => void) | null = null;

  constructor() {
    this.emptyCoverageTexture = createClassArrayTexture(new Uint16Array([0]), 1, 1, 1, true);
    this.emptyPaletteTexture = createPaletteTexture(new Uint8Array(256 * 256 * 4));
    this.paletteTexture = this.emptyPaletteTexture;
  }

  public setChangeCallback(callback: (() => void) | null): void {
    this.changeCallback = callback;
  }

  public updateLegend(legend: LandCoverLegendData): void {
    const lutData = new Uint8Array(256 * 256 * 4);
    for (const entry of legend.entries) {
      const classId = Number(entry.classId);
      if (!Number.isSafeInteger(classId) || classId < 0 || classId > 0xffff) continue;
      const offset = classId * 4;
      lutData[offset] = clampByte(entry.colorRgba[0]);
      lutData[offset + 1] = clampByte(entry.colorRgba[1]);
      lutData[offset + 2] = clampByte(entry.colorRgba[2]);
      lutData[offset + 3] = clampByte(entry.colorRgba[3]);
    }

    if (this.paletteTexture !== this.emptyPaletteTexture) this.paletteTexture.dispose();
    this.paletteTexture = createPaletteTexture(lutData);
    this.changeCallback?.();
  }

  /**
   * Start a new coverage generation. Allocation is lazy until the first tile,
   * because the binary tile itself is authoritative for layer dimensions.
   */
  public initGlobalBuffer(bounds: [number, number, number, number], resolution: number): void {
    if (!validBounds(bounds) || !Number.isFinite(resolution) || resolution <= 0) return;
    if (
      this.requestedBounds
      && sameBounds(this.requestedBounds, bounds)
      && approximatelyEqual(this.requestedResolution, resolution)
    ) {
      return;
    }

    const pending = this.pendingTiles;
    this.clearCoverage(false);
    this.pendingTiles = pending;
    this.requestedBounds = [...bounds] as [number, number, number, number];
    this.requestedResolution = resolution;
    this.globalResolution = resolution;
    this.globalWidth = Math.max(1, Math.ceil((bounds[2] - bounds[0]) / resolution));
    this.globalHeight = Math.max(1, Math.ceil((bounds[3] - bounds[1]) / resolution));

    if (this.pendingTiles.length > 0) {
      const queued = this.pendingTiles;
      this.pendingTiles = [];
      for (const tile of queued) this.addTile(tile);
    }
    this.changeCallback?.();
  }

  public addTile(tile: LandCoverTileData): boolean {
    if (!validTile(tile)) {
      console.warn("[LandCoverTextureManager] invalid categorical tile", tile.tileKey);
      return false;
    }

    const resolutionX = (tile.bounds[2] - tile.bounds[0]) / tile.width;
    const resolutionY = (tile.bounds[3] - tile.bounds[1]) / tile.height;
    if (!approximatelyEqual(resolutionX, resolutionY)) {
      console.warn("[LandCoverTextureManager] non-square categorical pixels", tile.tileKey);
      return false;
    }

    if (!this.requestedBounds) {
      // Normally surface_progress arrives first. Keep an early binary resource
      // rather than inventing a tile-sized global frame.
      this.pendingTiles.push(tile);
      return true;
    }
    if (!approximatelyEqual(resolutionX, this.requestedResolution)) {
      console.warn(
        "[LandCoverTextureManager] tile/request resolution mismatch",
        tile.tileKey,
        resolutionX,
        this.requestedResolution,
      );
      return false;
    }

    if (!this.activeCoverageTexture) this.allocateTileArray(tile, resolutionX, resolutionY);
    if (!this.activeCoverageTexture || !this.classData) return false;
    if (tile.width !== this.layerWidth || tile.height !== this.layerHeight) {
      console.warn("[LandCoverTextureManager] inconsistent tile dimensions", tile.tileKey);
      return false;
    }

    const column = Math.round((tile.bounds[0] - this.activeBounds.x) / this.tileWorldSize.x);
    const row = Math.round((this.activeBounds.w - tile.bounds[3]) / this.tileWorldSize.y);
    if (column < 0 || column >= this.gridColumns || row < 0 || row >= this.gridRows) return false;

    const layer = row * this.gridColumns + column;
    const layerSize = this.layerWidth * this.layerHeight;
    this.classData.set(tile.data, layer * layerSize);

    // Three.js r179 maps layerUpdates to a single texSubImage3D for the
    // specified layer. Missing/unloaded layers remain zero => BASE fallback.
    this.activeCoverageTexture.addLayerUpdate(layer);
    this.activeCoverageTexture.needsUpdate = true;
    this.changeCallback?.();
    return true;
  }

  public clear(): void {
    this.clearCoverage(true);
    this.requestedBounds = null;
    this.requestedResolution = 0;
    this.globalResolution = 0;
    this.globalWidth = 0;
    this.globalHeight = 0;
    this.changeCallback?.();
  }

  public dispose(): void {
    this.clear();
    if (this.paletteTexture !== this.emptyPaletteTexture) this.paletteTexture.dispose();
    this.paletteTexture = this.emptyPaletteTexture;
    this.emptyCoverageTexture.dispose();
    this.emptyPaletteTexture.dispose();
  }

  private allocateTileArray(tile: LandCoverTileData, resolutionX: number, resolutionY: number): void {
    if (!this.requestedBounds) return;
    const tileWorldX = resolutionX * tile.width;
    const tileWorldY = resolutionY * tile.height;
    if (!(tileWorldX > 0) || !(tileWorldY > 0)) return;

    const gridMinX = Math.floor(this.requestedBounds[0] / tileWorldX) * tileWorldX;
    const gridMaxX = Math.ceil(this.requestedBounds[2] / tileWorldX) * tileWorldX;
    const gridMinY = Math.floor(this.requestedBounds[1] / tileWorldY) * tileWorldY;
    const gridMaxY = Math.ceil(this.requestedBounds[3] / tileWorldY) * tileWorldY;
    const columns = Math.max(1, Math.round((gridMaxX - gridMinX) / tileWorldX));
    const rows = Math.max(1, Math.round((gridMaxY - gridMinY) / tileWorldY));
    const depth = columns * rows;

    this.layerWidth = tile.width;
    this.layerHeight = tile.height;
    this.gridColumns = columns;
    this.gridRows = rows;
    this.tileWorldSize.set(tileWorldX, tileWorldY);
    this.activeBounds.set(gridMinX, gridMinY, gridMaxX, gridMaxY);

    const layerSize = tile.width * tile.height;
    this.classData = new Uint16Array(layerSize * depth);
    this.activeCoverageTexture = createClassArrayTexture(
      this.classData,
      tile.width,
      tile.height,
      depth,
      true,
    );
  }

  private clearCoverage(clearPending: boolean): void {
    this.activeCoverageTexture?.dispose();
    this.activeCoverageTexture = null;
    this.classData = null;
    this.layerWidth = 0;
    this.layerHeight = 0;
    this.gridColumns = 0;
    this.gridRows = 0;
    this.activeBounds.set(0, 0, 0, 0);
    this.tileWorldSize.set(1, 1);
    if (clearPending) this.pendingTiles = [];
  }
}

function createClassArrayTexture(
  data: Uint16Array,
  width: number,
  height: number,
  depth: number,
  uploadImmediately: boolean,
): THREE.DataArrayTexture {
  const texture = new THREE.DataArrayTexture(data as any, width, height, depth);
  texture.format = THREE.RedIntegerFormat;
  texture.type = THREE.UnsignedShortType;
  texture.internalFormat = "R16UI";
  texture.minFilter = THREE.NearestFilter;
  texture.magFilter = THREE.NearestFilter;
  texture.wrapS = THREE.ClampToEdgeWrapping;
  texture.wrapT = THREE.ClampToEdgeWrapping;
  texture.wrapR = THREE.ClampToEdgeWrapping as any;
  texture.generateMipmaps = false;
  texture.flipY = false;
  texture.unpackAlignment = 1;
  texture.colorSpace = THREE.NoColorSpace;
  if (uploadImmediately) texture.needsUpdate = true;
  return texture;
}

function createPaletteTexture(data: Uint8Array): THREE.DataTexture {
  const texture = new THREE.DataTexture(
    data,
    256,
    256,
    THREE.RGBAFormat,
    THREE.UnsignedByteType,
  );
  texture.minFilter = THREE.NearestFilter;
  texture.magFilter = THREE.NearestFilter;
  texture.wrapS = THREE.ClampToEdgeWrapping;
  texture.wrapT = THREE.ClampToEdgeWrapping;
  texture.generateMipmaps = false;
  texture.flipY = false;
  texture.unpackAlignment = 1;
  texture.colorSpace = THREE.NoColorSpace;
  texture.needsUpdate = true;
  return texture;
}

function validTile(tile: LandCoverTileData): boolean {
  return Number.isSafeInteger(tile.width)
    && Number.isSafeInteger(tile.height)
    && tile.width > 0
    && tile.height > 0
    && tile.data.length === tile.width * tile.height
    && validBounds(tile.bounds);
}

function validBounds(bounds: readonly number[]): bounds is [number, number, number, number] {
  return bounds.length === 4
    && bounds.every(Number.isFinite)
    && bounds[2]! > bounds[0]!
    && bounds[3]! > bounds[1]!;
}

function sameBounds(a: readonly number[], b: readonly number[]): boolean {
  return a.length === 4
    && b.length === 4
    && a.every((value, index) => approximatelyEqual(value, b[index]!));
}

function approximatelyEqual(a: number, b: number): boolean {
  const tolerance = Math.max(1e-6, Math.max(Math.abs(a), Math.abs(b)) * 1e-7);
  return Math.abs(a - b) <= tolerance;
}

function clampByte(value: number): number {
  return Math.max(0, Math.min(255, Math.round(Number(value) || 0)));
}
