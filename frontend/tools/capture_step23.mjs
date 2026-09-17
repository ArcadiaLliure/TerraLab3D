import fs from "node:fs/promises";
import path from "node:path";
import puppeteer from "puppeteer";

const baseUrl = process.argv[2] ?? "http://127.0.0.1:14398/";
const pas23Dir = path.resolve(import.meta.dirname, "../../docs/evidencies/pas23");

await fs.mkdir(pas23Dir, { recursive: true });

async function saveScreenshot(page, targetPath) {
  const buffer = await page.screenshot();
  for (let attempt = 0; attempt < 5; attempt++) {
    try {
      try { await fs.unlink(targetPath); } catch {}
      await fs.writeFile(targetPath, buffer);
      console.log(`[CAPTURA DESADA]: ${targetPath}`);
      return;
    } catch (e) {
      if (attempt === 4) throw e;
      await new Promise(r => setTimeout(r, 500));
    }
  }
}

console.log(`Llançant Puppeteer cap a ${baseUrl}...`);
const browser = await puppeteer.launch({
  headless: true,
  args: ["--no-sandbox", "--disable-setuid-sandbox", "--enable-webgl", "--use-gl=angle"],
});

const page = await browser.newPage();
await page.setViewport({ width: 1920, height: 1080, deviceScaleFactor: 1.5 });

console.log("Carregant TerraLab3D...");
await page.goto(baseUrl, { waitUntil: "domcontentloaded", timeout: 45_000 });
await page.waitForSelector('button[title="Cel"]', { timeout: 30_000 });
await new Promise(resolve => setTimeout(resolve, 3_000));

// Esperar DEM
console.log("Esperant càrrega de terreny DEM...");
for (let i = 0; i < 30; i++) {
  const ready = await page.evaluate(() => window.__isDemLoaded?.() === true);
  if (ready) break;
  await new Promise(r => setTimeout(r, 1_000));
}

// Configurant condicions d'observació nocturna
await page.evaluate(async () => {
  window.__setBortle?.(1.0);
  await window.__setMilkyWayVisible?.(true);
  window.__selectTarget?.(null);
  window.__setSimulationTime?.("2026-09-16T21:30:00Z");
  window.__setHudVisible?.(false);
  window.__closeDrawer?.();
});
await new Promise(resolve => setTimeout(resolve, 2_000));

// ─── 1. Constel·lació personalitzada SENCERA amb marges còmodes i sense altres constel·lacions ───
console.log("1. Configurant i capturant constel·lació personalitzada SENCERA...");
await page.evaluate(() => {
  const ctrl = window.__getConstellationController?.();
  if (ctrl) {
    const doc = {
      type: "constellation_document",
      schemaVersion: 1,
      documentRevision: 1,
      constellations: [
        {
          constellationId: "user-summer-triangle",
          name: "Triangle d'Estiu propi",
          entityVersion: 1,
          nodes: [
            { nodeId: "n1", sourceId: "vega", starName: "Vega", startsNewStroke: true, raDeg: 279.2347, decDeg: 38.7837 },
            { nodeId: "n2", sourceId: "deneb", starName: "Deneb", startsNewStroke: false, raDeg: 310.3579, decDeg: 45.2803 },
            { nodeId: "n3", sourceId: "altair", starName: "Altair", startsNewStroke: false, raDeg: 297.6958, decDeg: 8.8683 },
            { nodeId: "n4", sourceId: "vega2", starName: "Vega", startsNewStroke: false, raDeg: 279.2347, decDeg: 38.7837 },
          ],
          strokes: [
            [
              { raDeg: 279.2347, decDeg: 38.7837 },
              { raDeg: 310.3579, decDeg: 45.2803 },
              { raDeg: 297.6958, decDeg: 8.8683 },
              { raDeg: 279.2347, decDeg: 38.7837 },
            ],
          ],
        },
      ],
      selectedConstellationId: "user-summer-triangle",
      editing: false,
      canUndo: false,
      canRedo: false,
      warning: null,
    };
    ctrl.present(doc);
    ctrl.setShowAll(false);
    ctrl.setSelectedOfficial(null);
  }
  window.__setConstellationsVisible?.(true);
  // Pose per enquadrar Vega, Deneb i Altair completament sencers amb marges còmodes
  window.__setCameraPose?.(230.0, 60.0, 92.0);
  window.__setHudVisible?.(false);
  window.__closeDrawer?.();
});
await new Promise(resolve => setTimeout(resolve, 3_500));
await saveScreenshot(page, path.join(pas23Dir, "edicio-i-visibilitat.png"));

// ─── 2. Catàleg de constel·lacions amb ZOOM OUT A TOPE (FOV 115°), SENSE constel·lació personalitzada ───
console.log("2. Configurant i capturant catàleg de constel·lacions amb ZOOM OUT A TOPE...");
await page.evaluate(() => {
  const ctrl = window.__getConstellationController?.();
  if (ctrl) {
    const emptyDoc = {
      type: "constellation_document",
      schemaVersion: 1,
      documentRevision: 2,
      constellations: [],
      selectedConstellationId: null,
      editing: false,
      canUndo: false,
      canRedo: false,
      warning: null,
    };
    ctrl.present(emptyDoc);
    ctrl.setShowAll(true);
    ctrl.setSelectedOfficial(null);
  }
  window.__setConstellationsVisible?.(true);
  // Panoràmica del cel nocturn a zoom out màxim (FOV 115°)
  window.__setCameraPose?.(210.0, 52.0, 115.0);
  window.__setHudVisible?.(false);
  window.__closeDrawer?.();
});
await new Promise(resolve => setTimeout(resolve, 3_500));
await saveScreenshot(page, path.join(pas23Dir, "constellacio-amb-trajectoria.png"));

console.log("Captures del Pas 23 finalitzades amb èxit!");
await browser.close();
