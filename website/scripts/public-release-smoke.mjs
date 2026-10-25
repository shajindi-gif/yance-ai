import {chromium,expect} from '@playwright/test';
import {mkdir,writeFile} from 'node:fs/promises';
const base=process.env.YANCE_SMOKE_BASE;
const output=process.env.YANCE_SMOKE_OUT;
if(!base||!output)throw new Error('Explicit target and output required');
const origin=new URL(base).origin;
if(!['https://yance.ai','http://127.0.0.1:3019'].includes(origin))throw new Error('Unapproved release-check target');
await mkdir(output,{recursive:true});
const browser=await chromium.launch();
const context=await browser.newContext({viewport:{width:1440,height:1000}});
const blockedMethods=[],failures=[],errors=[],checks=[];
await context.route('**/*',route => {
 const request=route.request();
 if(!['GET','HEAD','OPTIONS'].includes(request.method())){blockedMethods.push(request.method());return route.abort();}
 if(new URL(request.url()).origin!==origin)return route.abort();
 return route.continue();
});
const page=await context.newPage();
page.on('pageerror',error=>errors.push(error.message));
page.on('response',response=>{if(response.status()>=400)failures.push({path:new URL(response.url()).pathname,status:response.status()});});
try{
 const release=await context.request.get(`${base}/release.json`);
 expect(release.status()).toBe(200);
 expect((await release.json()).release).toBe('web-20261025-01');
 for(const path of ['/','/company-match','/brief-maker','/pricing','/login','/security','/policy-knowledge-base','/parks','/about']){
  const start=Date.now();const response=await page.goto(base+path,{timeout:60000});expect(response.status()).toBe(200);
  await expect(page.locator('h1').first()).toBeVisible();
  if(path==='/pricing')await expect(page.locator('.pricing-card').first()).toBeVisible({timeout:20000});
  if(path==='/'){const shot=page.locator('img[alt^="隔离合成项目"]');await shot.scrollIntoViewIfNeeded();await expect.poll(()=>shot.evaluate(img=>img.naturalWidth),{timeout:15000}).toBeGreaterThan(0);await page.evaluate(()=>scrollTo(0,0));await page.screenshot({path:`${output}/home-desktop.png`});}
  checks.push({path,visible_ms:Date.now()-start});
 }
 await page.setViewportSize({width:390,height:844});await page.goto(base+'/');
 await page.getByRole('button',{name:'打开菜单',exact:true}).click();await expect(page.getByRole('navigation',{name:'移动端导航'})).toBeVisible();
 await page.keyboard.press('Escape');await expect(page.getByRole('navigation',{name:'移动端导航'})).toBeHidden();
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
 await page.screenshot({path:`${output}/home-mobile.png`});
 const config=await context.request.get(base+'/api/v1/auth/config');expect(config.status()).toBe(200);
 const me=await context.request.get(base+'/api/v1/auth/me');expect(me.status()).toBe(401);
 expect(failures).toEqual([]);expect(errors).toEqual([]);
 const result={at:new Date().toISOString(),base,release:'web-20261025-01',checks,mobile:true,failures,errors,blockedMethods,productionBusinessWrites:false,backendWorkspaceRevision:(await config.json()).application_workspace_revision??null,sample:'one Chromium visit per public page; no throttling; not SLA'};
 await writeFile(`${output}/result.json`,JSON.stringify(result,null,2));console.log(JSON.stringify(result));
}finally{await browser.close();}
