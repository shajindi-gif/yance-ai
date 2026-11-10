import {test,expect} from '@playwright/test';

test.beforeEach(async({page,baseURL})=>{
 expect(new URL(baseURL!).hostname).toMatch(/^(localhost|127\.0\.0\.1)$/);
 await page.route('**/*',r=>['localhost','127.0.0.1'].includes(new URL(r.request().url()).hostname)?r.continue():r.abort());
 await page.route('**/api/v1/**',r=>r.fulfill({status:503,json:{detail:'isolated contract'}}));
});
test('two identity entrances, code signup and legacy email password access',async({page})=>{
 await page.route('**/api/v1/auth/config',r=>r.fulfill({json:{email_login_enabled:true,sms_login_enabled:true}}));
 await page.goto('/login?register=1');
 await expect(page.getByRole('button',{name:'邮箱注册 / 登录',exact:true})).toBeVisible();
 await expect(page.getByRole('button',{name:'手机注册 / 登录',exact:true})).toBeVisible();
 await expect(page.getByLabel('验证码',{exact:true})).toBeVisible();
 await expect(page.getByLabel('密码',{exact:true})).toHaveCount(0);
 await expect(page.getByRole('button',{name:'免费注册',exact:true})).toHaveCount(0);
 await page.getByRole('button',{name:'使用邮箱密码登录',exact:true}).click();
 await expect(page.getByLabel('密码',{exact:true})).toBeVisible();
 await page.getByRole('button',{name:'免费注册',exact:true}).click();
 await expect(page.getByLabel('工作邮箱')).toBeVisible();
 await page.getByRole('button',{name:'手机注册 / 登录',exact:true}).click();
 await expect(page.getByLabel('中国大陆手机号')).toBeVisible();
 await page.setViewportSize({width:390,height:844});
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
});
test('return URL cannot claim payment; retry displays only server-confirmed order state',async({page})=>{
 const pageErrors:string[]=[];
 page.on('pageerror',error=>pageErrors.push(error.message));
 await page.addInitScript(()=>localStorage.setItem('yance_token','synthetic-contract'));
 let paid=false;
 await page.route('**/api/v1/orders',r=>r.fulfill({json:[{id:'test-order',order_no:'SYNTHETIC',amount:99,status:paid?'paid':'created'}]}));
 await page.goto('/success?order=test-order&status=paid');
 await expect(page.getByRole('heading',{name:'等待付款确认'})).toBeVisible();
 await expect(page.getByRole('link',{name:'获取报告 →'})).toHaveCount(0);
 paid=true;
 await page.getByRole('button',{name:'刷新付款结果'}).click();
 await expect(page.getByRole('heading',{name:'付款已确认'})).toBeVisible();
 await expect(page.getByRole('link',{name:'获取报告 →'})).toBeVisible();
 await expect(page.getByRole('link',{name:'申请开票'})).toHaveAttribute('href','/billing');
 expect(pageErrors).toEqual([]);
});

test('resume uses server price and payment channel and never creates another order',async({page})=>{
 await page.addInitScript(()=>localStorage.setItem('yance_token','synthetic-contract'));
 await page.route('**/api/v1/auth/config',r=>r.fulfill({json:{checkout_idempotency_revision:1,checkout_resume_revision:1}}));
 await page.route('**/api/v1/products',r=>r.fulfill({json:[{id:'p',code:'POLICY_REPORT',price:199,purchase_available:true,entitlement_type:'report'}]}));
 await page.route('**/api/v1/companies',r=>r.fulfill({json:[{id:'c',name:'合成企业'}]}));
 await page.route('**/api/v1/orders/synthetic/checkout',r=>r.fulfill({json:{order:{id:'synthetic',product_code:'POLICY_REPORT',resource_id:'c',amount:79,currency:'CNY',status:'created'},provider:'wechat',can_continue:true,reason:null}}));
 let orders=0;
 await page.route('**/api/v1/orders',r=>{orders++;return r.fulfill({status:500});});
 await page.route('**/api/v1/payments/wechat/native*',r=>r.fulfill({json:{code_url:'weixin://synthetic'}}));
 await page.goto('/checkout?order=synthetic&amount=1');
 await expect(page.getByRole('button',{name:'生成付款二维码 ¥79'})).toBeVisible();
 await expect(page.getByRole('button',{name:'支付宝',exact:true})).toBeDisabled();
 await page.reload();
 await page.getByRole('button',{name:'生成付款二维码 ¥79'}).click();
 await expect(page.getByRole('img',{name:'微信支付的二维码'})).toBeVisible();
 expect(orders).toBe(0);
});

test('price change requires another confirmation before contacting a payment provider',async({page})=>{
 await page.addInitScript(()=>localStorage.setItem('yance_token','synthetic-contract'));
 await page.route('**/api/v1/auth/config',r=>r.fulfill({json:{checkout_idempotency_revision:1}}));
 await page.route('**/api/v1/products',r=>r.fulfill({json:[{id:'p',code:'POLICY_REPORT',price:99,purchase_available:true,entitlement_type:'report'}]}));
 await page.route('**/api/v1/companies',r=>r.fulfill({json:[{id:'c',name:'合成企业'}]}));
 let orders=0;let payments=0;
 await page.route('**/api/v1/orders',r=>{orders++;return r.fulfill({json:{id:'priced-order',status:'created',amount:120}});});
 await page.route('**/api/v1/payments/**',r=>{payments++;return r.fulfill({status:503,json:{detail:'合成渠道失败'}});});
 await page.goto('/checkout?product=POLICY_REPORT');
 await page.getByRole('button',{name:'确认支付 ¥99'}).click();
 await expect(page.getByRole('alert').filter({hasText:'价格已更新'})).toContainText('价格已更新');
 expect(payments).toBe(0);
 await page.getByRole('button',{name:'确认支付 ¥120'}).click();
 await expect(page.getByRole('alert').filter({hasText:'合成渠道失败'})).toContainText('合成渠道失败');
 expect(orders).toBe(1);expect(payments).toBe(1);
});

test('real local API restores an order and preserves it when provider is unavailable',async({page})=>{
 test.skip(!process.env.YANCE_CHECKOUT_FIXTURE,'Requires isolated API fixture');
 const {readFileSync}=await import('node:fs');
 const data=JSON.parse(readFileSync(process.env.YANCE_CHECKOUT_FIXTURE!,'utf8')) as {token:string;order_id:string};
 // Remove contract stubs while retaining an explicit localhost-only transport guard.
 await page.unroute('**/api/v1/**');
 await page.addInitScript(token=>localStorage.setItem('yance_token',token),data.token);
 await page.goto(`/checkout?order=${data.order_id}`);
 await expect(page.getByRole('button',{name:'生成付款二维码 ¥99'})).toBeVisible();
 await expect(page.getByRole('button',{name:'支付宝',exact:true})).toBeDisabled();
 await page.reload();
 await page.getByRole('button',{name:'生成付款二维码 ¥99'}).click();
 await expect(page.getByRole('alert').filter({hasText:'not configured'})).toBeVisible();
 const result=await page.request.get('/api/v1/orders',{headers:{Authorization:`Bearer ${data.token}`}});
 expect(result.status()).toBe(200);
 const orders=await result.json();
 expect(orders).toHaveLength(1);expect(orders[0].id).toBe(data.order_id);
});

test('pending return automatically refreshes the server status without claiming early success',async({page})=>{
 await page.addInitScript(()=>localStorage.setItem('yance_token','synthetic-contract'));
 let reads=0;
 await page.route('**/api/v1/orders',r=>{reads++;return r.fulfill({json:[{id:'auto-order',order_no:'SYNTHETIC',amount:99,status:reads>1?'paid':'created'}]});});
 await page.goto('/success?order=auto-order');
 await expect(page.getByRole('heading',{name:'等待付款确认'})).toBeVisible();
 await expect(page.getByRole('heading',{name:'付款已确认'})).toBeVisible({timeout:6000});
 expect(reads).toBe(2);
});
