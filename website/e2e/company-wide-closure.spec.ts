import { readFileSync } from 'node:fs';
import { expect, test } from '@playwright/test';

test.use({trace:'off',video:'off',screenshot:'off'});
const apiBase = process.env.PLAYWRIGHT_API_BASE_URL!;
const fixture = () => JSON.parse(readFileSync(process.env.YANCE_ROLES_FIXTURE!, 'utf8')) as {feedback_admin_token:string; feedback_user_email:string; feedback_user_password:string};

test.beforeEach(async ({page,baseURL}) => {
  expect(new URL(baseURL!).hostname).toMatch(/^(localhost|127\.0\.0\.1)$/);
  expect(new URL(apiBase).hostname).toMatch(/^(localhost|127\.0\.0\.1)$/);
  await page.route('**/*', route => ['127.0.0.1','localhost'].includes(new URL(route.request().url()).hostname) ? route.continue() : route.abort());
});

test('real login returns to feedback; lost response retry creates one record and operator progress is visible', async ({page,browser,baseURL}) => {
  test.skip(!process.env.YANCE_ROLES_FIXTURE,'Requires an isolated seeded database');
  const operator=fixture();
  const email=operator.feedback_user_email;
  await page.goto('/feedback');
  await page.getByRole('link',{name:'登录账号',exact:true}).click();
  const form=page.locator('form').first();
  await form.locator('input[type=email]').fill(email);
  await form.locator('input[type=password]').fill(operator.feedback_user_password);
  await form.getByRole('button',{name:'登录',exact:true}).click();
  await expect(page).toHaveURL(/\/feedback$/);
  await expect(page.getByRole('heading',{name:'我的反馈进度'})).toBeVisible();
  let posts=0;
  const keys:string[]=[];
  let feedbackId='';
  await page.route('**/api/v1/feedback', async route => {
    if(route.request().method()!=='POST')return route.continue();
    posts++; keys.push(route.request().postDataJSON().client_request_id);
    if(posts===1){
      const accepted=await route.fetch({maxRedirects:0});
      expect(accepted.status()).toBe(201);
      feedbackId=(await accepted.json()).id;
      return route.abort(); // Failure injection: persisted successfully, response lost.
    }
    return route.continue();
  });
  const syntheticMessage=`合成使用反馈：请明确显示来源缺失的下一步操作。${Date.now()}`;
  await page.getByLabel('问题与建议').fill(syntheticMessage);
  await page.getByRole('button',{name:'提交反馈',exact:true}).click();
  await expect(page.getByRole('alert').filter({hasText:'内容已保留'})).toBeVisible();
  await expect(page.getByLabel('问题与建议')).toHaveValue(syntheticMessage);
  await page.getByRole('button',{name:'提交反馈',exact:true}).click();
  await expect(page.getByRole('status').filter({hasText:'反馈已提交'})).toBeVisible();
  const history=page.getByRole('region',{name:'我的反馈进度'});
  await expect(history.getByText(syntheticMessage,{exact:true})).toHaveCount(1);
  expect(keys[0]).toBeTruthy(); expect(keys[1]).toBe(keys[0]);
  expect(posts).toBe(2);
  const operatorContext=await browser.newContext({baseURL});
  await operatorContext.route('**/*',route => ['localhost','127.0.0.1'].includes(new URL(route.request().url()).hostname) ? route.continue() : route.abort());
  await operatorContext.addInitScript(token=>localStorage.setItem('yance_token',token),operator.feedback_admin_token);
  const operatorPage=await operatorContext.newPage();
  await operatorPage.goto('/admin');
  await operatorPage.getByRole('tab',{name:/^Feedback/}).click();
  const feedbackRow=operatorPage.getByRole('row').filter({hasText:syntheticMessage});
  await expect(feedbackRow).toBeVisible();
  const processed=operatorPage.waitForResponse(response=>response.url().endsWith(`/admin/feedback/${feedbackId}`)&&response.request().method()==='PATCH');
  await feedbackRow.getByRole('combobox',{name:'更新反馈状态'}).selectOption('resolved');
  expect((await processed).status()).toBe(200);
  await expect(feedbackRow.getByRole('combobox',{name:'更新反馈状态'})).toHaveValue('resolved');
  await operatorContext.close();
  await history.getByRole('button',{name:'刷新进度'}).click();
  await expect(history.getByRole('listitem').filter({hasText:syntheticMessage}).getByText('已处理',{exact:true})).toBeVisible();
  await page.setViewportSize({width:390,height:844});
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
  await page.evaluate(() => window.scrollTo({top:0,behavior:'instant'}));
  await page.screenshot({path:'../docs/audit-evidence/company-wide-20261027/feedback-mobile.png',fullPage:true});
});

test('unsafe post-login destinations return to the workspace', async ({page}) => {
  test.skip(!process.env.YANCE_ROLES_FIXTURE,'Requires an isolated seeded database');
  const operator=fixture();
  const email=operator.feedback_user_email;
  await page.goto('/login?next=https%3A%2F%2Fevil.invalid');
  const form=page.locator('form').first();
  await form.locator('input[type=email]').fill(email);
  await form.locator('input[type=password]').fill(operator.feedback_user_password);
  await form.getByRole('button',{name:'登录',exact:true}).click();
  await expect(page).toHaveURL(/\/dashboard$/);
});
