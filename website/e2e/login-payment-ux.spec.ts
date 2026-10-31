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
});
