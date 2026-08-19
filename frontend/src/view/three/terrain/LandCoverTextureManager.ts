import * as THREE from "three";

export interface LandCoverTileData {
  readonly tileKey?: string;
  readonly resourceId?: string;
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
    label: string;
    colorRgba: [number, number, number, number];
  }>;
}

export interface CoverageBank {
  readonly bankIndex: number;
  readonly depth: number;
  readonly classData: Uint16Array;
  readonly texture: THREE.DataArrayTexture;
}

/**
 * Retained GPU representation of categorical land-cover tiles using banked 2D texture arrays.
 *
 * WebGL2 implementations guarantee at least 256 layers per 2D array texture.
 * To support large radii (e.g. 150 km = 30x30 = 900 tiles) without exceeding
 * GPU driver limits or requiring gigabyte-sized single texture allocations,
 * tiles are partitioned across a small set of DataArrayTexture banks (e.g. 4 banks of <=256 layers).
 *
 * Streaming a tile updates exactly one layer of the target bank via addLayerUpdate();
 * it never rebuilds DEM geometry and never re-uploads a giant stitched 2D atlas.
 */
export class LandCoverTextureManager {
  public static readonly MAX_LAYERS_PER_BANK = 256;
  public static readonly MAX_BANKS = 4;

  public readonly activeBounds = new THREE.Vector4(0, 0, 0, 0);
  public readonly tileWorldSize = new THREE.Vector2(1, 1);

  public readonly emptyCoverageTexture: THREE.DataArrayTexture;
  public readonly emptyPaletteTexture: THREE.DataTexture;
  public paletteTexture: THREE.DataTexture;

  public banks: CoverageBank[] = [];

  // Compatibility/diagnostic fields
  public globalResolution = 0;
  public globalWidth = 0;
  public globalHeight = 0;
  public gridColumns = 0;
  public gridRows = 0;
  public totalDepth = 0;
  public layerWidth = 0;
  public layerHeight = 0;

  private requestedBounds: [number, number, number, number] | null = null;
  private requestedResolution = 0;
  private pendingTiles: LandCoverTileData[] = [];
  private changeCallback: (() => void) | null = null;
  public latestLegend: LandCoverLegendData | null = null;

  public get activeCoverageTexture(): THREE.DataArrayTexture | null {
    return this.banks[0]?.texture ?? null;
  }

  constructor() {
    this.emptyCoverageTexture = createClassArrayTexture(new Uint16Array([0]), 1, 1, 1, true);
    this.emptyPaletteTexture = createPaletteTexture(new Uint8Array(256 * 256 * 4));
    this.paletteTexture = this.emptyPaletteTexture;
  }

  public setChangeCallback(callback: (() => void) | null): void {
    this.changeCallback = callback;
  }

  public updateLegend(legend: LandCoverLegendData): void {
    console.info("MGP: LandCoverTextureManager.updateLegend [INICI]");
    this.latestLegend = legend;
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
    console.info("MGP: LandCoverTextureManager.updateLegend [FI]");
  }

  /**
   * Start a new coverage generation. Allocation is lazy until the first tile,
   * because the binary tile itself is authoritative for layer dimensions.
   */
  public initGlobalBuffer(bounds: [number, number, number, number], resolution: number): void {
    console.info("MGP: LandCoverTextureManager.initGlobalBuffer [INICI]");
    if (!validBounds(bounds) || !Number.isFinite(resolution) || resolution <= 0) {
      console.info("MGP: LandCoverTextureManager.initGlobalBuffer [FI]");
      return;
    }
    if (
      this.requestedBounds
      && sameBounds(this.requestedBounds, bounds)
      && approximatelyEqual(this.requestedResolution, resolution)
    ) {
      console.info("MGP: LandCoverTextureManager.initGlobalBuffer [FI]");
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
    console.debug(`[LandCoverTextureManager] initGlobalBuffer: bounds=${bounds.join(",")}, res=${resolution}, dimensions=${this.globalWidth}x${this.globalHeight}`);

    if (this.pendingTiles.length > 0) {
      const queued = this.pendingTiles;
      this.pendingTiles = [];
      console.debug(`[LandCoverTextureManager] descarregant ${queued.length} rajoles pendents acumulades abans de initGlobalBuffer`);
      for (const tile of queued) this.addTile(tile);
    }
    this.changeCallback?.();
    console.info("MGP: LandCoverTextureManager.initGlobalBuffer [FI]");
  }

  public addTile(tile: LandCoverTileData): boolean {
    console.info("MGP: LandCoverTextureManager.addTile [INICI]");
    const tileKey = tile.tileKey || tile.resourceId || "unknown";
    console.debug(`[LandCoverTextureManager] addTile rebut: tileKey=${tileKey}, bounds=${tile.bounds.join(",")}, size=${tile.width}x${tile.height}, dataLen=${tile.data?.length}`);
    if (!validTile(tile)) {
      console.error("[LandCoverTextureManager] invalid categorical tile", tileKey);
      console.info("MGP: LandCoverTextureManager.addTile [FI]");
      return false;
    }

    const resolutionX = (tile.bounds[2] - tile.bounds[0]) / tile.width;
    const resolutionY = (tile.bounds[3] - tile.bounds[1]) / tile.height;
    if (!approximatelyEqual(resolutionX, resolutionY)) {
      console.warn("[LandCoverTextureManager] non-square categorical pixels", tileKey);
      console.info("MGP: LandCoverTextureManager.addTile [FI]");
      return false;
    }

    if (!this.requestedBounds) {
      console.debug(`[LandCoverTextureManager] no hi ha requestedBounds encara. Afegint rajola ${tileKey} a pendingTiles (${this.pendingTiles.length + 1} en cua)`);
      this.pendingTiles.push(tile);
      console.info("MGP: LandCoverTextureManager.addTile [FI]");
      return true;
    }
    if (!approximatelyEqual(resolutionX, this.requestedResolution)) {
      console.warn(
        "[LandCoverTextureManager] tile/request resolution mismatch",
        tileKey,
        resolutionX,
        this.requestedResolution,
      );
      console.info("MGP: LandCoverTextureManager.addTile [FI]");
      return false;
    }

    if (this.banks.length === 0) {
      this.allocateTileArray(tile, resolutionX, resolutionY);
    }
    if (this.banks.length === 0) {
      console.warn("[LandCoverTextureManager] No s'ha pogut crear/trobar bancs de textura per la rajola", tileKey);
      console.info("MGP: LandCoverTextureManager.addTile [FI]");
      return false;
    }
    if (tile.width !== this.layerWidth || tile.height !== this.layerHeight) {
      console.warn("[LandCoverTextureManager] inconsistent tile dimensions", tileKey);
      console.info("MGP: LandCoverTextureManager.addTile [FI]");
      return false;
    }

    const column = Math.round((tile.bounds[0] - this.activeBounds.x) / this.tileWorldSize.x);
    const row = Math.round((this.activeBounds.w - tile.bounds[3]) / this.tileWorldSize.y);
    if (column < 0 || column >= this.gridColumns || row < 0 || row >= this.gridRows) {
      console.warn(`[LandCoverTextureManager] rajola fora de la graella: col=${column}/${this.gridColumns}, row=${row}/${this.gridRows}`);
      console.info("MGP: LandCoverTextureManager.addTile [FI]");
      return false;
    }

    const globalLayer = row * this.gridColumns + column;
    const layersPerBank = LandCoverTextureManager.MAX_LAYERS_PER_BANK;
    const bankIndex = Math.floor(globalLayer / layersPerBank);
    const localLayer = globalLayer % layersPerBank;

    if (bankIndex >= this.banks.length) {
      console.warn(`[LandCoverTextureManager] bankIndex ${bankIndex} fora dels bancs creats (${this.banks.length})`);
      console.info("MGP: LandCoverTextureManager.addTile [FI]");
      return false;
    }

    const bank = this.banks[bankIndex];
    const layerSize = this.layerWidth * this.layerHeight;
    bank.classData.set(tile.data, localLayer * layerSize);

    bank.texture.source.dataReady = true;
    bank.texture.addLayerUpdate(localLayer);
    bank.texture.needsUpdate = true;

    console.info(`[LandCoverTextureManager] layer ${globalLayer} (bank ${bankIndex}, localLayer ${localLayer}) update requested (col=${column}, row=${row}, tileKey=${tileKey})`);
    this.changeCallback?.();
    console.info("MGP: LandCoverTextureManager.addTile [FI]");
    return true;
  }

  public getCategoryAtUv(u: number, v: number): { classId: number; label: string } | null {
    if (this.banks.length === 0 || !this.requestedBounds || !this.latestLegend) return null;

    const worldX = this.requestedBounds[0] + u * (this.requestedBounds[2] - this.requestedBounds[0]);
    const worldY = this.requestedBounds[1] + v * (this.requestedBounds[3] - this.requestedBounds[1]);

    if (
      worldX < this.activeBounds.x || worldX >= this.activeBounds.z
      || worldY < this.activeBounds.y || worldY >= this.activeBounds.w
    ) {
      return null;
    }

    const col = Math.floor((worldX - this.activeBounds.x) / this.tileWorldSize.x);
    const row = Math.floor((this.activeBounds.w - worldY) / this.tileWorldSize.y);

    if (col < 0 || col >= this.gridColumns || row < 0 || row >= this.gridRows) return null;

    const globalLayer = row * this.gridColumns + col;
    const layersPerBank = LandCoverTextureManager.MAX_LAYERS_PER_BANK;
    const bankIndex = Math.floor(globalLayer / layersPerBank);
    const localLayer = globalLayer % layersPerBank;

    if (bankIndex >= this.banks.length) return null;
    const bank = this.banks[bankIndex];

    const tileStartX = this.activeBounds.x + col * this.tileWorldSize.x;
    const tileStartY = this.activeBounds.w - (row + 1) * this.tileWorldSize.y;

    const localU = Math.max(0, Math.min(0.999999, (worldX - tileStartX) / this.tileWorldSize.x));
    const localV = Math.max(0, Math.min(0.999999, (tileMaxY_from(this.activeBounds.w, row, this.tileWorldSize.y) - worldY) / this.tileWorldSize.y));

    const pixelX = Math.floor(localU * this.layerWidth);
    const pixelY = Math.floor(localV * this.layerHeight);

    if (pixelX < 0 || pixelX >= this.layerWidth || pixelY < 0 || pixelY >= this.layerHeight) return null;

    const index = localLayer * (this.layerWidth * this.layerHeight) + pixelY * this.layerWidth + pixelX;
    const classId = bank.classData[index];

    if (classId === undefined || classId === 0) return null;

    const entry = this.latestLegend.entries.find((e) => e.classId === classId);
    if (!entry) return null;

    return { classId, label: entry.label };
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
    this.totalDepth = depth;
    this.tileWorldSize.set(tileWorldX, tileWorldY);
    this.activeBounds.set(gridMinX, gridMinY, gridMaxX, gridMaxY);

    const layersPerBank = LandCoverTextureManager.MAX_LAYERS_PER_BANK;
    const bankCount = Math.min(LandCoverTextureManager.MAX_BANKS, Math.ceil(depth / layersPerBank));
    const layerSize = tile.width * tile.height;

    this.banks = [];
    let remainingLayers = depth;
    for (let b = 0; b < bankCount; b++) {
      const bankDepth = Math.min(layersPerBank, remainingLayers);
      remainingLayers -= bankDepth;
      const classData = new Uint16Array(layerSize * bankDepth);
      const texture = createClassArrayTexture(classData, tile.width, tile.height, bankDepth, false);
      texture.onUpdate = (tex) => {
        console.info(`[LandCoverTextureManager] GPU upload completed for bank ${b}: version=${tex.version}`);
      };
      this.banks.push({
        bankIndex: b,
        depth: bankDepth,
        classData,
        texture,
      });
    }

    console.info(
      `[LandCoverTextureManager] Allocated ${this.banks.length} texture bank(s) for totalDepth=${depth} (${columns}x${rows} tiles). Total CPU Memory: ${((layerSize * depth * 2) / (1024 * 1024)).toFixed(1)}MB`,
    );
  }

  private clearCoverage(clearPending: boolean): void {
    for (const bank of this.banks) {
      bank.texture.dispose();
    }
    this.banks = [];
    this.layerWidth = 0;
    this.layerHeight = 0;
    this.gridColumns = 0;
    this.gridRows = 0;
    this.totalDepth = 0;
    this.activeBounds.set(0, 0, 0, 0);
    this.tileWorldSize.set(1, 1);
    if (clearPending) this.pendingTiles = [];
  }
}

function tileMaxY_from(activeBoundsW: number, row: number, tileWorldHeight: number): number {
  return activeBoundsW - row * tileWorldHeight;
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

  texture.needsUpdate = true;
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
