import * as THREE from "three";
import {
  sampleValidityName,
  type LandCoverLegendData,
  type LandCoverLegendEntryData,
  type LandCoverObservation,
  type LandCoverTileData,
} from "../../../contracts/land_cover_contracts";

export type {
  LandCoverLegendData,
  LandCoverObservation,
  LandCoverTileData,
} from "../../../contracts/land_cover_contracts";

export interface CoverageBank {
  readonly bankIndex: number;
  readonly depth: number;
  readonly classData: Uint16Array;
  readonly texture: THREE.DataArrayTexture;
  readonly validityData: Uint8Array;
  readonly validityTexture: THREE.DataArrayTexture;
}

interface ActiveSchemeDescriptor {
  readonly sourceName: string;
  readonly schemeKey: string;
  readonly schemeVersion: string;
  readonly mappingRevision: string;
  readonly taxonomyKey: "TLST";
  readonly taxonomyVersion: string;
}

/**
 * Retained GPU representation of categorical source codes and SampleValidity.
 *
 * Both resources are banked 2D array textures. A streamed tile updates one
 * persistent layer in each bank; no DEM geometry or per-pixel semantic objects
 * are rebuilt. Validity remains packed as four 2-bit samples per R8UI texel.
 */
export class LandCoverTextureManager {
  public static readonly MAX_LAYERS_PER_BANK = 256;
  public static readonly MAX_BANKS = 4;

  public readonly activeBounds = new THREE.Vector4(0, 0, 0, 0);
  public readonly tileWorldSize = new THREE.Vector2(1, 1);

  public readonly emptyCoverageTexture: THREE.DataArrayTexture;
  public readonly emptyValidityTexture: THREE.DataArrayTexture;
  public readonly emptyPaletteTexture: THREE.DataTexture;
  public paletteTexture: THREE.DataTexture;

  public banks: CoverageBank[] = [];

  public globalResolution = 0;
  public globalWidth = 0;
  public globalHeight = 0;
  public gridColumns = 0;
  public gridRows = 0;
  public totalDepth = 0;
  public layerWidth = 0;
  public layerHeight = 0;
  public validityLayerWidth = 0;

  private requestedBounds: [number, number, number, number] | null = null;
  private requestedResolution = 0;
  private pendingTiles: LandCoverTileData[] = [];
  private changeCallback: (() => void) | null = null;
  private activeScheme: ActiveSchemeDescriptor | null = null;
  private activeLegend: LandCoverLegendData | null = null;
  private activeLegendIdentity = "";
  private readonly legendEntriesByCode = new Map<number, LandCoverLegendEntryData>();
  public latestLegend: LandCoverLegendData | null = null;

  public get activeCoverageTexture(): THREE.DataArrayTexture | null {
    return this.banks[0]?.texture ?? null;
  }

  public get activeValidityTexture(): THREE.DataArrayTexture | null {
    return this.banks[0]?.validityTexture ?? null;
  }

  constructor() {
    this.emptyCoverageTexture = createClassArrayTexture(new Uint16Array([0]), 1, 1, 1);
    this.emptyValidityTexture = createValidityArrayTexture(new Uint8Array([0]), 1, 1, 1);
    this.emptyPaletteTexture = createPaletteTexture(new Uint8Array(256 * 256 * 4));
    this.paletteTexture = this.emptyPaletteTexture;
  }

  public setChangeCallback(callback: (() => void) | null): void {
    this.changeCallback = callback;
  }

  public updateLegend(legend: LandCoverLegendData): void {
    console.info("MGP: LandCoverTextureManager.updateLegend [INICI]");
    this.latestLegend = legend;
    if (!this.activeScheme || legendMatchesScheme(legend, this.activeScheme)) {
      this.activateLegend(legend);
    }
    console.info("MGP: LandCoverTextureManager.updateLegend [FI]");
  }

  private activateLegend(legend: LandCoverLegendData): void {
    const identity = `${legend.schemeKey}@${legend.schemeVersion}#${legend.mappingRevision}`;
    if (identity === this.activeLegendIdentity) return;
    this.legendEntriesByCode.clear();
    const lutData = new Uint8Array(256 * 256 * 4);
    for (const entry of legend.entries) {
      const sourceCode = Number(entry.sourceCode);
      if (!Number.isSafeInteger(sourceCode) || sourceCode < 0 || sourceCode > 0xffff) continue;
      this.legendEntriesByCode.set(sourceCode, entry);
      const offset = sourceCode * 4;
      lutData[offset] = clampByte(entry.colorRgba[0]);
      lutData[offset + 1] = clampByte(entry.colorRgba[1]);
      lutData[offset + 2] = clampByte(entry.colorRgba[2]);
      lutData[offset + 3] = clampByte(entry.colorRgba[3]);
    }

    if (this.paletteTexture !== this.emptyPaletteTexture) this.paletteTexture.dispose();
    this.paletteTexture = createPaletteTexture(lutData);
    this.activeLegend = legend;
    this.activeLegendIdentity = identity;
    this.changeCallback?.();
  }

  private clearLegendPresentation(): void {
    this.legendEntriesByCode.clear();
    this.activeLegend = null;
    this.activeLegendIdentity = "";
    if (this.paletteTexture !== this.emptyPaletteTexture) this.paletteTexture.dispose();
    this.paletteTexture = this.emptyPaletteTexture;
    this.changeCallback?.();
  }

  /** Start a new coverage generation; GPU allocation remains lazy. */
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

    if (this.pendingTiles.length > 0) {
      const queued = this.pendingTiles;
      this.pendingTiles = [];
      for (const tile of queued) this.addTile(tile);
    }
    this.changeCallback?.();
    console.info("MGP: LandCoverTextureManager.initGlobalBuffer [FI]");
  }

  public addTile(tile: LandCoverTileData): boolean {
    console.info("MGP: LandCoverTextureManager.addTile [INICI]");
    const tileKey = tile.tileKey || tile.resourceId;
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
      this.pendingTiles.push(tile);
      console.info("MGP: LandCoverTextureManager.addTile [FI]");
      return true;
    }
    if (!approximatelyEqual(resolutionX, this.requestedResolution)) {
      console.warn("[LandCoverTextureManager] tile/request resolution mismatch", tileKey);
      console.info("MGP: LandCoverTextureManager.addTile [FI]");
      return false;
    }

    const descriptor = schemeDescriptor(tile);
    const schemeChanged = this.activeScheme !== null && !sameScheme(this.activeScheme, descriptor);
    if (schemeChanged) {
      this.clearCoverage(false);
    }
    this.activeScheme = descriptor;
    if (this.latestLegend && legendMatchesScheme(this.latestLegend, descriptor)) {
      this.activateLegend(this.latestLegend);
    } else if (schemeChanged) {
      this.clearLegendPresentation();
    }

    if (this.banks.length === 0) this.allocateTileArrays(tile, resolutionX, resolutionY);
    if (this.banks.length === 0) {
      console.warn("[LandCoverTextureManager] no texture banks available", tileKey);
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
      console.warn("[LandCoverTextureManager] tile outside active grid", tileKey);
      console.info("MGP: LandCoverTextureManager.addTile [FI]");
      return false;
    }

    const globalLayer = row * this.gridColumns + column;
    const bankIndex = Math.floor(globalLayer / LandCoverTextureManager.MAX_LAYERS_PER_BANK);
    const localLayer = globalLayer % LandCoverTextureManager.MAX_LAYERS_PER_BANK;
    const bank = this.banks[bankIndex];
    if (!bank) {
      console.warn("[LandCoverTextureManager] tile bank unavailable", tileKey);
      console.info("MGP: LandCoverTextureManager.addTile [FI]");
      return false;
    }

    const classLayerSize = this.layerWidth * this.layerHeight;
    const validityLayerSize = this.validityLayerWidth * this.layerHeight;
    bank.classData.set(tile.sourceCodes, localLayer * classLayerSize);
    bank.validityData.set(tile.sampleValidity, localLayer * validityLayerSize);
    requestLayerUpdate(bank.texture, localLayer);
    requestLayerUpdate(bank.validityTexture, localLayer);

    this.changeCallback?.();
    console.info("MGP: LandCoverTextureManager.addTile [FI]");
    return true;
  }

  public getObservationAtWorld(worldX: number, worldY: number): LandCoverObservation | null {
    const located = this.locatePixel(worldX, worldY);
    if (!located || !this.activeScheme) return null;
    const { bank, localLayer, pixelX, pixelY } = located;
    const classLayerSize = this.layerWidth * this.layerHeight;
    const classIndex = localLayer * classLayerSize + pixelY * this.layerWidth + pixelX;
    const sourceCode = bank.classData[classIndex];
    if (sourceCode === undefined) return null;

    const validityLayerSize = this.validityLayerWidth * this.layerHeight;
    const validityIndex = localLayer * validityLayerSize
      + pixelY * this.validityLayerWidth
      + Math.floor(pixelX / 4);
    const packedValidity = bank.validityData[validityIndex];
    if (packedValidity === undefined) return null;
    const encodedValidity = (packedValidity >> ((pixelX % 4) * 2)) & 0b11;
    const validity = sampleValidityName(encodedValidity);
    const legendMatches = this.activeLegend !== null
      && legendMatchesScheme(this.activeLegend, this.activeScheme);
    const entry = legendMatches ? this.legendEntriesByCode.get(sourceCode) : undefined;
    const valid = validity === "valid";
    const sourceClassDeclared = valid || entry?.sampleValidity === validity;
    const classificationStatus = valid
      ? entry?.classificationStatus ?? "unclassified"
      : null;
    const categoryKey = valid ? entry?.categoryKey ?? null : null;

    return {
      sourceName: legendMatches ? this.activeLegend!.sourceName : this.activeScheme.sourceName,
      schemeKey: this.activeScheme.schemeKey,
      schemeVersion: this.activeScheme.schemeVersion,
      mappingRevision: this.activeScheme.mappingRevision,
      sourceCode,
      sourceValue: sourceClassDeclared ? entry?.sourceValue ?? sourceCode : sourceCode,
      sourceLabel: sourceClassDeclared ? entry?.sourceLabel ?? null : null,
      taxonomyKey: this.activeScheme.taxonomyKey,
      taxonomyVersion: this.activeScheme.taxonomyVersion,
      categoryKey,
      categoryLabelKey: valid ? entry?.categoryLabelKey ?? null : null,
      categoryLabel: valid ? entry?.categoryLabel ?? null : null,
      qualifiers: valid ? entry?.qualifiers ?? {} : {},
      classificationStatus,
      validity,
    };
  }

  /** Compatibility view for callers that only understand valid mapped classes. */
  public getCategoryAtWorld(worldX: number, worldY: number): { classId: number; label: string } | null {
    const observation = this.getObservationAtWorld(worldX, worldY);
    if (!observation || observation.validity !== "valid" || !observation.sourceLabel) return null;
    return { classId: observation.sourceCode, label: observation.sourceLabel };
  }

  public getObservationAtUv(u: number, v: number): LandCoverObservation | null {
    if (!this.requestedBounds) return null;
    const worldX = this.requestedBounds[0] + u * (this.requestedBounds[2] - this.requestedBounds[0]);
    const worldY = this.requestedBounds[1] + v * (this.requestedBounds[3] - this.requestedBounds[1]);
    return this.getObservationAtWorld(worldX, worldY);
  }

  public getCategoryAtUv(u: number, v: number): { classId: number; label: string } | null {
    if (!this.requestedBounds) return null;
    const worldX = this.requestedBounds[0] + u * (this.requestedBounds[2] - this.requestedBounds[0]);
    const worldY = this.requestedBounds[1] + v * (this.requestedBounds[3] - this.requestedBounds[1]);
    return this.getCategoryAtWorld(worldX, worldY);
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
    this.emptyValidityTexture.dispose();
    this.emptyPaletteTexture.dispose();
  }

  private allocateTileArrays(
    tile: LandCoverTileData,
    resolutionX: number,
    resolutionY: number,
  ): void {
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
    this.validityLayerWidth = Math.ceil(tile.width / 4);
    this.gridColumns = columns;
    this.gridRows = rows;
    this.totalDepth = depth;
    this.tileWorldSize.set(tileWorldX, tileWorldY);
    this.activeBounds.set(gridMinX, gridMinY, gridMaxX, gridMaxY);

    const bankCount = Math.min(
      LandCoverTextureManager.MAX_BANKS,
      Math.ceil(depth / LandCoverTextureManager.MAX_LAYERS_PER_BANK),
    );
    const classLayerSize = tile.width * tile.height;
    const validityLayerSize = this.validityLayerWidth * tile.height;
    let remainingLayers = depth;
    this.banks = [];
    for (let bankIndex = 0; bankIndex < bankCount; bankIndex++) {
      const bankDepth = Math.min(LandCoverTextureManager.MAX_LAYERS_PER_BANK, remainingLayers);
      remainingLayers -= bankDepth;
      const classData = new Uint16Array(classLayerSize * bankDepth);
      const validityData = new Uint8Array(validityLayerSize * bankDepth);
      this.banks.push({
        bankIndex,
        depth: bankDepth,
        classData,
        texture: createClassArrayTexture(classData, tile.width, tile.height, bankDepth),
        validityData,
        validityTexture: createValidityArrayTexture(
          validityData,
          this.validityLayerWidth,
          tile.height,
          bankDepth,
        ),
      });
    }

    const totalBytes = (classLayerSize * 2 + validityLayerSize) * depth;
    console.info(
      `[LandCoverTextureManager] Allocated ${this.banks.length} persistent bank(s); `
      + `CPU buffers ${(totalBytes / (1024 * 1024)).toFixed(1)}MB`,
    );
  }

  private locatePixel(worldX: number, worldY: number): {
    bank: CoverageBank;
    localLayer: number;
    pixelX: number;
    pixelY: number;
  } | null {
    if (this.banks.length === 0 || !this.requestedBounds) return null;
    if (
      worldX < this.activeBounds.x || worldX >= this.activeBounds.z
      || worldY < this.activeBounds.y || worldY >= this.activeBounds.w
    ) return null;

    const column = Math.floor((worldX - this.activeBounds.x) / this.tileWorldSize.x);
    const row = Math.floor((this.activeBounds.w - worldY) / this.tileWorldSize.y);
    if (column < 0 || column >= this.gridColumns || row < 0 || row >= this.gridRows) return null;

    const globalLayer = row * this.gridColumns + column;
    const bankIndex = Math.floor(globalLayer / LandCoverTextureManager.MAX_LAYERS_PER_BANK);
    const localLayer = globalLayer % LandCoverTextureManager.MAX_LAYERS_PER_BANK;
    const bank = this.banks[bankIndex];
    if (!bank) return null;

    const tileStartX = this.activeBounds.x + column * this.tileWorldSize.x;
    const tileMaxY = this.activeBounds.w - row * this.tileWorldSize.y;
    const localU = Math.max(0, Math.min(0.999999, (worldX - tileStartX) / this.tileWorldSize.x));
    const localV = Math.max(0, Math.min(0.999999, (tileMaxY - worldY) / this.tileWorldSize.y));
    const pixelX = Math.floor(localU * this.layerWidth);
    const pixelY = Math.floor(localV * this.layerHeight);
    if (pixelX < 0 || pixelX >= this.layerWidth || pixelY < 0 || pixelY >= this.layerHeight) {
      return null;
    }
    return { bank, localLayer, pixelX, pixelY };
  }

  private clearCoverage(clearPending: boolean): void {
    for (const bank of this.banks) {
      bank.texture.dispose();
      bank.validityTexture.dispose();
    }
    this.banks = [];
    this.layerWidth = 0;
    this.layerHeight = 0;
    this.validityLayerWidth = 0;
    this.gridColumns = 0;
    this.gridRows = 0;
    this.totalDepth = 0;
    this.activeScheme = null;
    this.activeBounds.set(0, 0, 0, 0);
    this.tileWorldSize.set(1, 1);
    if (clearPending) this.pendingTiles = [];
  }
}

export interface LandCoverTooltipModel {
  readonly title: string;
  readonly sourceHeading: string;
  readonly rows: readonly { label: string; value: string }[];
  readonly invalidity: string | null;
}

const INVALIDITY_LABELS: Readonly<Record<Exclude<LandCoverObservation["validity"], "valid">, string>> = {
  outside_coverage: "Fora de cobertura",
  nodata: "Sense dades",
  masked: "Emmascarada",
};

export function buildLandCoverTooltipModel(
  observation: LandCoverObservation,
): LandCoverTooltipModel {
  const invalidity = observation.validity === "valid"
    ? null
    : INVALIDITY_LABELS[observation.validity];
  const title = invalidity
    ?? observation.categoryLabel
    ?? (observation.classificationStatus === "unknown"
      ? "Cobertura desconeguda"
      : observation.classificationStatus === "unclassified"
        ? "Cobertura sense classificar"
        : "Cobertura classificada");
  const rows = observation.sourceLabel === null
    ? []
    : [
      { label: "Codi", value: String(observation.sourceValue) },
      { label: "Etiqueta", value: observation.sourceLabel },
    ];
  return {
    title,
    sourceHeading: `${observation.sourceName} · ${observation.schemeVersion}`,
    rows,
    invalidity,
  };
}

export function formatLandCoverTooltip(observation: LandCoverObservation): string {
  const model = buildLandCoverTooltipModel(observation);
  const lines = [model.title, "", model.sourceHeading];
  for (const row of model.rows) lines.push(`${row.label}: ${row.value}`);
  if (model.invalidity) lines.push(`Validesa: ${model.invalidity}`);
  return lines.join("\n");
}

/** Render a tooltip without interpreting source labels as HTML. */
export function renderLandCoverTooltip(
  container: HTMLElement,
  observation: LandCoverObservation,
): void {
  const model = buildLandCoverTooltipModel(observation);
  container.replaceChildren();

  const title = document.createElement("div");
  title.textContent = model.title;
  title.style.fontWeight = "600";
  title.style.marginBottom = "8px";
  container.appendChild(title);

  const source = document.createElement("div");
  source.textContent = model.sourceHeading;
  source.style.textDecoration = "underline";
  source.style.textUnderlineOffset = "2px";
  source.style.marginBottom = model.rows.length > 0 ? "3px" : "0";
  container.appendChild(source);

  for (const row of model.rows) {
    const line = document.createElement("div");
    line.textContent = `${row.label}: ${row.value}`;
    container.appendChild(line);
  }
  if (model.invalidity) {
    const validity = document.createElement("div");
    validity.textContent = `Validesa: ${model.invalidity}`;
    container.appendChild(validity);
  }
}

function requestLayerUpdate(texture: THREE.DataArrayTexture, localLayer: number): void {
  texture.source.dataReady = true;
  texture.addLayerUpdate(localLayer);
  texture.needsUpdate = true;
}

function createClassArrayTexture(
  data: Uint16Array,
  width: number,
  height: number,
  depth: number,
): THREE.DataArrayTexture {
  const texture = new THREE.DataArrayTexture(data as Uint16Array<ArrayBuffer>, width, height, depth);
  texture.format = THREE.RedIntegerFormat;
  texture.type = THREE.UnsignedShortType;
  texture.internalFormat = "R16UI";
  configureIntegerTexture(texture);
  return texture;
}

function createValidityArrayTexture(
  data: Uint8Array,
  width: number,
  height: number,
  depth: number,
): THREE.DataArrayTexture {
  const texture = new THREE.DataArrayTexture(data as Uint8Array<ArrayBuffer>, width, height, depth);
  texture.format = THREE.RedIntegerFormat;
  texture.type = THREE.UnsignedByteType;
  texture.internalFormat = "R8UI";
  configureIntegerTexture(texture);
  return texture;
}

function configureIntegerTexture(texture: THREE.DataArrayTexture): void {
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
}

function createPaletteTexture(data: Uint8Array): THREE.DataTexture {
  const texture = new THREE.DataTexture(data, 256, 256, THREE.RGBAFormat, THREE.UnsignedByteType);
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
    && tile.dtype === "uint16"
    && tile.validityEncoding === "tlst-sample-validity-2bit-v1"
    && tile.sourceCodes.length === tile.width * tile.height
    && tile.validityRowBytes === Math.ceil(tile.width / 4)
    && tile.sampleValidity.length === tile.validityRowBytes * tile.height
    && validBounds(tile.bounds);
}

function schemeDescriptor(tile: LandCoverTileData): ActiveSchemeDescriptor {
  return {
    sourceName: tile.sourceName,
    schemeKey: tile.schemeKey,
    schemeVersion: tile.schemeVersion,
    mappingRevision: tile.mappingRevision,
    taxonomyKey: tile.taxonomyKey,
    taxonomyVersion: tile.taxonomyVersion,
  };
}

function sameScheme(a: ActiveSchemeDescriptor, b: ActiveSchemeDescriptor): boolean {
  return a.schemeKey === b.schemeKey
    && a.schemeVersion === b.schemeVersion
    && a.mappingRevision === b.mappingRevision
    && a.taxonomyKey === b.taxonomyKey
    && a.taxonomyVersion === b.taxonomyVersion;
}

function legendMatchesScheme(
  legend: LandCoverLegendData,
  scheme: ActiveSchemeDescriptor,
): boolean {
  return legend.schemeKey === scheme.schemeKey
    && legend.schemeVersion === scheme.schemeVersion
    && legend.mappingRevision === scheme.mappingRevision
    && legend.taxonomyKey === scheme.taxonomyKey
    && legend.taxonomyVersion === scheme.taxonomyVersion;
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
