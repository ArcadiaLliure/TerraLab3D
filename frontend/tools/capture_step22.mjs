import fs from "node:fs/promises";
import path from "node:path";
import puppeteer from "puppeteer";

const baseUrl = process.argv[2] ?? "http://127.0.0.1:14398/";
const pas22Dir = path.resolve(import.meta.dirname, "../../docs/evidencies/pas22");

await fs.mkdir(pas22Dir, { recursive: true });

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

const browserErrors = [];
page.on("pageerror", err => browserErrors.push(String(err)));
page.on("console", msg => {
  if (msg.type() === "error") browserErrors.push(msg.text());
});

console.log("Carregant TerraLab3D...");
await page.goto(baseUrl, { waitUntil: "domcontentloaded", timeout: 45_000 });

await page.waitForSelector('button[title="Cel"]', { timeout: 30_000 });
await new Promise(resolve => setTimeout(resolve, 3_000));

console.log("Esperant càrrega de terreny DEM...");
for (let i = 0; i < 30; i++) {
  const ready = await page.evaluate(() => window.__isDemLoaded?.() === true);
  if (ready) break;
  await new Promise(r => setTimeout(r, 1_000));
}

// Configurar entorn de nit fosca (Bortle 1) i Via Làctia
console.log("Configurant condicions nocturnes...");
await page.evaluate(async () => {
  window.__setBortle?.(1.0);
  await window.__setMilkyWayVisible?.(true);
  window.__setConstellationsVisible?.(false);
  const ctrl = window.__getConstellationController?.();
  if (ctrl) {
    ctrl.setShowAll(false);
    ctrl.setSelectedOfficial(null);
  }
});
await new Promise(resolve => setTimeout(resolve, 2_000));

// ─── 1. Panoràmica nocturna: Lluna en culminació màxima al sud amb Alba i Posta simultànies ───
console.log("Seleccionant Lluna i configurant culminació nocturna...");
await page.evaluate(() => {
  window.__selectTarget?.("moon");
  window.__setSimulationTime?.("2026-09-20T19:50:10Z");
  window.__setHudVisible?.(false);
  window.__closeDrawer?.();
  window.__setConstellationsVisible?.(false);
  window.__setCameraPose?.(180.0, 20.0, 115.0);
});
await new Promise(resolve => setTimeout(resolve, 3_500));

await saveScreenshot(page, path.join(pas22Dir, "trajectoria-completa.png"));
await saveScreenshot(page, path.join(pas22Dir, "alba.png"));
await saveScreenshot(page, path.join(pas22Dir, "puesta.png"));
await saveScreenshot(page, path.join(pas22Dir, "hidden-segments.png"));
await saveScreenshot(page, path.join(pas22Dir, "real-horizon.png"));
await saveScreenshot(page, path.join(pas22Dir, "time-marker-and-labels.png"));

// ─── 2. Horitzó astronòmic 0° ───
console.log("Capturant horitzó astronòmic 0°...");
await page.click('button[title="Topografia"]');
await page.waitForSelector('#earth-horizon-enabled', { timeout: 10_000 });
await page.click('#earth-horizon-enabled');
await new Promise(resolve => setTimeout(resolve, 1_500));
await page.click('button[title="Topografia"]');
await page.evaluate(() => {
  window.__setHudVisible?.(false);
  window.__closeDrawer?.();
  window.__setConstellationsVisible?.(false);
  window.__setCameraPose?.(180.0, 20.0, 115.0);
  window.__requestTrajectory?.();
});
await new Promise(resolve => setTimeout(resolve, 3_000));
await saveScreenshot(page, path.join(pas22Dir, "astronomical-horizon.png"));

// Reactivar horitzó real
await page.click('button[title="Topografia"]');
await page.waitForSelector('#earth-horizon-enabled', { timeout: 10_000 });
await page.click('#earth-horizon-enabled');
await new Promise(resolve => setTimeout(resolve, 1_000));
await page.click('button[title="Topografia"]');

console.log("Captures del Pas 22 finalitzades amb èxit!", { browserErrors });
await browser.close();
