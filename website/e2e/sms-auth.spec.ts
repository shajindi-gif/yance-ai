import { test, expect } from '@playwright/test';

test.beforeEach(async ({ page, baseURL }) => {
  expect(new URL(baseURL!).hostname).toMatch(/^(localhost|127\.0\.0\.1)$/);
  await page.route('**/*', route => ['127.0.0.1', 'localhost'].includes(new URL(route.request().url()).hostname) ? route.continue() : route.abort());
});

test('mobile registration through real local API, OTP replay rejected, company accessible', async ({ page, request }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  const phone = '199' + String(Date.now()).slice(-8);
  await page.goto('/login?next=/companies');
  await page.getByRole('button', { name: '手机注册 / 登录', exact: true }).click();
  await page.getByLabel('中国大陆手机号').fill(phone);
  await page.getByRole('button', { name: '获取短信验证码', exact: true }).click();
  await expect(page.getByRole('status')).toContainText('短信服务已受理');
  await page.getByLabel('短信验证码', { exact: true }).fill('000000');
  await page.getByRole('button', { name: '短信验证并登录', exact: true }).click();
  await expect(page.getByRole('alert').filter({ hasText: '验证码不正确' })).toContainText('验证码不正确');
  await expect(page.getByLabel('中国大陆手机号')).toHaveValue(phone);
  await page.getByLabel('短信验证码', { exact: true }).fill('123456');
  await page.getByRole('button', { name: '短信验证并登录', exact: true }).click();
  await page.getByLabel('联系人姓名', { exact: true }).fill('合成浏览器用户');
  await page.getByLabel('企业全称', { exact: true }).fill('合成手机注册企业');
  await page.getByRole('checkbox').check();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  await page.evaluate(() => window.scrollTo(0, 0));
  await page.screenshot({ path: '../docs/audit-evidence/sms-auth-20261029/mobile-register.png', fullPage: true });
  await page.getByRole('button', { name: '完成注册并登录', exact: true }).click();
  await expect(page).toHaveURL(/\/companies$/);
  await expect(page.getByText('合成手机注册企业', { exact: true }).first()).toBeVisible();
  const token = await page.evaluate(() => localStorage.getItem('yance_token'));
  const me = await request.get('/api/v1/auth/me', { headers: { Authorization: `Bearer ${token}` } });
  expect(me.status()).toBe(200);
  expect((await me.json()).email).toBeNull();
  const replay = await request.post('/api/v1/auth/sms/verify', { data: { phone, code: '123456' } });
  expect(replay.status()).toBe(401);
});

test('email account binds phone through authenticated local API', async ({ page, request }) => {
  const id = Date.now().toString();
  const registered = await request.post('/api/v1/auth/register', { data: { company_name: '合成绑定测试企业', owner_email: `sms-${id}@example.com`, owner_name: '合成测试用户', owner_password: 'synthetic-password-123456', agreed_terms_version: '2026-09-19' } });
  expect(registered.status()).toBe(201);
  const token = (await registered.json()).access_token;
  await page.goto('/login');
  await page.evaluate(t => localStorage.setItem('yance_token', t), token);
  await page.goto('/settings');
  await page.getByLabel('中国大陆手机号').fill('198' + id.slice(-8));
  await page.getByRole('button', { name: '获取短信验证码', exact: true }).click();
  await expect(page.getByRole('status')).toContainText('短信服务已受理');
  await page.getByLabel('短信验证码', { exact: true }).fill('123456');
  await page.getByRole('button', { name: '验证并绑定手机号', exact: true }).click();
  await expect(page.getByRole('status')).toContainText('手机号绑定成功');
});
