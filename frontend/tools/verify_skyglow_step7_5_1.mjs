import fs from 'node:fs/promises';
import path from 'node:path';
import assert from 'node:assert/strict';
import puppeteer from 'puppeteer';

const output = path.resolve(import.meta.dirname, '../../docs/evidencies/pas7.5.1');
await fs.mkdir(output, {recursive:true});
const browser = await puppeteer.launch({headless:true, args:['--no-sandbox','--enable-webgl','--use-gl=angle']});
try {
 const page = await browser.newPage();
 await page.setViewport({width:1280,height:1000,hasTouch:true});
 const cdp = await page.createCDPSession();
 await cdp.send('Network.enable');
 const snapshots=[];
 cdp.on('Network.webSocketFrameReceived', ({response}) => {
  try { const value=JSON.parse(response.payloadData); if(value.type==='skyglow_configuration_snapshot') snapshots.push(value); } catch {}
 });
 await page.goto(process.argv[2] ?? 'http://127.0.0.1:14398/', {waitUntil:'domcontentloaded'});
 await page.waitForSelector('button[title="Cel"]');
 await page.click('button[title="Cel"]');
 const mode='select[aria-label="Modalitat de simulació de contaminació lumínica"]';
 await page.waitForSelector(mode);
 async function waitForConfiguration(predicate) {
  const start=Date.now();
  while(Date.now()-start<15000) {
   const value=snapshots.at(-1);
   if(value && predicate(value)) return value;
   await new Promise(resolve=>setTimeout(resolve,100));
  }
  throw new Error('No ha arribat la configuració autoritativa esperada');
 }
 await waitForConfiguration(()=>true);
 await page.select(mode,'realistic');
 await waitForConfiguration(s=>s.configuration.mode==='realistic');
 await page.select(mode,'kelvin');
 await waitForConfiguration(s=>s.configuration.mode==='kelvin' && s.effectiveSpectrum);
 const slider=await page.$('#skyglow-kelvin');
 await slider.scrollIntoView();
 await slider.focus();
 await page.keyboard.press('End');
 const cold=await waitForConfiguration(s=>s.configuration.kelvin===6500 && s.effectiveSpectrum);
 assert.ok(Math.abs(cold.effectiveSpectrum.effectiveCctK-6500)<.1);
 await page.keyboard.press('Home');
 await page.keyboard.press('ArrowRight');
 const warm=await waitForConfiguration(s=>s.configuration.kelvin===2850 && s.effectiveSpectrum);
 assert.notEqual(cold.configurationKey,warm.configurationKey);
 assert.equal(cold.configuration.spectral_family,warm.configuration.spectral_family);
 const box=await slider.boundingBox();
 await page.mouse.click(box.x+box.width*.55,box.y+box.height/2);
 const mouse=await waitForConfiguration(s=>s.configuration.kelvin>4000 && s.configuration.kelvin<5200 && s.effectiveSpectrum);
 await page.touchscreen.tap(box.x+box.width*.35,box.y+box.height/2);
 const touch=await waitForConfiguration(s=>s.configuration.kelvin>3400 && s.configuration.kelvin<4400 && s.effectiveSpectrum);
 assert.notEqual(mouse.configurationKey,touch.configurationKey);
 await page.select('select[aria-label="Magnitud conservada en canviar la temperatura"]','constant_dnb_reference');
 const normalized=await waitForConfiguration(s=>s.configuration.normalization==='constant_dnb_reference' && s.effectiveSpectrum);
 assert.equal(normalized.skyRadiance,null);
 assert.equal(normalized.calculationStatus,'transport_pending');
 const startingGeneration=normalized.generation;
 await slider.focus();
 await page.keyboard.press('End');
 await page.keyboard.press('Home');
 await page.keyboard.press('End');
 const latest=await waitForConfiguration(s=>s.generation>=startingGeneration+3 && s.configuration.kelvin===6500 && s.effectiveSpectrum);
 assert.equal(await page.$eval('#skyglow-kelvin',e=>e.value),'6500');
 assert.ok(latest.generation>normalized.generation);

 const layout=await page.evaluate(()=>{
  const slider=document.querySelector('#skyglow-kelvin');
  const group=slider.parentElement;
  return {min:slider.min,max:slider.max,aria:slider.getAttribute('aria-valuetext'),text:group.textContent, scale:[...slider.nextElementSibling.children].map(e=>({text:e.textContent,x:e.getBoundingClientRect().x})), label:document.querySelector('label[for="skyglow-kelvin"]').textContent};
 });
 assert.equal(layout.min,'2800'); assert.equal(layout.max,'6500');
 assert.ok(layout.label.includes('Temperatura de color'));
 assert.equal(layout.scale[0].text,'2.800 K'); assert.equal(layout.scale[1].text,'6.500 K');
 assert.ok(layout.scale[0].x<layout.scale[1].x);
 assert.ok(layout.text.includes('Exemple:'));
 assert.ok(layout.aria.endsWith(' K'));
 await slider.scrollIntoView();
 await page.$eval('#skyglow-kelvin', e=>e.parentElement.parentElement.scrollIntoView({block:'center'}));
 await page.screenshot({path:path.join(output,'control-kelvins.png')});
 await page.select(mode,'realistic');
 await waitForConfiguration(s=>s.configuration.mode==='realistic');
 assert.equal(await page.$eval('#skyglow-kelvin',e=>e.parentElement.hidden),true);
 await page.$eval(mode, e=>e.parentElement.parentElement.scrollIntoView({block:'center'}));
 await page.screenshot({path:path.join(output,'simulacio-realista.png')});
 await fs.writeFile(path.join(output,'verificacio-ui.json'),JSON.stringify({resultat:'PASS',keyboard:true,mouse:true,touch:true,latestWins:true,layout,configuration:latest,renderResult:null},null,2)+'\n');
 console.log('PASS: controls, teclat, ratolí, tacte, bridge real, CCT efectiva i cap radiància fictícia.');
} finally {await browser.close();}
