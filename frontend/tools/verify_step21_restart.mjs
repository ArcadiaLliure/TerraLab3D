import puppeteer from "puppeteer";

const baseUrl = process.argv[2] ?? "http://127.0.0.1:14398/";
const browser = await puppeteer.launch({ headless: true });
const page = await browser.newPage();
await page.setViewport({ width: 1440, height: 900, deviceScaleFactor: 1 });
const errors = [];
page.on("pageerror", error => errors.push(String(error)));
page.on("console", message => { if (message.type() === "error") errors.push(message.text()); });
await page.goto(baseUrl, { waitUntil: "domcontentloaded", timeout: 30_000 });
await page.waitForFunction(() => document.querySelectorAll(".measurement-label").length === 4, { timeout: 30_000 });
await page.click('button[title="Eines"]');
const result = await page.evaluate(() => ({
  count: document.querySelectorAll(".measurement-label").length,
  labels: [...document.querySelectorAll(".measurement-label")].map(node => ({
    text: node.textContent,
    hidden: node.hidden,
    style: node.getAttribute("style"),
    bounds: node.getBoundingClientRect().toJSON(),
  })),
  status: document.querySelector(".measurement-status")?.textContent,
}));
console.log(JSON.stringify({ ...result, browserErrors: errors }, null, 2));
await browser.close();
