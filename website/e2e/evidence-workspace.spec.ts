import { readFileSync } from 'node:fs';
import { expect, test } from '@playwright/test';

const fixturePath = process.env.YANCE_V2_FIXTURE;
test('evidence matrix links real API results and creates persistent gap tasks', async ({ page }) => {
  test.skip(!fixturePath, 'Requires an explicitly seeded isolated V2 database');
  const fixture = JSON.parse(readFileSync(fixturePath!, 'utf8')) as { token: string; application_id: string };
  await page.route('**/*', async route => {
    const url = new URL(route.request().url());
    if (!['127.0.0.1', 'localhost'].includes(url.hostname)) return route.abort();
    return route.continue();
  });
  await page.addInitScript(token => localStorage.setItem('yance_token', token), fixture.token);
  const errors: string[] = [];
  page.on('pageerror', error => errors.push(error.message));
  await page.goto(`/applications/${fixture.application_id}`);
  await expect(page.getByRole('heading', { name: '资格审查矩阵' })).toBeVisible();
  await expect(page.getByRole('cell', { name: /证据不足/ }).first()).toBeVisible();
  await page.getByText('查看政策原文 · 逐字核验', { exact: true }).first().click();
  await expect(page.getByText('支持人工智能企业', { exact: true })).toBeVisible();
  await expect(page.getByText(/企业自述，不代表第三方鉴证/).first()).toBeVisible();
  await page.getByRole('button', { name: '创建补证待办', exact: true }).click();
  await expect(page.getByText('补充核验：研发证明', { exact: true })).toBeVisible();
  await page.reload();
  await page.getByRole('button', { name: '创建补证待办', exact: true }).click();
  await expect(page.getByText('补充核验：研发证明', { exact: true })).toHaveCount(1);
  await page.getByRole('tab', { name: /工作稿/ }).click();
  await page.getByRole('button', { name: '重新生成', exact: true }).click();
  await expect(page.getByText(/v1 · deterministic-evidence-v1/)).toBeVisible();
  await page.getByRole('tab', { name: '资格矩阵', exact: true }).click();
  await page.screenshot({ path: test.info().outputPath('evidence-matrix-desktop.png'), fullPage: true });
  await page.setViewportSize({ width: 390, height: 844 });
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  await page.screenshot({ path: test.info().outputPath('evidence-matrix-mobile.png'), fullPage: true });
  await page.keyboard.press('Tab');
  await expect(page.locator(':focus')).toBeVisible();
  expect(errors).toEqual([]);
});
