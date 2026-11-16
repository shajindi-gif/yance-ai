import { existsSync, readFileSync } from 'node:fs';
import { test, expect, firefox, webkit } from '@playwright/test';

// Engine smoke coverage; does not stand in for native Safari/Edge or every workflow.
for (const engine of [firefox, webkit]) {
  test(`${engine.name()}: public pages and read-only workspace remain usable`, async ({baseURL},testInfo) => {
    test.skip(!existsSync(engine.executablePath()),'Browser engine is not installed');
    expect(new URL(baseURL!).hostname).toMatch(/^(localhost|127\.0\.0\.1)$/);
    const browser=await engine.launch();
    try {
      for (const width of [1440,768,390]) {
        const context=await browser.newContext({baseURL,viewport:{width,height:900}});
        await context.route('**/*',r=>['localhost','127.0.0.1'].includes(new URL(r.request().url()).hostname)?r.continue():r.abort());
        const page=await context.newPage();
        for (const path of ['/','/pricing','/login']) {
          await page.goto(path,{waitUntil:'networkidle'});
          await expect(page.locator('h1').first()).toBeVisible();
          expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),`${width} ${path} overflow`).toBe(true);
        }
        if (process.env.YANCE_ROLES_FIXTURE) {
          const data=JSON.parse(readFileSync(process.env.YANCE_ROLES_FIXTURE,'utf8')) as {token:string;application_id:string};
          await context.addInitScript(token=>localStorage.setItem('yance_token',token),data.token);
          await page.goto(`/applications/${data.application_id}`);
          await expect(page.getByRole('tab',{name:/工作稿/})).toBeVisible();
          await page.getByRole('tab',{name:/工作稿/}).click();
          await expect(page.getByRole('button',{name:'重新生成',exact:true})).toBeVisible();
          await page.screenshot({path:testInfo.outputPath(`workspace-${width}.png`)});
        }
        await context.close();
      }
    } finally { await browser.close(); }
  });
}
