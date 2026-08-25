import * as THREE from "three";
import {
  buildLandCoverTooltipModel,
  formatLandCoverTooltip,
  LandCoverTextureManager,
  type LandCoverLegendData,
  type LandCoverTileData,
} from "../view/three/terrain/LandCoverTextureManager";
import { decodeLandCoverTile, type LandCoverTileMetadata } from "../contracts/land_cover_contracts";
import { DemTerrainLayerRenderer } from "../view/three/layers/DemTerrainLayerRenderer";
import { MoonSurfaceRenderer } from "../view/three/MoonSurfaceRenderer";
import type { MoonSurfaceResourceDescriptor } from "../contracts/solar_system_contracts";
import { resourceImportAction } from "../view/ui/modals/ResourceManagerModal";

let passed = 0;
let failed = 0;

function assert(condition: boolean, message: string): void {
  if (condition) {
    passed++;
    console.log(`  ✓ ${message}`);
  } else {
    failed++;
    console.error(`  ✗ FAIL: ${message}`);
  }
}

const tileWidth = 32;
const tileHeight = 32;
const tileResolution = 10;

const categoricalImport = resourceImportAction("earth", "categorical");
assert(categoricalImport.available, "Categorical import is available in the resource manager");
assert(
  !/vertical\s*\d/i.test(categoricalImport.title),
  "Categorical import does not expose internal delivery terminology",
);
assert(
  categoricalImport.title === "Importar una classificació de cobertes del sòl",
  "Categorical import uses a user-facing description",
);

const validPacked = new Uint8Array(Math.ceil(tileWidth / 4) * tileHeight);
validPacked.fill(0x55); // 01 repeated: four valid samples per byte.

function makeTile(
  tileKey: string,
  bounds: [number, number, number, number],
  sourceCodes: Uint16Array,
  sampleValidity: Uint8Array = validPacked,
): LandCoverTileData {
  const sourceCodeByteLength = sourceCodes.byteLength;
  return {
    role: "land_cover_tile",
    resourceId: tileKey,
    tileKey,
    version: 1,
    bounds,
    width: tileWidth,
    height: tileHeight,
    resolution: tileResolution,
    sourceId: "s2glc-fixture",
    sourceName: "Configured S2GLC fixture",
    schemeKey: "s2glc_europe",
    schemeVersion: "2017-v1.2",
    mappingRevision: "official-v1",
    taxonomyKey: "TLST",
    taxonomyVersion: "1.0",
    sourceDtype: "uint8",
    dtype: "uint16",
    sourceCodeOffset: 0,
    sourceCodeByteLength,
    sampleValidityOffset: sourceCodeByteLength,
    sampleValidityByteLength: sampleValidity.byteLength,
    validityEncoding: "tlst-sample-validity-2bit-v1",
    validityRowBytes: Math.ceil(tileWidth / 4),
    validPixels: tileWidth * tileHeight,
    sourceCodes,
    sampleValidity,
  };
}

function legendEntry(
  sourceCode: number,
  sourceLabel: string,
  colorRgba: [number, number, number, number],
  categoryKey: string | null,
  sampleValidity: "masked" | "nodata" | null = null,
) {
  const categoryLabels: Readonly<Record<string, string>> = {
    "artificial.unspecified": "Superfície artificial sense especificar",
    "agriculture.cropland.permanent_crop.vineyard": "Vinya",
    "water.unspecified": "Aigua sense especificar",
  };
  return {
    sourceCode,
    sourceValue: sourceCode,
    sourceLabel,
    sourceLabelKey: `fixture.${sourceCode}`,
    colorRgba,
    sampleValidity,
    classificationStatus: categoryKey ? "classified" as const : null,
    categoryKey,
    categoryLabelKey: categoryKey ? `tlst.category.${categoryKey}` : null,
    categoryLabel: categoryKey ? categoryLabels[categoryKey] ?? categoryKey : null,
    qualifiers: {},
    mappingKind: sampleValidity ? "observation_state" as const : "single" as const,
    resolvedPath: categoryKey ? categoryKey.split(".") : [],
    semanticDepth: categoryKey ? categoryKey.split(".").length : null,
    unresolvedChildren: [],
  };
}

const testLegend: LandCoverLegendData = {
  type: "land_cover_legend",
  schemeKey: "s2glc_europe",
  schemeVersion: "2017-v1.2",
  mappingRevision: "official-v1",
  sourceName: "S2GLC Europe",
  taxonomyKey: "TLST",
  taxonomyVersion: "1.0",
  entries: [
    legendEntry(0, "Clouds", [0, 0, 0, 0], null, "masked"),
    legendEntry(62, "Artificial surfaces", [230, 20, 20, 255], "artificial.unspecified"),
    legendEntry(75, "Vineyards", [176, 91, 16, 255], "agriculture.cropland.permanent_crop.vineyard"),
    legendEntry(162, "Water bodies", [20, 80, 220, 255], "water.unspecified"),
  ],
};

console.log("=== TerraLab3D TLST categorical texture and lifecycle tests ===");

const manager = new LandCoverTextureManager();
assert(manager.banks.length === 0, "No banks allocated initially");
assert(manager.activeCoverageTexture === null, "Source-code texture is absent initially");
assert(manager.activeValidityTexture === null, "Validity texture is absent initially");
assert(manager.emptyCoverageTexture instanceof THREE.DataArrayTexture, "Code fallback is persistent");
assert(manager.emptyValidityTexture instanceof THREE.DataArrayTexture, "Validity fallback is persistent");
assert(manager.paletteTexture === manager.emptyPaletteTexture, "Palette defaults to persistent fallback");

const globalBounds: [number, number, number, number] = [-640, -640, 640, 640];
manager.initGlobalBuffer(globalBounds, tileResolution);
const firstCodes = new Uint16Array(tileWidth * tileHeight);
firstCodes.fill(62);
const tile00 = makeTile("landcover.0_0.g1", [-640, -640, -320, -320], firstCodes);
assert(manager.addTile(tile00), "First source-code/validity tile is accepted");
assert(manager.banks.length === 1, "One bank allocated for a 4x4 tile grid");
assert(manager.banks[0]!.depth === 16, "Bank depth matches grid depth");
assert(manager.banks[0]!.texture.image.width === tileWidth, "R16UI texture keeps source width");
assert(manager.banks[0]!.texture.internalFormat === "R16UI", "Source codes use R16UI");
assert(manager.banks[0]!.validityTexture.image.width === tileWidth / 4, "Validity stays 2-bit packed");
assert(manager.banks[0]!.validityTexture.internalFormat === "R8UI", "Validity uses R8UI");
assert(manager.banks[0]!.texture.layerUpdates.has(12), "Code layer receives incremental update");
assert(manager.banks[0]!.validityTexture.layerUpdates.has(12), "Validity layer receives incremental update");

const largeBounds: [number, number, number, number] = [-4800, -4800, 4800, 4800];
manager.initGlobalBuffer(largeBounds, tileResolution);
manager.addTile(makeTile("tile.bank0", [-4800, 4480, -4480, 4800], firstCodes));
assert(manager.banks.length === 4, "900 tiles are partitioned into four persistent banks");
assert(manager.banks[0]!.depth === 256, "Bank 0 has 256 layers");
assert(manager.banks[3]!.depth === 132, "Bank 3 has the remaining 132 layers");
assert(manager.totalDepth === 900, "Full 150 km-equivalent grid depth is retained");

manager.addTile(makeTile("tile.bank1", [-4800, 1280, -4480, 1600], firstCodes));
assert(manager.banks[1]!.texture.layerUpdates.has(44), "Bank 1 updates only local layer 44");
manager.addTile(makeTile("tile.bank3", [-1600, -4480, -1280, -4160], firstCodes));
assert(manager.banks[3]!.texture.layerUpdates.has(82), "Bank 3 updates only local layer 82");

const newBounds: [number, number, number, number] = [-320, -320, 320, 320];
manager.initGlobalBuffer(newBounds, tileResolution);
assert(manager.banks.length === 0, "Changing coverage disposes old banks before lazy allocation");
const vineyardCodes = new Uint16Array(tileWidth * tileHeight);
vineyardCodes.fill(75);
manager.addTile(makeTile("landcover.vineyard.g2", [-320, -320, 0, 0], vineyardCodes));
assert(manager.banks.length === 1, "New coverage recreates one bank");

manager.updateLegend(testLegend);
const paletteArray = manager.paletteTexture.image.data as Uint8Array;
assert(paletteArray[75 * 4] === 176, "Palette LUT is keyed by raw source code");

const vineyard = manager.getObservationAtWorld(-319, -1);
assert(vineyard?.sourceCode === 75, "Picking returns the original source code");
assert(vineyard?.sourceLabel === "Vineyards", "Picking resolves the official source label once");
assert(
  vineyard?.categoryKey === "agriculture.cropland.permanent_crop.vineyard",
  "Picking resolves TLST without per-pixel semantic objects",
);
assert(vineyard?.validity === "valid", "Picking decodes packed validity");
if (vineyard) {
  const tooltipModel = buildLandCoverTooltipModel(vineyard);
  assert(tooltipModel.title === "Vinya", "Tooltip uses the Catalan descriptive TLST label");
  assert(tooltipModel.invalidity === null, "A valid sample does not print validity");
  assert(
    formatLandCoverTooltip(vineyard) === [
      "Vinya",
      "",
      "S2GLC Europe · 2017-v1.2",
      "Codi: 75",
      "Etiqueta: Vineyards",
    ].join("\n"),
    "Scientific tooltip preserves source and presents the interpretation",
  );
  assert(!formatLandCoverTooltip(vineyard).includes(vineyard.categoryKey!), "Tooltip hides the TLST key");
}

const maskedPacked = new Uint8Array(Math.ceil(tileWidth / 4) * tileHeight);
maskedPacked.fill(0xff); // 11 repeated: masked.
const cloudCodes = new Uint16Array(tileWidth * tileHeight);
manager.initGlobalBuffer(globalBounds, tileResolution);
manager.addTile(makeTile("landcover.clouds.g3", [-640, -640, -320, -320], cloudCodes, maskedPacked));
const masked = manager.getObservationAtWorld(-639, -321);
assert(masked?.validity === "masked", "Code zero can represent masked for S2GLC");
assert(masked?.categoryKey === null, "Invalid samples never receive TLST categories");
assert(masked !== null && !formatLandCoverTooltip(masked).includes("TLST 1.0"), "Invalid tooltip omits TLST");
assert(masked !== null && formatLandCoverTooltip(masked).includes("Validesa: Emmascarada"), "Invalid tooltip localizes validity");

const nodataPacked = new Uint8Array(Math.ceil(tileWidth / 4) * tileHeight);
nodataPacked.fill(0xaa); // 10 repeated: nodata.
manager.addTile(makeTile("landcover.physical-nodata.g3", [-640, -640, -320, -320], cloudCodes, nodataPacked));
const physicalNodata = manager.getObservationAtWorld(-639, -321);
assert(
  physicalNodata?.sourceLabel === null,
  "Physical invalidity does not invent a declared source class from an execution code",
);
const worldCoverTile: LandCoverTileData = {
  ...makeTile("worldcover.nodata.g4", [-640, -640, -320, -320], cloudCodes, nodataPacked),
  sourceId: "worldcover-fixture",
  sourceName: "Configured WorldCover fixture",
  schemeKey: "esa_worldcover",
  schemeVersion: "2021-v200",
};
manager.addTile(worldCoverTile);
const worldCoverNodata = manager.getObservationAtWorld(-639, -321);
assert(worldCoverNodata?.validity === "nodata", "The same code zero can represent WorldCover nodata");
assert(worldCoverNodata?.sourceLabel === null, "A stale S2GLC legend is never applied to WorldCover");
assert(manager.paletteTexture === manager.emptyPaletteTexture, "Scheme changes clear a stale source palette");

const metadata = { ...tile00 } as unknown as LandCoverTileMetadata;
const payload = new Uint8Array(tile00.sourceCodeByteLength + tile00.sampleValidityByteLength);
payload.set(new Uint8Array(tile00.sourceCodes.buffer), 0);
payload.set(tile00.sampleValidity, tile00.sampleValidityOffset);
const decoded = decodeLandCoverTile(metadata, payload.buffer);
assert(decoded.sourceCodes[0] === 62, "Bridge decoder splits uint16 source codes");
assert(decoded.sampleValidity[0] === 0x55, "Bridge decoder splits packed validity");

const parent = new THREE.Group();
const demRenderer = new DemTerrainLayerRenderer(parent);
const demUniforms = (demRenderer as any).surfaceUniforms;
assert(demUniforms.hasLandCover.value === 0, "DEM starts with categorical rendering disabled");
assert(
  demUniforms.landCoverValidityTex0.value === demRenderer.landCoverManager.emptyValidityTexture,
  "DEM starts with the persistent validity fallback",
);
demRenderer.landCoverManager.initGlobalBuffer(globalBounds, tileResolution);
demRenderer.landCoverManager.addTile(tile00);
demRenderer.updateShaderUniforms();
assert(demUniforms.hasLandCover.value === 1, "Categorical rendering activates after a tile");
assert(
  demUniforms.landCoverValidityTex0.value === demRenderer.landCoverManager.banks[0]!.validityTexture,
  "Shader receives the packed validity bank",
);
demRenderer.landCoverManager.clear();
demRenderer.updateShaderUniforms();
assert(demUniforms.hasLandCover.value === 0, "Clearing returns to fallback rendering");

let loadCount = 0;
const mockLoader = (_url: string, onLoad: (texture: THREE.Texture) => void) => {
  loadCount++;
  onLoad(new THREE.Texture());
};
const moonRenderer = new MoonSurfaceRenderer(parent, mockLoader);
const moonDescriptor: MoonSurfaceResourceDescriptor = {
  label: "LRO 2025",
  status: "ready",
  datasetId: "nasa-cgi-moon-kit-lro-lola",
  version: "LROC color map 2025",
  projection: "global equirectangular/cylindrical",
  centralLongitudeDeg: 0,
  colorSpace: "sRGB",
  albedo8k: { role: "albedo_8k", name: "8k.png", url: "/assets/moon/lro_albedo_8k.png", widthPx: 8192, heightPx: 4096, sha256: "a".repeat(64), byteSize: 1024 },
  normalMap: { role: "normal_4k", name: "normal.png", url: "/assets/moon/lro_normal_4k.png", widthPx: 4096, heightPx: 2048, sha256: "b".repeat(64), byteSize: 1024 },
  albedo4k: { role: "albedo_4k", name: "4k.png", url: "/assets/moon/lro_albedo_4k.png", widthPx: 4096, heightPx: 2048, sha256: "c".repeat(64), byteSize: 1024 },
  credits: ["NASA/LRO"],
  detail: null,
};
moonRenderer.configureResource(moonDescriptor, 8192);
const firstAlbedoCount = moonRenderer.metrics().albedoTextureLoadCount;
moonRenderer.configureResource(moonDescriptor, 8192);
assert(loadCount === 2, "Unrelated Moon textures remain idempotent");
assert(moonRenderer.metrics().albedoTextureLoadCount === firstAlbedoCount, "Land-cover changes do not reload Moon resources");

demRenderer.dispose();
manager.dispose();
moonRenderer.dispose();

console.log(`\n=== Land Cover Test Results: ${passed} passed, ${failed} failed ===`);
if (failed > 0) throw new Error(`${failed} land-cover test(s) failed`);
