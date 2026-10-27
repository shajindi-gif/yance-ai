import { expect, test } from '@playwright/test';
const evidenceDir = process.env.YANCE_EVIDENCE_ROOT || '../docs/audit-evidence/audience-20261026';

test.beforeEach(async ({ page, baseURL }) => {
  expect(new URL(baseURL!).hostname).toMatch(/^(localhost|127\.0\.0\.1)$/);
  await page.route('**/*', route => {
    const url = new URL(route.request().url());
    if (!['localhost', '127.0.0.1'].includes(url.hostname)) return route.abort();
    if (url.pathname.startsWith('/api/')) return route.fulfill({ status: 503, json: { detail: 'Isolated contract only' } });
    return route.continue();
  });
});

test('homepage broadens audience while marking examples and feedback honestly', async ({ page }) => {
  await page.goto('/');
  await expect(page.getByRole('heading', { level: 1 })).toContainText('为新质生产力企业');
  const businesses = page.locator('#for-business');
  await expect(businesses.getByRole('heading', { name: '新质生产力企业', exact: true })).toBeVisible();
  await expect(businesses.getByRole('heading', { name: '科技与研发型企业' })).toBeVisible();
  await expect(businesses.getByRole('heading', { name: '各类有政策需求的企业' })).toBeVisible();
  const cases = page.locator('#scenarios');
  await expect(cases.getByRole('article')).toHaveCount(3);
  await expect(cases).toContainText('不是真实客户案例、客户评价或获批结果');
  for (const card of await cases.getByRole('article').all()) await expect(card).toContainText('场景示例');
  await expect(page.locator('#customer-feedback')).toContainText('暂未展示获授权的客户评价');
  await page.screenshot({ path: `${evidenceDir}/home-desktop.png`, fullPage: true });
  await page.getByRole('link', { name: '分享使用反馈' }).click();
  await expect(page).toHaveURL(/\/feedback$/);
  await expect(page.getByRole('button', { name: '提交反馈' })).toBeDisabled();
  await expect(page.getByRole('link', { name: '登录账号' })).toHaveAttribute('href', '/login?next=%2Ffeedback');
});

test('mobile scene links, focus and FAQ remain usable', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.emulateMedia({ reducedMotion: 'reduce' });
  await page.goto('/');
  const faq = page.locator('summary').filter({ hasText: '适合哪些企业' });
  await faq.focus(); await page.keyboard.press('Enter');
  await expect(page.getByText('重点服务新质生产力与科技企业，同时面向制造', { exact: false })).toBeVisible();
  const feedback = page.getByRole('link', { name: '分享使用反馈' });
  await feedback.focus(); await expect(feedback).toBeFocused();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  await page.screenshot({ path: `${evidenceDir}/home-mobile.png`, fullPage: true });
  await feedback.click();
  await expect(page.getByLabel('问题与建议')).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
});

test('authenticated feedback uses existing API, blocks repeats and confirms only after response', async ({ page }) => {
  await page.addInitScript(() => localStorage.setItem('yance_token', 'synthetic-ui-only'));
  let calls = 0; let release!: () => void;
  const responseReady = new Promise<void>(resolve => { release = resolve; });
  await page.route('**/api/v1/feedback', async route => {
    calls++;
    expect(route.request().method()).toBe('POST');
    expect(route.request().postDataJSON()).toEqual({ category: 'policy', message: '合成反馈：政策来源待核对', route: '/feedback' });
    await responseReady;
    await route.fulfill({ status: 201, json: { id: 'synthetic-feedback', status: 'open' } });
  });
  await page.goto('/feedback');
  await page.getByLabel('反馈类型').selectOption('policy');
  await page.getByLabel('问题与建议').fill('合成反馈：政策来源待核对');
  await page.getByRole('button', { name: '提交反馈' }).click();
  await expect(page.getByRole('button', { name: '正在提交…' })).toBeDisabled();
  await expect(page.getByText('反馈已提交，感谢你的建议。', { exact: false })).toHaveCount(0);
  release();
  await expect(page.getByRole('status').filter({ hasText: '反馈已提交' })).toBeVisible();
  await expect(page.getByLabel('问题与建议')).toHaveValue('');
  expect(calls).toBe(1);
});

test('failed feedback retains text and allows retry; whitespace is not submitted', async ({ page }) => {
  await page.addInitScript(() => localStorage.setItem('yance_token', 'synthetic-ui-only'));
  let calls = 0;
  await page.route('**/api/v1/feedback', route => { calls++; return route.fulfill({ status: 503, json: {} }); });
  await page.goto('/feedback');
  const message = page.getByLabel('问题与建议');
  await message.fill('  ');
  await expect(page.getByRole('button', { name: '提交反馈' })).toBeDisabled();
  await message.fill('合成反馈：功能入口不清楚');
  await page.getByRole('button', { name: '提交反馈' }).click();
  await expect(page.getByRole('alert').filter({ hasText: '内容已保留' })).toBeVisible();
  await expect(message).toHaveValue('合成反馈：功能入口不清楚');
  await expect(page.getByRole('button', { name: '提交反馈' })).toBeEnabled();
  expect(calls).toBe(1);
});
