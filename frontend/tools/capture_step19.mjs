import fs from "node:fs/promises";
import path from "node:path";
import puppeteer from "puppeteer";

const baseUrl = process.argv[2] ?? "http://127.0.0.1:14398/";
const outputDir = path.resolve("../docs/evidencies/pas19");
await fs.mkdir(outputDir, { recursive: true });

const browser = await puppeteer.launch({ headless: true });
const page = await browser.newPage();
await page.setViewport({ width: 1440, height: 900, deviceScaleFactor: 1 });
const errors = [];
page.on("pageerror", error => errors.push(String(error)));
page.on("console", message => {
  if (message.type() === "error") {
    const location = message.location();
    errors.push(`${message.text()} (${location.url || "unknown"})`);
  }
});

await page.goto(baseUrl, { waitUntil: "domcontentloaded", timeout: 30_000 });
await page.waitForSelector(".observation-mode-toggle", { timeout: 30_000 });
await new Promise(resolve => setTimeout(resolve, 3_000));

async function capture(mode) {
  await page.waitForFunction(expected => {
    const button = document.querySelector(".observation-mode-toggle");
    return button?.getAttribute("data-mode") === expected;
  }, { timeout: 10_000 }, mode);
  await page.screenshot({ path: path.join(outputDir, `${mode}.png`) });
}

async function nextMode() {
  await page.$eval(".observation-mode-toggle", button => button.click());
}

await capture("eye");
await nextMode();
await capture("camera");
const cameraHud = await page.$eval(".observation-hud", element => element.textContent);
await nextMode();
await capture("telescope");
const telescopeHud = await page.$eval(".observation-hud", element => element.textContent);
await nextMode();
await capture("eye");

const accessibility = await page.$eval(".observation-mode-toggle", element => {
  const bounds = element.getBoundingClientRect();
  return {
    ariaLabel: element.getAttribute("aria-label"),
    title: element.getAttribute("title"),
    width: bounds.width,
    height: bounds.height,
  };
});
const frameDurations = await page.evaluate(async () => {
  const samples = [];
  let previous = performance.now();
  for (let index = 0; index < 120; index++) {
    await new Promise(requestAnimationFrame);
    const current = performance.now();
    samples.push(current - previous);
    previous = current;
  }
  return samples.sort((a, b) => a - b);
});
const percentile = fraction => frameDurations[Math.floor((frameDurations.length - 1) * fraction)];
console.log(JSON.stringify({
  cameraHud,
  telescopeHud,
  accessibility,
  frameMsP50: percentile(0.50),
  frameMsP95: percentile(0.95),
  browserErrors: errors,
}, null, 2));

await browser.close();
