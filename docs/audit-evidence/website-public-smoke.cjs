const { chromium, expect } = require('../../website/node_modules/@playwright/test');
const fs = require('node:fs');
(async () => {
  const base = process.env.YANCE_SMOKE_BASE;
  if (!base) throw new Error('YANCE_SMOKE_BASE required');
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({ viewport: { width: 1440, height: 1000 } });
  const page = await context.newPage();
  const failures = [], errors = [], timings = [], blockedMethods = [];
  await context.route('**/*', async route => {
    const method = route.request().method();
    if (!['GET', 'HEAD', 'OPTIONS'].includes(method)) {
      blockedMethods.push(method);
      return route.fulfill({ status: 204 });
    }
    if (process.env.YANCE_CANDIDATE_ORIGIN && new URL(route.request().url()).hostname === 'api.yance.ai') {
      const response = await route.fetch({ headers: { ...route.request().headers(), origin: 'https://yance.ai' }, maxRetries: 2 });
      return route.fulfill({ response, headers: { ...response.headers(), 'access-control-allow-origin': base } });
    }
    return route.continue();
  });
  page.on('pageerror', error => errors.push(error.message));
  page.on('response', response => {
    if (response.status() >= 400) failures.push({ path: new URL(response.url()).pathname, status: response.status() });
  });
  const version = await context.request.get(`${process.env.YANCE_CANDIDATE_ORIGIN || base}/release.json`);
  expect(version.status()).toBe(200);
  expect((await version.json()).release).toBe('web-20261020-01');
  for (const path of ['/', '/pricing', '/login', '/security', '/policy-knowledge-base']) {
    console.log("Checking", path);
    const started = Date.now();
    const response = await page.goto(`${base}${path}`, { waitUntil: 'domcontentloaded', timeout: 60000 });
    expect(response.status()).toBe(200);
    await expect(page.locator('h1').first()).toBeVisible();
    if (path === '/') {
      await expect(page.locator('footer a', { hasText: '申报工作台' })).toBeVisible();
      await page.screenshot({ path: `${process.env.YANCE_SMOKE_OUT}-home.png`, fullPage: true });
    }
    if (path === '/pricing') await expect(page.locator('.pricing-card').first()).toBeVisible({ timeout: 20000 });
    if (path === '/login') await expect(page.locator('form input[type=email]').first()).toBeVisible();
    timings.push({ path, navigationAndVisibleContentMs: Date.now() - started });
  }
  expect(failures).toEqual([]);
  expect(errors).toEqual([]);
  const result = { at: new Date().toISOString(), base, candidateOrigin: process.env.YANCE_CANDIDATE_ORIGIN || null, release: 'web-20261020-01', status: 'passed', checks: timings, failures, errors, blockedMethods, sample: 'one desktop Chromium visit per page; no throttling; not SLA', productionBusinessWrites: false };
  fs.writeFileSync(`${process.env.YANCE_SMOKE_OUT}.json`, JSON.stringify(result, null, 2));
  console.log(JSON.stringify(result, null, 2));
  await browser.close();
})().catch(error => { console.error(error); process.exit(1); });
