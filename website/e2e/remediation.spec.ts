import { readFileSync } from 'node:fs';
import { test, expect } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';

// UI contracts use isolated supplier responses only; real API journeys remain separate.
test.beforeEach(async ({page,baseURL}) => {
  expect(new URL(baseURL!).hostname).toMatch(/^(localhost|127\.0\.0\.1)$/);
  await page.route('**/*', r => ['localhost','127.0.0.1'].includes(new URL(r.request().url()).hostname) ? r.continue() : r.abort());
});
test('nine audited page/viewport samples have no automated WCAG violations', async ({page}, testInfo) => {
  const results = [];
  for (const width of [1440,768,390]) {
    await page.setViewportSize({width,height:900});
    for (const path of width === 1440 ? ['/','/pricing','/login','/about','/privacy'] : ['/','/login']) {
      await page.goto(path, {waitUntil:'networkidle'});
      const result = await new AxeBuilder({page}).withTags(['wcag2a','wcag2aa','wcag21a','wcag21aa','wcag22aa']).analyze();
      results.push({width,path,violations:result.violations,incomplete:result.incomplete.map(v=>v.id)});
      expect(result.violations, `${width} ${path}`).toEqual([]);
    }
  }
  await testInfo.attach('axe-samples', {body: JSON.stringify(results,null,2),contentType:'application/json'});
});
test('payment QR is rendered locally without an external image service', async ({page}) => {
  await page.addInitScript(()=>localStorage.setItem('yance_token','synthetic-only'));
  await page.route('**/api/v1/**',r=>r.fulfill({status:503,json:{detail:'isolated test'}}));
  await page.route('**/api/v1/auth/config',r=>r.fulfill({json:{checkout_idempotency_revision:1}}));
  await page.route('**/api/v1/products',r=>r.fulfill({json:[{id:'p',code:'POLICY_REPORT',name:'合成报告',price:99,entitlement_type:'report',purchase_available:true}]}));
  await page.route('**/api/v1/companies',r=>r.fulfill({json:[{id:'c',name:'合成企业'}]}));
  let orders=0;
  await page.route('**/api/v1/orders',r=>{orders++;return r.fulfill({json:{id:'synthetic-order'}});});
  await page.route('**/api/v1/payments/wechat/native*',r=>r.fulfill({json:{code_url:'weixin://wxpay/bizpayurl?pr=synthetic-only',out_trade_no:'synthetic',amount_fen:9900}}));
  await page.goto('/checkout?product=POLICY_REPORT');
  await page.getByText('微信支付', {exact:true}).click();
  await page.getByRole('button',{name:'生成付款二维码 ¥99'}).click();
  const qr = page.getByRole('img',{name:'微信支付的二维码'});
  await expect(qr).toHaveAttribute('src',/^data:image\/png;base64,/);
  expect(await qr.evaluate((e)=>(e as HTMLImageElement).naturalWidth)).toBeGreaterThan(0);
  expect(orders).toBe(1);
});

test('real isolated API: demo request is persisted privately and displayed with a server status', async ({page}, testInfo) => {
  test.skip(!process.env.YANCE_ROLES_FIXTURE,'Requires isolated data; never production');
  const fixture=JSON.parse(readFileSync(process.env.YANCE_ROLES_FIXTURE!,'utf8')) as {token:string};
  await page.addInitScript(token=>localStorage.setItem('yance_token',token), fixture.token);
  await page.goto('/feedback?category=sales');
  await expect(page.getByRole('heading',{name:'申请产品演示与需求沟通'})).toBeVisible();
  const message=`合成演示需求 ${Date.now()}：希望了解政策条件与材料复核流程`;
  await page.getByLabel('问题与建议').fill(message);
  const response=page.waitForResponse(r=>r.url().endsWith('/api/v1/feedback')&&r.request().method()==='POST');
  await page.getByRole('button',{name:'提交演示需求'}).click();
  expect((await response).status()).toBe(201);
  await expect(page.getByText(message,{exact:true})).toBeVisible();
  await expect(page.getByText('已收到',{exact:true})).toBeVisible();
  await page.screenshot({path:testInfo.outputPath('demo-request.png'),fullPage:true});
});

test('private entrances are excluded from indexing and base/embed protection is present', async ({page}) => {
  const response=await page.goto('/login');
  expect(response?.headers()['x-robots-tag']).toBe('noindex, nofollow');
  expect(response?.headers()['content-security-policy']).toContain("object-src 'none'");
  expect(response?.headers()['content-security-policy']).toContain("base-uri 'self'");
  await page.goto('/');
  await expect(page.locator('meta[property="og:image"]')).toHaveAttribute('content',/og-brand\.png$/);
  const schema=JSON.parse(await page.locator('script[type="application/ld+json"]').innerText());
  expect(schema['@type']).toBe('Organization');
  expect(schema.url).toBe('https://yance.ai');
});
