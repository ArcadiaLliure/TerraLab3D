import fs from "node:fs/promises";
import path from "node:path";
import puppeteer from "puppeteer";

const baseUrl = process.argv[2] ?? "http://127.0.0.1:14398/";
const examplesDir = path.resolve(import.meta.dirname, "../../docs/examples/interficie");
const evidenciesDir = path.resolve(import.meta.dirname, "../../docs/evidencies/interficie");
await fs.mkdir(examplesDir, { recursive: true });
await fs.mkdir(evidenciesDir, { recursive: true });

console.log("Llançant Puppeteer...");
const browser = await puppeteer.launch({
  headless: true,
  args: ["--no-sandbox", "--disable-setuid-sandbox"],
});

// 1. Generar il·lustració d'estil docs/examples/pas22/ per al mapa de la interfície
const diagramPage = await browser.newPage();
await diagramPage.setViewport({ width: 1000, height: 580, deviceScaleFactor: 2 });

const htmlContent = `
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif; }
  body {
    background-color: #f1f5f9;
    display: flex;
    flex-direction: column;
    padding: 32px 40px;
    height: 100vh;
    color: #0f172a;
  }
  h1 {
    font-size: 24px;
    font-weight: 700;
    color: #0f172a;
    margin-bottom: 6px;
  }
  p.subtitle {
    font-size: 14px;
    color: #475569;
    margin-bottom: 24px;
  }
  .app-frame {
    background-color: #0f172a;
    border-radius: 12px;
    box-shadow: 0 10px 25px -5px rgba(15, 23, 42, 0.3);
    position: relative;
    flex: 1;
    display: flex;
    flex-direction: column;
    overflow: hidden;
    border: 1px solid #1e293b;
    padding: 16px;
  }
  .center-dome {
    position: absolute;
    top: 16px;
    left: 16px;
    right: 16px;
    bottom: 74px;
    background: radial-gradient(circle at 65% 35%, #1e293b 0%, #090d16 100%);
    border-radius: 8px;
    border: 1px dashed rgba(56, 189, 248, 0.4);
    display: flex;
    align-items: center;
    justify-content: center;
    flex-direction: column;
    z-index: 1;
  }
  .center-dome .title {
    color: #38bdf8;
    font-size: 20px;
    font-weight: 700;
    letter-spacing: 0.05em;
    margin-bottom: 4px;
  }
  .center-dome .desc {
    color: #94a3b8;
    font-size: 13px;
  }
  .drawer-panel {
    position: absolute;
    top: 28px;
    left: 28px;
    width: 220px;
    background: rgba(15, 23, 42, 0.88);
    backdrop-filter: blur(12px);
    border: 1px solid rgba(148, 163, 184, 0.2);
    border-radius: 8px;
    padding: 12px;
    z-index: 10;
    box-shadow: 0 4px 16px rgba(0, 0, 0, 0.5);
  }
  .drawer-panel .tab-item {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 6px 10px;
    border-radius: 6px;
    font-size: 13px;
    font-weight: 600;
    color: #e2e8f0;
    margin-bottom: 4px;
    background: rgba(255, 255, 255, 0.04);
  }
  .drawer-panel .tab-item.active {
    background: rgba(56, 189, 248, 0.15);
    border-left: 3px solid #38bdf8;
    color: #38bdf8;
  }
  .hud-panel {
    position: absolute;
    bottom: 84px;
    left: 28px;
    width: 290px;
    background: rgba(15, 23, 42, 0.92);
    backdrop-filter: blur(12px);
    border: 1px solid rgba(234, 179, 8, 0.3);
    border-radius: 8px;
    padding: 12px;
    z-index: 10;
    box-shadow: 0 4px 16px rgba(0, 0, 0, 0.5);
  }
  .hud-panel .badge {
    display: inline-block;
    padding: 2px 6px;
    background: rgba(234, 179, 8, 0.2);
    color: #fbbf24;
    border: 1px solid #fbbf24;
    border-radius: 4px;
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 0.05em;
    margin-bottom: 6px;
  }
  .hud-panel .target-name {
    font-size: 15px;
    font-weight: 700;
    color: #f8fafc;
    margin-bottom: 4px;
  }
  .hud-panel .target-coords {
    font-size: 12px;
    color: #94a3b8;
    margin-bottom: 8px;
  }
  .hud-panel .actions {
    display: flex;
    gap: 6px;
  }
  .hud-panel .actions button {
    flex: 1;
    padding: 4px 8px;
    border-radius: 4px;
    border: none;
    font-size: 11px;
    font-weight: 600;
    cursor: pointer;
  }
  .hud-panel .actions .btn-follow {
    background: #eab308;
    color: #0f172a;
  }
  .hud-panel .actions .btn-center {
    background: rgba(255, 255, 255, 0.1);
    color: #f8fafc;
  }
  .timeline-bar {
    position: absolute;
    bottom: 16px;
    left: 16px;
    right: 16px;
    height: 50px;
    background: rgba(15, 23, 42, 0.95);
    border: 1px solid rgba(148, 163, 184, 0.2);
    border-radius: 8px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 0 16px;
    z-index: 10;
  }
  .timeline-bar .time-display {
    font-size: 14px;
    font-weight: 700;
    color: #f8fafc;
    font-variant-numeric: tabular-nums;
  }
  .timeline-bar .slider-track {
    flex: 1;
    margin: 0 20px;
    height: 6px;
    background: #334155;
    border-radius: 3px;
    position: relative;
  }
  .timeline-bar .slider-thumb {
    position: absolute;
    top: -5px;
    left: 45%;
    width: 16px;
    height: 16px;
    background: #38bdf8;
    border: 2px solid #ffffff;
    border-radius: 50%;
  }
  .top-right-tools {
    position: absolute;
    top: 28px;
    right: 28px;
    display: flex;
    gap: 8px;
    z-index: 10;
  }
  .tool-btn {
    width: 32px;
    height: 32px;
    background: rgba(15, 23, 42, 0.85);
    border: 1px solid rgba(148, 163, 184, 0.2);
    border-radius: 6px;
    color: #e2e8f0;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 14px;
  }
  .footer-legend {
    margin-top: 12px;
    display: flex;
    justify-content: space-between;
    font-size: 12px;
    color: #64748b;
  }
</style>
</head>
<body>
  <h1>Organització de la interfície de TerraLab3D</h1>
  <p class="subtitle">Disposició dels elements clau per a una observació astronòmica i topogràfica fluida.</p>
  
  <div class="app-frame">
    <!-- Cúpula central -->
    <div class="center-dome">
      <div class="title">CÚPULA CELESTE 3D · 360°</div>
      <div class="desc">Volta celeste astronòmica + Relleu DEM tridimensional</div>
    </div>

    <!-- Calaix lateral -->
    <div class="drawer-panel">
      <div class="tab-item active">📍 Ubicació & Temps</div>
      <div class="tab-item">🌌 Cel & Sistema Solar</div>
      <div class="tab-item">⛰️ Terra & Horitzó DEM</div>
      <div class="tab-item">📐 Eines & Òptica</div>
    </div>

    <!-- Eines superior dreta -->
    <div class="top-right-tools">
      <div class="tool-btn">⛶</div>
      <div class="tool-btn">⚙</div>
    </div>

    <!-- HUD inferior esquerre -->
    <div class="hud-panel">
      <span class="badge">SEGUINT ✓</span>
      <div class="target-name">Sol (Sun)</div>
      <div class="target-coords">Az: 268.4° · Alt: +14.2° · Mag: -26.7</div>
      <div class="actions">
        <button class="btn-center">Centrar</button>
        <button class="btn-follow">Seguint ✓</button>
      </div>
    </div>

    <!-- Línia temporal inferior -->
    <div class="timeline-bar">
      <div class="time-display">2026-09-17 18:30:00 UTC · LST 14h 22m</div>
      <div class="slider-track">
        <div class="slider-thumb"></div>
      </div>
      <div class="time-display">Velocitat: 1× (Temps real)</div>
    </div>
  </div>

  <div class="footer-legend">
    <span>TerraLab3D · Laboratori 3D interactiu</span>
    <span>Interfície d'usuari reactiva amb Three.js i càlcul científic</span>
  </div>
</body>
</html>
`;

await diagramPage.setContent(htmlContent);
const diagramBuffer = await diagramPage.screenshot();
await fs.writeFile(path.join(examplesDir, "mapa-interficie.png"), diagramBuffer);
console.log(`Diagrama desat a ${path.join(examplesDir, "mapa-interficie.png")}`);
await diagramPage.close();

// 2. Captura real de l'aplicació en marxa
const appPage = await browser.newPage();
await appPage.setViewport({ width: 1440, height: 900, deviceScaleFactor: 1 });

try {
  console.log(`Navegant cap a ${baseUrl}...`);
  await appPage.goto(baseUrl, { waitUntil: "domcontentloaded", timeout: 20_000 });
  await new Promise(resolve => setTimeout(resolve, 3_000));

  // Esperar el DEM
  console.log("Esperant inicialització de l'escena...");
  for (let i = 0; i < 30; i++) {
    const ready = await appPage.evaluate(() => window.__isDemLoaded?.() === true);
    if (ready) break;
    await new Promise(r => setTimeout(r, 1_000));
  }

  // Configurar Bortle 1 i Via Làctia
  await appPage.evaluate(async () => {
    window.__setBortle?.(1.0);
    await window.__setMilkyWayVisible?.(true);
  });
  await new Promise(r => setTimeout(r, 1_500));

  // Captura 1: Vista general neta
  const generalPath = path.join(evidenciesDir, "interficie-general.png");
  await appPage.screenshot({ path: generalPath });
  console.log(`Captura general real desada: ${generalPath}`);

  // Captura 2: Amb el panell Cel obert i astre seleccionat
  await appPage.click('button[title="Cel"]');
  await new Promise(r => setTimeout(r, 800));
  const searchInput = await appPage.$('.search-widget input');
  if (searchInput) {
    await searchInput.type("Sol");
    await new Promise(r => setTimeout(r, 600));
    const firstResult = await appPage.$('.search-results-list .search-result-item');
    if (firstResult) await firstResult.click();
  }
  await new Promise(r => setTimeout(r, 1_000));

  const panelPath = path.join(evidenciesDir, "calaix-pestanyes.png");
  await appPage.screenshot({ path: panelPath });
  console.log(`Captura amb calaix obert desada: ${panelPath}`);

} catch (err) {
  console.warn("No s'ha pogut capturar la instància en viu:", err.message);
}

await browser.close();
console.log("Completat!");
