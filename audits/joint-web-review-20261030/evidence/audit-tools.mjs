import {createRequire} from 'node:module';import fs from 'node:fs';
const require=createRequire('/private/tmp/yance-joint-20261030/tools/package.json');
const {chromium,firefox,webkit}=require('/Users/shajindi/yance-backup/yance/website/node_modules/@playwright/test');
const AxeBuilder=require('@axe-core/playwright').default;
const out='/Users/shajindi/yance-backup/yance/audits/joint-web-review-20261030/evidence';
const browser=await chromium.launch();const results=[];
for (const width of [1440,768,390]) {
 const context=await browser.newContext({viewport:{width,height:900}});await context.route('**/*',r=>new URL(r.request().url()).origin==='https://yance.ai'&&['GET','HEAD','OPTIONS'].includes(r.request().method())?r.continue():r.abort());
 const page=await context.newPage();
 for(const path of (width===1440?['/','/pricing','/login','/about','/privacy']:['/','/login'])){
 await page.goto('https://yance.ai'+path,{waitUntil:'networkidle'});const axe=await new AxeBuilder({page}).withTags(['wcag2a','wcag2aa','wcag21a','wcag21aa','wcag22aa']).analyze();
 results.push({width,path,violations:axe.violations.map(v=>({id:v.id,impact:v.impact,description:v.description,helpUrl:v.helpUrl,nodes:v.nodes.map(n=>({target:n.target,summary:n.failureSummary}))})),incomplete:axe.incomplete.map(v=>({id:v.id,impact:v.impact,count:v.nodes.length})),overflow:await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth)});
 if(path==='/')await page.screenshot({path:`${out}/home-${width}.png`});
 }await context.close();
}await browser.close();fs.writeFileSync(`${out}/axe.json`,JSON.stringify(results,null,2));
const compatibility=[];for(const [name,b] of [['firefox',firefox],['webkit',webkit]]){try{const br=await b.launch();const p=await br.newPage();await p.goto('http://127.0.0.1:3038/login');compatibility.push({name,status:await p.locator('h1').innerText(),scope:'isolated page only; not native Safari/Edge'});await br.close();}catch{compatibility.push({name,status:'not executed: browser runtime unavailable'})}}fs.writeFileSync(`${out}/compatibility.json`,JSON.stringify(compatibility,null,2));
const lh=(await import(require.resolve('lighthouse'))).default;const launcher=await import(require.resolve('chrome-launcher'));
const chrome=await launcher.launch({chromePath:chromium.executablePath(),chromeFlags:['--headless','--no-sandbox']});try{const run=await lh('http://127.0.0.1:3038/',{port:chrome.port,output:'json',onlyCategories:['performance','accessibility','best-practices','seo'],blockedUrlPatterns:['https://*'],maxWaitForLoad:30000});fs.writeFileSync(`${out}/lighthouse.json`,run.report);console.log(JSON.stringify(Object.fromEntries(Object.entries(run.lhr.categories).map(([k,v])=>[k,v.score]))));}finally{await chrome.kill()}
