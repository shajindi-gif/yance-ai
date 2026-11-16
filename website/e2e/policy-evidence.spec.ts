import {readFileSync} from 'node:fs';
import {test, expect} from '@playwright/test';

test('customer searches collected evidence and reads its immutable source version', async ({page, baseURL}) => {
  test.skip(!process.env.YANCE_V2_FIXTURE, 'Requires isolated database fixture');
  expect(new URL(baseURL!).hostname).toMatch(/^(localhost|127\.0\.0\.1)$/);
  const fixture = JSON.parse(readFileSync(process.env.YANCE_V2_FIXTURE!, 'utf8'));
  await page.route('**/*', route => ['localhost','127.0.0.1'].includes(new URL(route.request().url()).hostname) ? route.continue() : route.abort());
  await page.addInitScript(token => localStorage.setItem('yance_token', token), fixture.token);
  await page.goto('/discover');
  await page.getByLabel('政策原文关键词').fill('合成');
  await page.getByRole('button', {name:'检索原文', exact:true}).click();
  const read = page.getByRole('button', {name:'查看对应版本原文'}).first();
  await expect(read).toBeVisible();
  await read.click();
  await expect(page.getByText('对应版本完整原文', {exact:true})).toBeVisible();
  await expect(page.locator('details[open]')).toContainText('合成');
  const search = page.locator('section[aria-labelledby="evidence-search-heading"]');
  await page.route('**/policies/evidence-search?**', route => route.fulfill({status:503,json:{detail:'测试中断'}}));
  await search.getByRole('button',{name:'检索原文',exact:true}).click();
  await expect(search.getByRole('alert')).toBeVisible();
  await expect(search.getByRole('status')).toBeEmpty();
  await expect(search.getByLabel('政策原文关键词')).toHaveValue('合成');
  await page.unroute('**/policies/evidence-search?**');
  await search.getByRole('button',{name:'检索原文',exact:true}).click();
  await expect(read).toBeVisible();
  await page.setViewportSize({width:390,height:844});
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
});
