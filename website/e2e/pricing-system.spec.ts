import { expect, test } from '@playwright/test';

// Synthetic UI contracts only; no payment provider, production API or email calls.
const catalogue = [
  { code: 'FREE_POLICY_MATCH', name: '免费匹配', price: 0, original_price: null, entitlement_type: 'match' },
  { code: 'POLICY_REPORT', name: '企业政策AI体检报告', price: 99, original_price: 199, entitlement_type: 'report' },
  { code: 'POLICY_DIAGNOSIS', name: '单项目申报诊断', price: 299, original_price: 399, entitlement_type: 'diagnosis' },
  { code: 'APPLICATION_PLAN', name: 'AI申报方案包', price: 699, original_price: 999, entitlement_type: 'application' },
].map((product, i) => ({ ...product, id: `synthetic-${i}`, promotional_price: null, product_type: 'service', description: 'Synthetic legacy description' }));

test.beforeEach(async ({ page, baseURL }) => {
  expect(new URL(baseURL!).hostname).toMatch(/^(localhost|127\.0\.0\.1)$/);
  await page.route('**/*', route => {
    const url = new URL(route.request().url());
    if (!['localhost', '127.0.0.1'].includes(url.hostname)) return route.abort();
    if (url.pathname.startsWith('/api/')) return route.fulfill({ status: 503, json: { detail: 'Unconfigured isolated contract' } });
    return route.continue();
  });
  await page.route('**/api/v1/products', route => route.fulfill({ json: catalogue }));
});

test('catalogue controls price; unaccepted project tiers stay visible and unavailable', async ({ page }) => {
  await page.goto('/pricing');
  const report = page.getByRole('article', { name: '企业政策机会简报' });
  await expect(report).toContainText('¥99');
  await expect(report).not.toContainText('¥199');
  await expect(report.getByRole('button', { name: '选择企业并购买' })).toBeEnabled();
  for (const name of ['单项政策条件核对包', '申报材料工作稿包']) {
    const card = page.getByRole('article', { name });
    await expect(card).toContainText('待验收');
    await expect(card.getByRole('button', { name: '待开通' })).toBeDisabled();
  }
  await expect(page.getByText('团队订阅仍在准备中', { exact: false })).toBeVisible();
  await page.screenshot({ path: '../docs/audit-evidence/pricing-system-20261025/catalogue-desktop.png', fullPage: true });
  await report.getByRole('button').click();
  await expect(page).toHaveURL(/\/login\?register=1/);
});

test('server promotional price wins; no hard-coded fallback catalogue on failure', async ({ page }) => {
  await page.route('**/api/v1/products', route => route.fulfill({ json: [{ ...catalogue[1], price: 123, promotional_price: 87 }] }));
  await page.goto('/pricing');
  await expect(page.getByRole('article')).toContainText('¥87');
  await expect(page.getByRole('article')).not.toContainText('¥99');
  await page.route('**/api/v1/products', route => route.fulfill({ status: 503, json: {} }));
  await page.reload();
  await expect(page.getByRole('alert').filter({ hasText: '当前无法读取' })).toBeVisible();
  await expect(page.getByRole('article')).toHaveCount(0);
  await page.route('**/api/v1/products', route => route.fulfill({ json: [] }));
  await page.getByRole('button', { name: '重新加载产品目录' }).click();
  await expect(page.getByText('当前没有已启用的产品。', { exact: false })).toBeVisible();
});

test('mobile scope and customer review FAQ remain readable with keyboard', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto('/pricing');
  await expect(page.getByRole('article', { name: '企业政策机会简报' })).toBeVisible();
  const summary = page.locator('summary').filter({ hasText: '衍策会替企业审核和申报吗' });
  await summary.focus();
  await page.keyboard.press('Enter');
  await expect(page.getByText('业务复核由客户本人或授权团队完成。', { exact: false })).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  await page.screenshot({ path: '../docs/audit-evidence/pricing-system-20261025/catalogue-mobile.png', fullPage: true });
});

test('checkout retains server identity and price without striking unverifiable originals or creating an order', async ({ page }) => {
  await page.addInitScript(() => localStorage.setItem('yance_token', 'synthetic-ui-contract'));
  await page.route('**/api/v1/companies', route => route.fulfill({ json: [{ id: 'synthetic-company', name: '合成企业', industry: '制造', province: '江苏' }] }));
  const writes: string[] = [];
  page.on('request', request => { if (request.method() !== 'GET' && new URL(request.url()).pathname.startsWith('/api/')) writes.push(request.url()); });
  await page.goto('/checkout?product=POLICY_REPORT');
  await expect(page.getByRole('heading', { name: '确认订单' })).toBeVisible();
  await expect(page.getByText('商品：企业政策AI体检报告 · POLICY_REPORT')).toBeVisible();
  await expect(page.getByText('¥199', { exact: true })).toHaveCount(0);
  await expect(page.getByText('¥99', { exact: true })).toHaveCount(2);
  await page.goto('/checkout?product=POLICY_DIAGNOSIS');
  await expect(page.getByText('待开通。目录金额不代表该交付已验收', { exact: false })).toBeVisible();
  await expect(page.getByRole('button', { name: '待开通', exact: true })).toBeDisabled();
  expect(writes).toEqual([]);
});
