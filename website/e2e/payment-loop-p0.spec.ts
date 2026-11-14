import {readFileSync} from 'node:fs';
import {test,expect} from '@playwright/test';

test.beforeEach(async({page,baseURL})=>{
  expect(new URL(baseURL!).hostname).toMatch(/^(localhost|127\.0\.0\.1)$/);
  await page.route('**/*',route=>['localhost','127.0.0.1'].includes(new URL(route.request().url()).hostname)?route.continue():route.abort());
});

test('prices are present before browser JavaScript executes',async({browser,baseURL})=>{
  const context=await browser.newContext({javaScriptEnabled:false});
  const page=await context.newPage();
  await page.route('**/*',route=>['localhost','127.0.0.1'].includes(new URL(route.request().url()).hostname)?route.continue():route.abort());
  await page.goto(baseURL+'/pricing');
  await expect(page.locator('.pricing-price').filter({hasText:'¥99'})).toBeVisible();
  await expect(page.locator('.pricing-card')).toHaveCount(2);
  await expect(page.getByText('更多服务 · 预约咨询',{exact:true})).toBeVisible();
  await context.close();
});

test('Alipay return is compensated through the server query without trusting URL status',async({page})=>{
  await page.addInitScript(()=>localStorage.setItem('yance_token','synthetic-contract'));
  await page.route('**/api/v1/orders/by-no/RETURN-ATTEMPT',route=>route.fulfill({json:{id:'lookup-order',order_no:'YRETURN',amount:99,status:'created'}}));
  await page.route('**/api/v1/orders/lookup-order/checkout',route=>route.fulfill({json:{provider:'alipay'}}));
  let queries=0;
  await page.route('**/api/v1/payments/alipay/query?order_id=lookup-order',route=>{queries++;return route.fulfill({json:{status:'paid',queried:true}});});
  await page.goto('/success?out_trade_no=RETURN-ATTEMPT&trade_status=TRADE_SUCCESS');
  await expect(page.getByRole('heading',{name:'付款已确认'})).toBeVisible();
  await expect(page.getByRole('link',{name:'获取报告 →'})).toBeVisible();
  expect(queries).toBe(1);
});

test('real isolated merchant-number lookup preserves an unpaid order',async({page})=>{
  test.skip(!process.env.YANCE_CHECKOUT_FIXTURE,'Requires isolated checkout fixture');
  const fixture=JSON.parse(readFileSync(process.env.YANCE_CHECKOUT_FIXTURE!,'utf8'));
  const state=await page.request.get(`/api/v1/orders/${fixture.order_id}/checkout`,{headers:{Authorization:`Bearer ${fixture.token}`}});
  expect(state.status()).toBe(200);
  const order=(await state.json()).order;
  await page.addInitScript(token=>localStorage.setItem('yance_token',token),fixture.token);
  await page.goto('/success?out_trade_no='+encodeURIComponent(order.order_no));
  await expect(page.getByText(`订单号：${order.order_no} · ¥99.00`)).toBeVisible();
  await expect(page.getByRole('heading',{name:'等待付款确认'})).toBeVisible();
});
