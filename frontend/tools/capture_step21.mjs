import fs from "node:fs/promises";
import path from "node:path";
import puppeteer from "puppeteer";

const baseUrl = process.argv[2] ?? "http://127.0.0.1:14398/";
const outputDir = path.resolve("../docs/evidencies/pas21");
await fs.mkdir(outputDir, { recursive: true });

const browser = await puppeteer.launch({ headless: true });
const page = await browser.newPage();
await page.setViewport({ width: 1440, height: 900, deviceScaleFactor: 1 });
const errors = [];
page.on("pageerror", error => errors.push(String(error)));
page.on("console", message => { if (message.type() === "error") errors.push(message.text()); });
await page.goto(baseUrl, { waitUntil: "domcontentloaded", timeout: 30_000 });
await page.waitForSelector('button[title="Eines"]', { timeout: 30_000 });
await new Promise(resolve => setTimeout(resolve, 2_000));
await page.click('button[title="Eines"]');
await page.waitForSelector('[data-measurement-tool="ruler"]', { visible: true });
const recorder = await page.screencast({ path: path.join(outputDir, "measurement-cycle.webm"), scale: 0.75 });

const canvas = await page.$("canvas");
const bounds = await canvas.boundingBox();
if (!bounds) throw new Error("Canvas without bounds");
const gestures = [
  ["ruler", 0.22, 0.25, 0.38, 0.28],
  ["square", 0.64, 0.22, 0.70, 0.28],
  ["rectangle", 0.22, 0.62, 0.40, 0.70],
  ["circle", 0.66, 0.62, 0.73, 0.68],
];
const point = (x, y) => ({ x: bounds.x + bounds.width * x, y: bounds.y + bounds.height * y });
const cameraHudBefore = await page.$eval("#location-hud", node => node.textContent);
async function drag(x0, y0, x1, y1) {
  const start = point(x0, y0), end = point(x1, y1);
  await page.mouse.move(start.x, start.y);
  await page.mouse.down();
  await page.mouse.move(end.x, end.y, { steps: 10 });
  await page.mouse.up();
}
async function waitCount(count) {
  try {
    await page.waitForFunction(expected => document.querySelectorAll(".measurement-label").length === expected, { timeout: 10_000 }, count);
  } catch (error) {
    const actual = await page.evaluate(() => ({ count: document.querySelectorAll(".measurement-label").length, status: document.querySelector(".measurement-status")?.textContent }));
    throw new Error(`Expected ${count} labels, got ${actual.count}; status=${actual.status}; errors=${errors.join(" | ")}`, { cause: error });
  }
}

let count = 0;
for (const [kind, x0, y0, x1, y1] of gestures) {
  await page.click(`[data-measurement-tool="${kind}"]`);
  await drag(x0, y0, x1, y1);
  await waitCount(++count);
  await new Promise(resolve => setTimeout(resolve, 250));
}
await page.screenshot({ path: path.join(outputDir, "four-tools.png") });

// Resize the ruler through its end handle; the accepted backend label must change.
const rulerSelector = '.measurement-label[data-measurement-kind="ruler"]';
const rulerBefore = await page.$eval(rulerSelector, label => label.textContent ?? "");
await drag(0.38, 0.28, 0.46, 0.34);
await page.waitForFunction((selector, previous) => (document.querySelector(selector)?.textContent ?? "") !== previous, { timeout: 10_000 }, rulerSelector, rulerBefore);
const rulerAfter = await page.$eval(rulerSelector, label => label.textContent ?? "");

// Move the circle rigidly through its centre handle; its angular radius is preserved.
const circleSelector = '.measurement-label[data-measurement-kind="circle"]';
const circleBefore = await page.$eval(circleSelector, label => ({ text: label.textContent, x: label.getBoundingClientRect().x, y: label.getBoundingClientRect().y }));
await drag(0.66, 0.62, 0.59, 0.57);
await page.waitForFunction(() => !document.querySelector(".measurement-status")?.textContent?.includes("Aplicant"), { timeout: 10_000 });
const circleAfter = await page.$eval(circleSelector, label => ({ text: label.textContent, x: label.getBoundingClientRect().x, y: label.getBoundingClientRect().y }));

await page.click('[data-measurement-action="delete"]');
await waitCount(3);
await page.click('[data-measurement-action="undo"]');
await waitCount(4);
await page.screenshot({ path: path.join(outputDir, "edit-delete-undo.png") });
await new Promise(resolve => setTimeout(resolve, 500));

const labels = await page.$$eval(".measurement-label", nodes => nodes.map(node => node.textContent));
const status = await page.$eval(".measurement-status", node => node.textContent);
const cameraHudAfter = await page.$eval("#location-hud", node => node.textContent);
const toolAccessibility = await page.$$eval("[data-measurement-tool]", nodes => nodes.map(node => ({
  kind: node.getAttribute("data-measurement-tool"),
  title: node.getAttribute("title"),
  pressed: node.getAttribute("aria-pressed"),
})));
console.log(JSON.stringify({
  rulerBefore,
  rulerAfter,
  circleAngularLabelPreserved: circleBefore.text === circleAfter.text,
  circleMovedCssPx: Math.hypot(circleAfter.x - circleBefore.x, circleAfter.y - circleBefore.y),
  labels,
  status,
  cameraPosePreservedExactly: cameraHudBefore === cameraHudAfter,
  toolAccessibility,
  browserErrors: errors,
}, null, 2));
await recorder.stop();
await browser.close();
