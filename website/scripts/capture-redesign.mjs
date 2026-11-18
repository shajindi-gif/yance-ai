// Local-only visual/performance sample. Fixture credentials stay outside Git.
import { chromium } from '@playwright/test';
import { readFile, mkdir, writeFile } from 'node:fs/promises';

const baseURL = process.env.PLAYWRIGHT_BASE_URL || 'http://127.0.0.1:3024';
if (!['127.0.0.1', 'localhost'].includes(new URL(baseURL).hostname)) throw new Error('Local target required');
const output = process.env.YANCE_CAPTURE_OUT;
if (!output) throw new Error('YANCE_CAPTURE_OUT required');
const fixture = JSON.parse(await readFile(process.env.YANCE_ROLES_FIXTURE, 'utf8'));
await mkdir(output, { recursive: true });
const browser = await chromium.launch();
const results = [];
try {
  for (const [device, viewport] of Object.entries({ desktop: {width:1440,height:1000}, mobile:{width:390,height:844} })) {
    const context = await browser.newContext({baseURL, viewport, reducedMotion:'reduce'});
    await context.route('**/*', route => ['127.0.0.1','localhost'].includes(new URL(route.request().url()).hostname) ? route.continue() : route.abort());
    await context.addInitScript(token => {
      localStorage.setItem('yance_token', token);
      window.__visualVitals = {lcp: null, cls: 0};
      new PerformanceObserver(list => { for (const entry of list.getEntries()) window.__visualVitals.lcp = entry.startTime; }).observe({type:'largest-contentful-paint',buffered:true});
      new PerformanceObserver(list => { for (const entry of list.getEntries()) if (!entry.hadRecentInput) window.__visualVitals.cls += entry.value; }).observe({type:'layout-shift',buffered:true});
    }, fixture.token);
    const page = await context.newPage();
    const authorized = await context.request.get('/api/v1/auth/me', {headers:{Authorization:`Bearer ${fixture.token}`}});
    if (authorized.status() !== 200) throw new Error(`Isolated fixture expired or unavailable (${authorized.status()}); reseed before capturing`);
    for (const [name, path] of [['home','/'],['application',`/applications/${fixture.application_id}`],['pricing','/pricing'],['login','/login']].filter(([name]) => !process.env.YANCE_CAPTURE_PAGES || process.env.YANCE_CAPTURE_PAGES.split(',').includes(name))) {
      await page.goto(path);
      if (name === 'application') await page.getByRole('region',{name:'资格审查矩阵'}).waitFor();
      if (name === 'pricing') await page.getByText('加载产品目录...').waitFor({state:'hidden'});
      await page.screenshot({path:`${output}/${name}-${device}.png`,fullPage:false});
      results.push({name,device,...await page.evaluate(() => {
        const nav = performance.getEntriesByType('navigation')[0];
        return {response_start_ms:nav.responseStart,dom_content_loaded_ms:nav.domContentLoadedEventEnd,...window.__visualVitals,horizontal_overflow:document.documentElement.scrollWidth>innerWidth};
      })});
    }
    await context.close();
  }
  await writeFile(`${output}/measurements.json`,JSON.stringify({environment:'Local Chromium; no CPU/network throttling; warm server; one sample per page/device; screenshot-time LCP/CLS observation',results},null,2));
  console.log('Local visual samples captured (no credentials in output)');
} finally {await browser.close();}
