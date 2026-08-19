import * as THREE from "three";
import { LandCoverTextureManager, LandCoverTileData, LandCoverLegendData } from "../view/three/terrain/LandCoverTextureManager";
import { DemTerrainLayerRenderer } from "../view/three/layers/DemTerrainLayerRenderer";
import { MoonSurfaceRenderer } from "../view/three/MoonSurfaceRenderer";
import type { MoonSurfaceResourceDescriptor } from "../contracts/solar_system_contracts";

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

console.log("=== TerraLab3D Land Cover Banked Categorical Texture & WebGL Lifecycle Tests ===");

// 1. Creació inicial de la cobertura
console.log("\n1. Creació inicial de la cobertura");
const manager = new LandCoverTextureManager();
assert(manager.banks.length === 0, "No banks allocated initially");
assert(manager.activeCoverageTexture === null, "activeCoverageTexture is null initially");
assert(manager.emptyCoverageTexture instanceof THREE.DataArrayTexture, "emptyCoverageTexture is a valid fallback DataArrayTexture");
assert(manager.emptyCoverageTexture.image.width === 1, "emptyCoverageTexture has width 1");
assert(manager.emptyCoverageTexture.image.depth === 1, "emptyCoverageTexture has depth 1");
assert(manager.emptyPaletteTexture instanceof THREE.DataTexture, "emptyPaletteTexture is a valid DataTexture");
assert(manager.paletteTexture === manager.emptyPaletteTexture, "paletteTexture defaults to emptyPaletteTexture");

// 2. Recepció de la primera tile (lazy allocation)
console.log("\n2. Recepció de la primera tile (lazy allocation)");
const globalBounds: [number, number, number, number] = [-20480, -20480, 20480, 20480];
const resolution = 10.0;
manager.initGlobalBuffer(globalBounds, resolution);

const tileWidth = 1024;
const tileHeight = 1024;

const firstTileData = new Uint16Array(tileWidth * tileHeight);
firstTileData.fill(62); // Agricultural land
const tile00: LandCoverTileData = {
  tileKey: "landcover.0_0.g1",
  bounds: [-20480, -20480, -10240, -10240], // col 0, row 3 => globalLayer = 12
  width: tileWidth,
  height: tileHeight,
  nodataValue: 0,
  data: firstTileData,
};

const acceptedFirst = manager.addTile(tile00);
assert(acceptedFirst, "First tile accepted successfully");
assert(manager.banks.length === 1, "1 bank allocated for 16 layers (<=256)");
assert(manager.banks[0]!.depth === 16, "Bank 0 depth matches 16 layers");
assert(manager.banks[0]!.texture.image.width === 1024, "Array texture width matches tile width (1024)");
assert(manager.banks[0]!.texture.image.height === 1024, "Array texture height matches tile height (1024)");
assert(manager.banks[0]!.texture.format === THREE.RedIntegerFormat, "Texture format is RedIntegerFormat");
assert(manager.banks[0]!.texture.type === THREE.UnsignedShortType, "Texture type is UnsignedShortType");
assert(manager.banks[0]!.texture.internalFormat === "R16UI", "Texture internalFormat is R16UI");
assert(manager.banks[0]!.texture.layerUpdates.has(12), "Layer 12 update registered in Bank 0 layerUpdates set");
assert(manager.banks[0]!.texture.version > 0, "Bank 0 texture version incremented for GPU upload");

// 3. Suport per radi complet de 150 km (900 rajoles = 4 bancs de DataArrayTexture)
console.log("\n3. Suport per radi complet de 150 km (900 rajoles en 4 bancs)");
const largeBounds150km: [number, number, number, number] = [-153600, -153600, 153600, 153600]; // 30x30 = 900 tiles
manager.initGlobalBuffer(largeBounds150km, resolution);

// Tile in Bank 0 (e.g. col 0, row 0 => globalLayer 0 => Bank 0, localLayer 0)
manager.addTile({
  tileKey: "tile.bank0",
  bounds: [-153600, 143360, -143360, 153600], // col 0, row 0 => globalLayer 0
  width: tileWidth,
  height: tileHeight,
  nodataValue: 0,
  data: firstTileData,
});
assert(manager.banks.length === 4, "4 banks allocated for 900 layers (256, 256, 256, 132)");
assert(manager.banks[0]!.depth === 256, "Bank 0 has depth 256");
assert(manager.banks[1]!.depth === 256, "Bank 1 has depth 256");
assert(manager.banks[2]!.depth === 256, "Bank 2 has depth 256");
assert(manager.banks[3]!.depth === 132, "Bank 3 has depth 132");
assert(manager.totalDepth === 900, "Total depth is exactly 900 layers for 150km coverage");
assert(manager.banks[0]!.texture.layerUpdates.has(0), "Bank 0 received localLayer 0 update");

// 4. Actualització parcial de layers a bancs diferents (Bank 1 i Bank 3)
console.log("\n4. Actualització parcial de layers a bancs diferents");
// Tile in Bank 1: globalLayer = 300 => Bank 1 (layers 256..511), localLayer = 44
// col = 0, row = 10 => globalLayer = 10 * 30 + 0 = 300
manager.addTile({
  tileKey: "tile.bank1",
  bounds: [-153600, 40960, -143360, 51200], // col 0, row 10 => globalLayer 300
  width: tileWidth,
  height: tileHeight,
  nodataValue: 0,
  data: firstTileData,
});
assert(manager.banks[1]!.texture.layerUpdates.has(44), "Bank 1 received localLayer 44 update for globalLayer 300");

// Tile in Bank 3: globalLayer = 850 => Bank 3 (layers 768..899), localLayer = 82
// col = 10, row = 28 => globalLayer = 28 * 30 + 10 = 850
manager.addTile({
  tileKey: "tile.bank3",
  bounds: [-51200, -143360, -40960, -133120], // col 10, row 28 => globalLayer 850
  width: tileWidth,
  height: tileHeight,
  nodataValue: 0,
  data: firstTileData,
});
assert(manager.banks[3]!.texture.layerUpdates.has(82), "Bank 3 received localLayer 82 update for globalLayer 850");

// 5. Canvi de cobertura o regeneració de la textura
console.log("\n5. Canvi de cobertura o regeneració de la textura");
const newBounds: [number, number, number, number] = [-10240, -10240, 10240, 10240]; // 2x2 = 4 layers
manager.initGlobalBuffer(newBounds, resolution);
assert(manager.banks.length === 0, "Old banks are disposed upon buffer bounds re-initialization");

const newTileData = new Uint16Array(tileWidth * tileHeight);
newTileData.fill(162);
manager.addTile({
  tileKey: "landcover.new_0_0.g2",
  bounds: [-10240, -10240, 0, 0],
  width: tileWidth,
  height: tileHeight,
  nodataValue: 0,
  data: newTileData,
});
assert(manager.banks.length === 1, "New single bank allocated for small 2x2 grid");
assert(manager.banks[0]!.depth === 4, "New bank depth matches 4 layers");

// 6. dispose() i posterior recreació
console.log("\n6. dispose() i posterior recreació");
manager.dispose();
assert(manager.banks.length === 0, "All banks disposed on manager.dispose()");
manager.initGlobalBuffer(newBounds, resolution);
manager.addTile({
  tileKey: "landcover.recreated.g3",
  bounds: [-10240, -10240, 0, 0],
  width: tileWidth,
  height: tileHeight,
  nodataValue: 0,
  data: newTileData,
});
assert(manager.banks.length === 1, "Manager recreates bank cleanly after dispose");

// 7. Recepció de tile abans/després de la llegenda
console.log("\n7. Recepció de tile abans/després de la llegenda");
const testLegend: LandCoverLegendData = {
  legendId: "clc_plus",
  entries: [
    { classId: 62, label: "Cultius", colorRgba: [230, 200, 50, 255] },
    { classId: 82, label: "Boscos", colorRgba: [30, 150, 40, 255] },
    { classId: 102, label: "Aigua", colorRgba: [20, 80, 220, 255] },
  ],
};
manager.updateLegend(testLegend);
assert(manager.paletteTexture !== manager.emptyPaletteTexture, "paletteTexture updated with custom legend");
assert(manager.paletteTexture.image.width === 256, "LUT palette texture is 256x256");
assert(manager.paletteTexture.image.height === 256, "LUT palette texture height is 256");
const paletteArray = manager.paletteTexture.image.data as Uint8Array;
assert(paletteArray[62 * 4] === 230, "Class 62 Red channel matched in LUT");
assert(paletteArray[62 * 4 + 1] === 200, "Class 62 Green channel matched in LUT");
assert(paletteArray[62 * 4 + 2] === 50, "Class 62 Blue channel matched in LUT");
assert(paletteArray[62 * 4 + 3] === 255, "Class 62 Alpha channel matched in LUT");

// 8. Identificació correcta de tileKey / resourceId
console.log("\n8. Identificació correcta de tileKey / resourceId");
const tileWithResourceIdOnly = {
  resourceId: "landcover_s2glc.0_0.g1",
  bounds: [-10240, -10240, 0, 0] as [number, number, number, number],
  width: tileWidth,
  height: tileHeight,
  nodataValue: 0,
  data: new Uint16Array(tileWidth * tileHeight),
};
const acceptedResourceId = manager.addTile(tileWithResourceIdOnly as any);
assert(acceptedResourceId, "Tile with resourceId only (no tileKey) is accepted without being undefined");

// 9. Absència de regressions en el renderitzat DEM sense cobertura categòrica
console.log("\n9. Absència de regressions en el renderitzat DEM sense cobertura categòrica");
const parent = new THREE.Group();
const demRenderer = new DemTerrainLayerRenderer(parent);
const demUniforms = (demRenderer as any).surfaceUniforms;
assert(demUniforms.hasLandCover.value === 0, "hasLandCover uniform is 0 initially (no land cover)");
assert(demUniforms.landCoverTex0.value === demRenderer.landCoverManager.emptyCoverageTexture, "landCoverTex0 uses fallback empty coverage texture");
assert(demUniforms.landCoverLUT.value === demRenderer.landCoverManager.emptyPaletteTexture, "landCoverLUT uses fallback empty palette texture");

demRenderer.landCoverManager.initGlobalBuffer(globalBounds, resolution);
demRenderer.landCoverManager.addTile(tile00);
demRenderer.updateShaderUniforms();
assert(demUniforms.hasLandCover.value === 1, "hasLandCover uniform becomes 1 once categorical coverage is active");
assert(demUniforms.landCoverTex0.value === demRenderer.landCoverManager.banks[0]!.texture, "landCoverTex0 binds active Bank 0 texture");

demRenderer.landCoverManager.clear();
demRenderer.updateShaderUniforms();
assert(demUniforms.hasLandCover.value === 0, "hasLandCover uniform returns to 0 on clear()");
assert(demUniforms.landCoverTex0.value === demRenderer.landCoverManager.emptyCoverageTexture, "landCoverTex0 safely falls back to emptyCoverageTexture");

// 10. Verificació de no regressió a la Lluna (Idempotència de textures / no pampallugues)
console.log("\n10. Verificació de no regressió a la Lluna");
let loadCount = 0;
const mockLoader = (url: string, onLoad: (t: THREE.Texture) => void) => {
  loadCount++;
  const tex = new THREE.Texture();
  onLoad(tex);
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
assert(loadCount === 2, "First configureResource loads albedo and normal textures");
const firstAlbedoCount = moonRenderer.metrics().albedoTextureLoadCount;

// Re-configure with identical descriptor must NOT reload or flash fallback disc
moonRenderer.configureResource(moonDescriptor, 8192);
assert(moonRenderer.metrics().albedoTextureLoadCount === firstAlbedoCount, "Second configureResource with same descriptor is idempotent (no reload)");
assert(moonRenderer.metrics().surfaceStatus === "ready", "Moon surfaceStatus remains ready (no flickering)");

demRenderer.dispose();
manager.dispose();
moonRenderer.dispose();

console.log(`\n=== Land Cover Test Results: ${passed} passed, ${failed} failed ===`);
if (failed > 0 && typeof process !== "undefined") (process as any).exit(1);
