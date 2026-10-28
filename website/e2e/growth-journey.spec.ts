import {test,expect} from '@playwright/test';
import {mkdir} from 'node:fs/promises';
const out='../docs/audit-evidence/growth-20261028';
test.beforeEach(async({page,baseURL})=>{
 expect(new URL(baseURL!).hostname).toMatch(/^(localhost|127\.0\.0\.1)$/);
 await page.route('**/*',route=>['localhost','127.0.0.1'].includes(new URL(route.request().url()).hostname)?route.continue():route.abort());
});
test('industry assets, task paths and mobile layout',async({page})=>{
 await mkdir(out,{recursive:true});await page.goto('/');
 for(const image of await page.locator('img[src*="industries"]').all()) {await image.scrollIntoViewIfNeeded();await expect.poll(()=>image.evaluate(e=>(e as HTMLImageElement).naturalWidth)).toBeGreaterThan(0);}
 await expect(page.locator('#for-business')).toContainText('各类有政策需求的企业');
 await expect(page.locator('#start-with-your-task').getByRole('link',{name:'查看订单与交付'})).toHaveAttribute('href','/orders');
 await page.evaluate(()=>scrollTo(0,0));await page.screenshot({path:out+'/home-desktop.png'});
 await page.setViewportSize({width:390,height:844});await page.reload();
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
 await expect(page.getByRole('link',{name:'查看交付范围与价格'})).toHaveAttribute('href','/pricing');
 await page.evaluate(()=>scrollTo(0,0));await page.screenshot({path:out+'/home-mobile.png'});
});
test('provider failure retry reuses an existing order, contract simulation only',async({page})=>{
 await page.addInitScript(()=>localStorage.setItem('yance_token','synthetic-contract-token'));
 const product={id:'p',code:'POLICY_REPORT',name:'报告',price:99,entitlement_type:'report',purchase_available:true};
 await page.route('**/api/v1/**',r=>r.fulfill({status:503,json:{detail:'isolated contract'}}));
 await page.route('**/api/v1/auth/config',r=>r.fulfill({json:{checkout_idempotency_revision:1}}));
 await page.route('**/api/v1/products',r=>r.fulfill({json:[product]}));
 await page.route('**/api/v1/companies',r=>r.fulfill({json:[{id:'c',name:'合成企业'}]}));
 let orders=0;let payments=0;
 await page.route('**/api/v1/orders',r=>{orders++;expect(r.request().postDataJSON().client_request_id).toBeTruthy();return r.fulfill({json:{id:'synthetic-order'}})});
 await page.route('**/api/v1/payments/**',r=>{payments++;return r.fulfill({status:503,json:{detail:'合成渠道失败'}})});
 await page.goto('/checkout?product=POLICY_REPORT');
 await page.getByRole('button',{name:'确认支付 ¥99'}).click();
 await expect(page.getByText('合成渠道失败')).toBeVisible();
 await page.getByRole('button',{name:'确认支付 ¥99'}).click();
 await expect.poll(()=>payments).toBe(2);expect(orders).toBe(1);
});
