import { chromium, expect } from '../../../website/node_modules/@playwright/test/index.mjs';
import { readFile, writeFile, readdir } from 'node:fs/promises';

const base = process.env.PLAYWRIGHT_BASE_URL || 'http://127.0.0.1:3038';
if (new URL(base).hostname !== '127.0.0.1') throw new Error('Local target required');
const fixture = JSON.parse(await readFile(process.env.YANCE_DETAILS_FIXTURE, 'utf8'));
const root = new URL('../../../website/app/', import.meta.url);
const output = new URL('./', import.meta.url);
const browser = await chromium.launch();
const results = [];
try {
    const context = await browser.newContext();
    await context.route('**/*', route => new URL(route.request().url()).hostname === '127.0.0.1' ? route.continue() : route.abort());
    const page = await context.newPage();
    const pageErrors = [];
    page.on('pageerror', error => pageErrors.push(error.message));
    await page.goto(base);
    for (const file of await readdir(root, { recursive: true })) {
        if (!file.endsWith('page.tsx')) continue;
        let path = '/' + file.replace(/\/?page.tsx$/, '');
        const ids = {
            '[applicationId]': fixture.application_id,
            '[companyId]': fixture.company_id,
            '[opportunityId]': fixture.opportunity_id,
            '[taskId]': fixture.task_id,
            '[runId]': path.startsWith('/admin') ? fixture.eval_run_id : fixture.agent_run_id,
        };
        for (const [placeholder, id] of Object.entries(ids)) path = path.replace(placeholder, id);
        await page.evaluate(token => localStorage.setItem('yance_token', token), path.startsWith('/admin') ? fixture.admin_token : fixture.token);
        for (const width of [390, 768, 1440]) {
            await page.setViewportSize({ width, height: 900 });
            const response = await page.goto(base + path);
            expect(response.status(), path).toBe(200);
            await expect(page.locator('h1').first(), path).toBeVisible();
            const overflow = await page.evaluate(() => document.documentElement.scrollWidth > innerWidth);
            results.push({ base, file, path, width, http: response.status(), overflow });
            expect(overflow, `${path} at ${width}`).toBe(false);
            expect(pageErrors, path).toEqual([]);
            if (['/', '/discover', '/orders', '/login'].includes(path)) {
                await page.screenshot({ path: new URL(`final-${path === '/' ? 'home' : path.slice(1)}-${width}.png`, output).pathname });
            }
        }
    }
    await writeFile(new URL('all-pages-results.json', output), JSON.stringify(results, null, 2));
    console.log(`${results.length} route and viewport checks passed`);
} finally {
    await browser.close();
}
