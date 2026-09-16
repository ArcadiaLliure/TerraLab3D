import fs from "node:fs/promises";
import path from "node:path";
import puppeteer from "puppeteer";

const baseUrl = process.argv[2] ?? "http://127.0.0.1:14398/";
const outputDir = path.resolve(import.meta.dirname, "../../docs/evidencies/pas22");
await fs.mkdir(outputDir, { recursive: true });

async function saveScreenshot(page, targetPath) {
  const buffer = await page.screenshot();
  for (let attempt = 0; attempt < 5; attempt++) {
    try {
      try { await fs.unlink(targetPath); } catch {}
      await fs.writeFile(targetPath, buffer);
      console.log(`Captura desada: ${targetPath}`);
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
  args: ["--no-sandbox", "--disable-setuid-sandbox"],
});

const page = await browser.newPage();
await page.setViewport({ width: 1440, height: 900, deviceScaleFactor: 1 });

const browserErrors = [];
page.on("pageerror", err => browserErrors.push(String(err)));
page.on("console", msg => {
  if (msg.type() === "error") {
    browserErrors.push(msg.text());
  }
});

console.log("Navegant a la URL base...");
await page.goto(baseUrl, { waitUntil: "domcontentloaded", timeout: 45_000 });

// Esperar que la UI principal estigui llesta
await page.waitForSelector('button[title="Cel"]', { timeout: 30_000 });
await new Promise(resolve => setTimeout(resolve, 2_000));

// Esperar que el perfil DEM estigui completament carregat (fins a ~120s si cal)
console.log("Esperant que el perfil DEM estigui llest...");
let demReady = false;
for (let attempt = 0; attempt < 60; attempt++) {
  demReady = await page.evaluate(() => {
    return window.__isDemLoaded?.() === true;
  });
  if (demReady) {
    console.log(`Perfil DEM carregat correctament (comprovació ${attempt + 1}).`);
    break;
  }
  await new Promise(r => setTimeout(r, 2_000));
}
if (!demReady) {
  console.log("Marge addicional de càrrega...");
  await new Promise(r => setTimeout(r, 5_000));
}

// Configurar Bortle 1 i activar la Via Làctia
console.log("Configurant Bortle 1 i activant Via Làctia...");
await page.evaluate(async () => {
  window.__setBortle?.(1.0);
  await window.__setMilkyWayVisible?.(true);
});
await new Promise(resolve => setTimeout(resolve, 2_500));

// Assegurar que l'horitzó real està activat a Topografia
console.log("Comprovant horitzó real a Topografia...");
await page.click('button[title="Topografia"]');
await page.waitForSelector('#earth-horizon-enabled', { timeout: 10_000 });
const isHorizonChecked = await page.$eval('#earth-horizon-enabled', el => el.checked);
if (!isHorizonChecked) {
  console.log("Reactivant horitzó real a Topografia...");
  await page.click('#earth-horizon-enabled');
  await new Promise(r => setTimeout(r, 1_500));
}
await page.click('button[title="Topografia"]');
await new Promise(r => setTimeout(r, 600));

// Obrir el panell Cel
console.log("Obrint panell Cel...");
await page.click('button[title="Cel"]');
await page.waitForSelector('.trajectory-visibility-panel', { visible: true, timeout: 10_000 });

// Verificar que el checkbox 'Trajectòria de l'objecte' està marcat per defecte
const isCheckedByDefault = await page.$eval('#trajectory-object-toggle', el => el.checked);
console.log(`Checkbox 'Trajectòria de l'objecte' marcat per defecte: ${isCheckedByDefault}`);

// Cercar i seleccionar el Sol
console.log("Cercant i seleccionant el Sol...");
const searchInput = await page.waitForSelector('.search-widget input', { visible: true });
await searchInput.type("Sol");
await new Promise(resolve => setTimeout(resolve, 600));

await page.waitForSelector('.search-widget div[style*="cursor: pointer"]', { timeout: 10_000 });
await page.click('.search-widget div[style*="cursor: pointer"]');
await new Promise(resolve => setTimeout(resolve, 1_000));

// Esperar que el càlcul de trajectòria sobre el DEM hagi finalitzat
console.log("Esperant resultat del càlcul de trajectòria sobre DEM...");
await page.waitForFunction(() => {
  const statusEl = document.querySelector('.trajectory-visibility-panel [role="status"]');
  const text = statusEl?.textContent ?? "";
  return text.length > 0 && !text.includes("Selecciona") && !text.includes("Calculant");
}, { timeout: 30_000 });

const statusInitial = await page.$eval('.trajectory-visibility-panel [role="status"]', el => el.textContent);
console.log(`Estat de la trajectòria: ${statusInitial}`);

// Tancar calaix per gaudir de la visual neta
await page.click('button[title="Cel"]');
await new Promise(resolve => setTimeout(resolve, 600));

// ─── Captura 1: Puesta de Sol sobre muntanyes amb línia discontínua lila ───
console.log("Preparant captura de la posta de Sol...");
await page.evaluate(() => {
  window.__setHudVisible?.(false);
  // Posta a les ~20:00 CEST (18:00 UTC). Posem el temps a les 20:03 per veure el Sol sota la carena amb traça lila
  window.__setSimulationTime?.("2026-09-16T18:03:00Z");
  // Orientar la càmera cap al punt de posta centrat (Az 273.0°, Alt 2.0°, FOV 40°)
  window.__setCameraPose?.(273.0, 2.0, 40);
});
await new Promise(resolve => setTimeout(resolve, 2_500));

await saveScreenshot(page, path.join(outputDir, "puesta.png"));
await saveScreenshot(page, path.join(outputDir, "hidden-segments.png"));

// ─── Captura 2: Alba de Sol sobre el relleu oriental ───
console.log("Preparant captura de l'alba...");
await page.evaluate(() => {
  window.__setHudVisible?.(false);
  // Sortida a les 07:42:32 CEST (05:42:32 UTC) a Az 86.5°
  window.__setSimulationTime?.("2026-09-16T05:43:00Z");
  // Orientar la càmera cap a la sortida centrada (Az 86.5°, Alt 1.5°, FOV 38°)
  window.__setCameraPose?.(86.5, 1.5, 38);
});
await new Promise(resolve => setTimeout(resolve, 2_500));

await saveScreenshot(page, path.join(outputDir, "alba.png"));
await saveScreenshot(page, path.join(outputDir, "real-horizon.png"));

// ─── Captura 3: Trajectòria completa general amb zoom-out, objecte identificat i caiguda cap a l'horitzó ───
console.log("Preparant captura de la trajectòria completa general amb zoom out...");
await page.evaluate(() => {
  // Mostrem el HUD per identificar clarament l'objecte "Sol"
  window.__setHudVisible?.(true);
  // Moment de mitja tarda: 16:30 CEST (14:30 UTC), Sol a Alt ~37° Az ~233°
  window.__setSimulationTime?.("2026-09-16T14:30:00Z");
  // Gran angular (zoom-out FOV 95°) mirant cap a Az 255°, Alt 22° per contemplar tota la caiguda cap a la posta
  window.__setCameraPose?.(255.0, 22.0, 95);
  window.__requestTrajectory?.();
});
await new Promise(resolve => setTimeout(resolve, 4_000));

await saveScreenshot(page, path.join(outputDir, "trajectoria-completa.png"));

// ─── Captura 4: Detall de targeta d'esdeveniment amb zoom invariant ───
console.log("Preparant detall d'etiqueta d'esdeveniment invariant al zoom...");
await page.evaluate(() => {
  window.__setHudVisible?.(false);
  window.__setSimulationTime?.("2026-09-16T18:03:00Z");
  window.__setCameraPose?.(273.2, 1.5, 20);
});
await new Promise(resolve => setTimeout(resolve, 2_500));

await saveScreenshot(page, path.join(outputDir, "time-marker-and-labels.png"));

// ─── Captura 5: Comparació amb horitzó astronòmic pla a 0° ───
console.log("Preparant comparació amb horitzó astronòmic a Topografia...");
await page.click('button[title="Topografia"]');
await page.waitForSelector('#earth-horizon-enabled', { visible: true, timeout: 10_000 });
await page.click('#earth-horizon-enabled');
await new Promise(resolve => setTimeout(resolve, 1_500));
await page.click('button[title="Topografia"]');
await page.evaluate(() => {
  window.__setHudVisible?.(false);
  window.__setCameraPose?.(271.5, 2.8, 40);
});
await new Promise(resolve => setTimeout(resolve, 2_000));

await saveScreenshot(page, path.join(outputDir, "astronomical-horizon.png"));

// Reactivar l'horitzó real
await page.click('button[title="Topografia"]');
await page.waitForSelector('#earth-horizon-enabled', { visible: true, timeout: 10_000 });
await page.click('#earth-horizon-enabled');
await new Promise(resolve => setTimeout(resolve, 1_000));
await page.click('button[title="Topografia"]');

// Mètriques finals
const metrics = await page.evaluate(() => {
  const canvas = document.querySelector("canvas");
  return {
    canvasPresent: canvas !== null,
    canvasWidth: canvas?.width,
    canvasHeight: canvas?.height,
    panelStatus: document.querySelector('.trajectory-visibility-panel [role="status"]')?.textContent,
    checkboxChecked: (document.querySelector('#trajectory-object-toggle'))?.checked,
  };
});

console.log("Mètriques finals:", JSON.stringify({ metrics, browserErrors }, null, 2));

await browser.close();
console.log("Sessió Puppeteer finalitzada amb èxit.");
