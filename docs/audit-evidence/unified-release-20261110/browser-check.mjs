import {chromium,expect} from '../../../website/node_modules/@playwright/test/index.mjs';
import {writeFile} from 'node:fs/promises';
const base=process.env.CHECK_BASE || 'http://127.0.0.1:3028';
const prefix=process.env.CHECK_PREFIX || 'candidate';
const out=new URL('./',import.meta.url).pathname;
const browser=await chromium.launch({headless:true});
const results=[];
const pageErrors=[];
try{
 const page=await browser.newPage();
 page.on('pageerror',error=>pageErrors.push(error.message));
 await page.route('**/*',route=>['GET','HEAD'].includes(route.request().method()) && new URL(route.request().url()).origin===base ? route.continue():route.abort());
 for(const width of [390,768,1440]){
  await page.setViewportSize({width,height:900});
  for(const path of ['/','/intelligence','/login','/pricing','/orders']){
   const response=await page.goto(base+path);
   expect(response.status()).toBe(200);
   await expect(page.locator('h1').first()).toBeVisible();
   expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
   await page.screenshot({path:`${out}${prefix}-${path==='/'?'home':path.slice(1)}-${width}.png`,fullPage:true});
   results.push({width,path,status:response.status(),overflow:false});
  }
 }
 await page.goto(base+'/intelligence');
 await page.getByLabel('采购文件原文').fill('验收后结算，须提供资质证明。');
 await expect(page.locator('dd').filter({hasText:'须提供资质'}).first()).toBeVisible();
 expect(pageErrors).toEqual([]);
 const release=await (await page.request.get(base+'/release.json')).json();
 expect(release.website_source).toBe('5c41702');
 await writeFile(`${out}${prefix}-results.json`,JSON.stringify({release,results,localTextTool:true,requests:'GET/HEAD only'},null,2));
 console.log(`${prefix}: ${results.length} responsive pages and text tool passed`);
}finally{await browser.close();}
