import {chromium,expect} from '@playwright/test';
import {mkdir,writeFile} from 'node:fs/promises';
const base=process.env.YANCE_SMOKE_BASE;
const output=process.env.YANCE_SMOKE_OUT;
const expectedRelease=process.env.YANCE_SMOKE_RELEASE;
if(!['web-20261026-01','full-20261028-01'].includes(expectedRelease))throw new Error('Explicit approved release required');
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
page.on('response',response=>{const path=new URL(response.url()).pathname;if(response.status()>=400&&!(path==='/api/v1/auth/me'&&response.status()===401))failures.push({path,status:response.status()});});
async function readPublicJSON(path){return page.evaluate(async path=>{const response=await fetch(path,{cache:'no-store',credentials:'omit',signal:AbortSignal.timeout(15000)});return {status:response.status,data:await response.json()};},path);}
try{
 await page.goto(base+'/',{timeout:60000});
 const release=await readPublicJSON('/release.json');
 expect(release.status).toBe(200);
 expect(release.data.release).toBe(expectedRelease);
 for(const path of ['/','/company-match','/brief-maker','/pricing','/feedback','/login','/security','/policy-knowledge-base','/parks','/about']){
  const start=Date.now();const response=await page.goto(base+path,{timeout:60000});expect(response.status()).toBe(200);
  await expect(page.locator('h1').first()).toBeVisible();
  if(path==='/feedback'){await expect(page.getByRole('heading',{name:'分享使用反馈'})).toBeVisible();await expect(page.getByRole('button',{name:'提交反馈'})).toBeDisabled();}
  if(path==='/pricing')await expect(page.locator('.pricing-card').first()).toBeVisible({timeout:20000});
  if(path==='/'){await expect(page.locator('#for-business')).toContainText('各类有政策需求的企业');await expect(page.locator('#scenarios')).toContainText('不是真实客户案例');await expect(page.locator('#customer-feedback')).toContainText('暂未展示获授权');const shot=page.locator('img[alt^="隔离合成项目"]');await shot.scrollIntoViewIfNeeded();await expect.poll(()=>shot.evaluate(img=>img.naturalWidth),{timeout:15000}).toBeGreaterThan(0);await page.evaluate(()=>scrollTo(0,0));await page.screenshot({path:`${output}/home-desktop.png`});}
  checks.push({path,visible_ms:Date.now()-start});
 }
 await page.setViewportSize({width:390,height:844});await page.goto(base+'/');
 await page.getByRole('button',{name:'打开菜单',exact:true}).click();await expect(page.getByRole('navigation',{name:'移动端导航'})).toBeVisible();
 await page.keyboard.press('Escape');await expect(page.getByRole('navigation',{name:'移动端导航'})).toBeHidden();
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
 await page.screenshot({path:`${output}/home-mobile.png`});
 const config=await readPublicJSON('/api/v1/auth/config');expect(config.status).toBe(200);
 const me=await readPublicJSON('/api/v1/auth/me');expect(me.status).toBe(401);
 expect(failures).toEqual([]);expect(errors).toEqual([]);
 const result={at:new Date().toISOString(),base,release:expectedRelease,checks,mobile:true,failures,errors,blockedMethods,productionBusinessWrites:false,backendWorkspaceRevision:config.data.application_workspace_revision??null,sample:'Chromium read-only page visits and browser fetch; no throttling; not SLA'};
 await writeFile(`${output}/result.json`,JSON.stringify(result,null,2));console.log(JSON.stringify(result));
}catch(error){await writeFile(`${output}/failure.json`,JSON.stringify({at:new Date().toISOString(),base,checks,failures,errors,blockedMethods,error:String(error),productionBusinessWrites:false},null,2));throw error;}finally{await browser.close();}
