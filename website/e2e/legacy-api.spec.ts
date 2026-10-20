import { expect, test } from '@playwright/test';

// Contract simulation only: this checks compatibility with the production API's
// older capability response, not the quality of real customer data.
test('older API supports profile saving and local logout without new endpoints', async ({ page, request }) => {
  const apiBase = process.env.PLAYWRIGHT_API_BASE_URL || 'http://127.0.0.1:8018/api/v1';
  const registered = await request.post(`${apiBase}/auth/register`, { data: {
    company_name: '合成旧接口兼容企业', owner_name: '合成用户',
    owner_email: `legacy-web-${Date.now()}@example.com`,
    owner_password: 'synthetic-browser-password-123', agreed_terms_version: 'test-terms',
  } });
  expect(registered.status()).toBe(201);
  const { access_token: token } = await registered.json();
  const companies = await request.get(`${apiBase}/companies`, { headers: { Authorization: `Bearer ${token}` } });
  const [company] = await companies.json();
  await page.addInitScript((value) => localStorage.setItem('yance_token', value), token);
  await page.route('**/auth/config', (route) => route.fulfill({ json: { email_login_enabled: false } }));
  let logoutRequests = 0;
  page.on('request', (req) => { if (req.url().endsWith('/auth/logout')) logoutRequests++; });
  await page.goto(`/companies/${company.id}`);
  await expect(page.getByLabel('所属行业', { exact: true })).toBeVisible();
  await expect(page.getByLabel('区县', { exact: true })).toHaveCount(0);
  await page.getByLabel('所属行业', { exact: true }).fill('人工智能');
  const saveRequest = page.waitForRequest((req) => req.method() === 'PUT' && req.url().endsWith(`/companies/${company.id}/profile`));
  await page.getByRole('button', { name: '保存草稿', exact: true }).click();
  expect((await saveRequest).postDataJSON()).not.toHaveProperty('district');
  await expect(page.getByText(/画像草稿已保存/)).toBeVisible();
  await page.getByRole('button', { name: '退出当前设备', exact: true }).click();
  await expect(page).toHaveURL(/\/login$/);
  expect(await page.evaluate(() => localStorage.getItem('yance_token'))).toBeNull();
  expect(logoutRequests).toBe(0);
});
