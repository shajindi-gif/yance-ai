const {createRequire}=require('module');const fs=require('fs');
const req=createRequire('/Users/shajindi/yance-backup/yance/website/package.json');
const {chromium}=req('playwright');
(async()=>{
 const out='/Users/shajindi/yance-backup/yance/docs/audit-evidence/commercial-release-20261108/';
 const token=JSON.parse(fs.readFileSync('/private/tmp/yance-release-1108/candidate-fixture.json')).token;
 const browser=await chromium.launch();const samples=[];
 for(const width of [1440,390]){
  const context=await browser.newContext({viewport:{width,height:900}});
  await context.route('**/*',async route=>{
   const u=new URL(route.request().url());
   if(!['127.0.0.1','localhost'].includes(u.hostname))return route.abort();
   if(u.pathname.startsWith('/api/v1/')){
    const result=await route.fetch({url:'http://127.0.0.1:18088'+u.pathname+u.search});
    return route.fulfill({response:result});
   }
   return route.continue();
  });
  const page=await context.newPage();const errors=[];page.on('pageerror',e=>errors.push(e.message));
  for(const path of ['/','/pricing','/login','/feedback']){
   const response=await page.goto('http://127.0.0.1:3088'+path);
   if(response.status()!==200)throw Error(path+' status '+response.status());
   if(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth))throw Error('overflow '+path);
   await page.screenshot({path:out+'candidate-'+width+'-'+(path.slice(1)||'home')+'.png',fullPage:true});
   samples.push({width,path,status:response.status()});
  }
  await context.addInitScript(t=>localStorage.setItem('yance_token',t),token);
  await page.goto('http://127.0.0.1:3088/discover');
  await page.getByLabel('政策原文关键词').fill('合成发布验收');
  await page.getByRole('button',{name:'检索原文',exact:true}).click();
  await page.getByRole('button',{name:'查看对应版本原文'}).first().click();
  await page.locator('details[open] mark').waitFor();
  if(!(await page.locator('details[open] mark').textContent()).includes('合成发布验收'))throw Error('wrong source highlight');
  await page.screenshot({path:out+'candidate-'+width+'-evidence.png',fullPage:true});
  if(errors.length)throw Error(errors.join('\n'));
  samples.push({width,path:'/discover',evidence_version_highlight:true});
  await context.close();
 }
 await browser.close();fs.writeFileSync(out+'candidate-browser.json',JSON.stringify(samples,null,2));console.log('CANDIDATE_BROWSER_PASSED');
})().catch(e=>{console.error(e);process.exit(1)});
