const jsdom = require("jsdom");
const { JSDOM } = jsdom;
const fs = require("fs");

const bundleCode = fs.readFileSync("dist/bundle.js", "utf8");

const virtualConsole = new jsdom.VirtualConsole();
virtualConsole.on("error", () => { /* No-op */ });
virtualConsole.on("warn", () => { /* No-op */ });
virtualConsole.on("info", () => { /* No-op */ });
virtualConsole.on("dir", () => { /* No-op */ });
const dom = new JSDOM(`<!DOCTYPE html>
<html>
<body>
  <div id="sky"></div>
  <div id="uiOverlay"></div>
  <div id="diagnostics"></div>
  <div id="timeBarContainer"></div>
  <div id="locationHUD"></div>
</body>
</html>`, {
  runScripts: "dangerously",
  virtualConsole
});

try {
  dom.window.eval(bundleCode);
  console.log("App loaded successfully without immediate crash!");
} catch (e) {
  console.error("APP CRASHED!");
  console.error(e);
}
