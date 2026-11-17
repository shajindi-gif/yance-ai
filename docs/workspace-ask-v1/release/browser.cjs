const fs = require('node:fs');
const path = require('node:path');
const {chromium} = require(process.env.YANCE_PLAYWRIGHT_MODULE || '../../../../website/node_modules/playwright');
(async()=>{
 const base=process.env.YANCE_PREVIEW_URL;
 if(!['http://127.0.0.1:3039','https://yance.ai'].includes(base))throw Error('Unexpected verification target');
 const output=process.env.YANCE_BROWSER_OUTPUT;
 fs.mkdirSync(output,{recursive:true});
 const browser=await chromium.launch({timeout: 30000, ...(process.env.YANCE_BROWSER_EXECUTABLE ? {executablePath:process.env.YANCE_BROWSER_EXECUTABLE} : {channel:"chrome"})});const results=[];console.log("browser",browser.version());
 for(const width of [390,1440]){
  const context=await browser.newContext({viewport:{width,height:900},reducedMotion:'reduce'});
  await context.route('**/*',route=>{
   const r=route.request(),u=new URL(r.url());
   const allowed=['127.0.0.1','yance.ai','api.yance.ai'].includes(u.hostname);
   return allowed&&['GET','HEAD'].includes(r.method())?route.continue():route.abort();
  });
  const page=await context.newPage();const errors=[];page.on('pageerror',e=>errors.push(e.message));
  for(const route of ['/','/pricing','/login','/discover','/checkout','/success','/parks']){
   const response=await page.goto(base+route,{waitUntil:'domcontentloaded',timeout:90000});
   if(response.status()!==200)throw Error(route+' status '+response.status());
   await page.locator('main h1').first().waitFor();
   if(!await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth))throw Error(route+' overflow '+width);
   if(route==='/parks' && (await page.getByText('让你的园区服务更智能',{exact:true}).count() || await page.getByText('注册后可创建企业工作区；可用额度与付费能力以账户中的真实配置为准。',{exact:true}).count())) throw Error('Legacy park promotion remains');
   const file=`${base.startsWith('https')?'production':'candidate'}-${width}-${route==='/'?'home':route.slice(1)}.png`;
   await page.screenshot({path:path.join(output,file),fullPage:true});
   console.log("checked",width,route);
   results.push({width,route,status:response.status(),overflow:false,screenshot:file});
  }
  if(errors.length)throw Error(JSON.stringify(errors));
  await context.close();
 }
 const context=await browser.newContext({javaScriptEnabled:false});
 await context.route('**/*',r=>['GET','HEAD'].includes(r.request().method())&&['127.0.0.1','yance.ai','api.yance.ai'].includes(new URL(r.request().url()).hostname)?r.continue():r.abort());
 const page=await context.newPage();await page.goto(base+'/pricing');
 if(await page.locator('.pricing-price').filter({hasText:'¥99'}).count()!==1)throw Error('SSR catalogue missing');
 const headers=(await page.request.get(base+'/login')).headers();
 if(!headers['strict-transport-security']?.includes('max-age=63072000'))throw Error('HSTS missing');
 const release=await (await page.request.get(base+'/release.json?verification='+Date.now())).json();
 if(release.website_source!=='0746e06c9bc4e570577e0350129b038002a80eae')throw Error('Unexpected website source');
 let apiRuntime=null;
 if(true){
  apiRuntime=await (await page.request.get(base+'/api/runtime-version?verification='+Date.now())).json();
  if(apiRuntime.source_revision!==(release.api_patch_source||release.website_source)||JSON.stringify(apiRuntime.database_revisions)!=='["20261117_0043"]')throw Error('Runtime identity mismatch');
 }
 await context.close();await browser.close();
 const releaseEvidence={...release,backend_commit:release.api_source||release.api_patch_source};
 delete releaseEvidence.api_patch_source; delete releaseEvidence.api_source;
 fs.writeFileSync(path.join(output,'browser-'+(base.startsWith('https')?'production':'candidate')+'.json'),JSON.stringify({base,mode:'GET/HEAD only; no authentication or real purchase',release:releaseEvidence,apiRuntime,results,ssrPrice:true,hsts:true,pageErrors:[]},null,2));
 console.log('PUBLIC_READ_ONLY_BROWSER_PASSED',results.length,'pages/viewports; SSR price; HSTS');
})().catch(e=>{console.error(e);process.exit(1)});
