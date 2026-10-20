import { expect, test } from '@playwright/test';

const apiBase = process.env.PLAYWRIGHT_API_BASE_URL || 'http://127.0.0.1:8018/api/v1';

test('password login recovers from an error and logout revokes the saved session', async ({ page, request }) => {
  const email = `audit-browser-${Date.now()}@example.com`;
  const password = 'synthetic-browser-password-123';
  const registered = await request.post(`${apiBase}/auth/register`, { data: {
    company_name: '合成浏览器验收企业', owner_name: '合成用户', owner_email: email,
    owner_password: password, agreed_terms_version: 'test-terms',
  } });
  expect(registered.status()).toBe(201);
  await page.goto('/login');
  const form = page.locator('form').first();
  await form.locator('input[type=email]').fill(email);
  await form.locator('input[type=password]').fill('wrong-test-password');
  await form.getByRole('button', { name: '登录', exact: true }).click();
  await expect(page.getByText('Incorrect email or password')).toBeVisible();
  await form.locator('input[type=password]').fill(password);
  await form.locator('input[type=password]').press('Enter');
  await expect(page).toHaveURL(/\/dashboard$/);
  const token = await page.evaluate(() => localStorage.getItem('yance_token'));
  expect(token).toBeTruthy();
  await page.getByRole('button', { name: '退出所有设备', exact: true }).click();
  await expect(page).toHaveURL(/\/login$/);
  const revoked = await request.get(`${apiBase}/auth/me`, { headers: { Authorization: `Bearer ${token}` } });
  expect(revoked.status()).toBe(401);
});

test('pricing hydrates with the server catalogue and records a local timing sample', async ({ page }, testInfo) => {
  const errors: string[] = [];
  page.on('pageerror', (error) => errors.push(error.message));
  const catalogue = page.waitForResponse((response) => response.url().endsWith('/products') && response.status() === 200);
  await page.goto('/pricing');
  await catalogue;
  await expect(page.getByRole('heading', { name: '按次购买，需要时再买' })).toBeVisible();
  await expect(page.locator('.pricing-card').first()).toBeVisible();
  expect(errors).toEqual([]);
  const navigation = await page.evaluate(() => {
    const entry = performance.getEntriesByType('navigation')[0] as PerformanceNavigationTiming;
    return { ttfbMs: entry.responseStart - entry.requestStart, domContentLoadedMs: entry.domContentLoadedEventEnd, loadMs: entry.loadEventEnd, viewport: `${innerWidth}x${innerHeight}`, userAgent: navigator.userAgent };
  });
  await testInfo.attach('local-navigation-sample', { body: JSON.stringify({ ...navigation, network: 'loopback, no throttling', samples: 1, productionPerformanceClaim: false }), contentType: 'application/json' });
});

test('mobile login has no horizontal page overflow and the first keyboard target is visible', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto('/login');
  await expect(page.locator('form input[type=email]').first()).toBeVisible();
  await page.keyboard.press('Tab');
  await expect(page.locator(':focus')).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
});

test('district evidence survives saving and refreshing a company profile', async ({ page, request }) => {
  const registration = await request.post(`${apiBase}/auth/register`, { data: {
    company_name: '合成区县证据企业', owner_name: '合成用户',
    owner_email: `district-browser-${Date.now()}@example.com`, owner_password: 'synthetic-browser-password-123',
    agreed_terms_version: 'test-terms',
  } });
  expect(registration.status()).toBe(201);
  const { access_token: token } = await registration.json();
  const companies = await request.get(`${apiBase}/companies`, { headers: { Authorization: `Bearer ${token}` } });
  const [company] = await companies.json();
  await page.addInitScript((value) => localStorage.setItem('yance_token', value), token);
  await page.goto(`/companies/${company.id}`);
  await page.getByLabel('区县', { exact: true }).fill('浦东新区');
  await page.getByRole('button', { name: '保存草稿', exact: true }).click();
  await expect(page.getByText(/画像草稿已保存/)).toBeVisible();
  await page.reload();
  await expect(page.getByLabel('区县', { exact: true })).toHaveValue('浦东新区');
});
