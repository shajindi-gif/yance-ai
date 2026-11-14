import { chromium, expect } from '../../../website/node_modules/@playwright/test/index.mjs';
import { readFile, writeFile } from 'node:fs/promises';
const base = process.env.PLAYWRIGHT_BASE_URL || 'http://127.0.0.1:3038';
if (new URL(base).hostname !== '127.0.0.1')
    throw new Error('Local target required');
const data = JSON.parse(await readFile(process.env.YANCE_DETAILS_FIXTURE, 'utf8'));
const other = JSON.parse(await readFile(process.env.YANCE_CHECKOUT_FIXTURE, 'utf8'));
const output = new URL('./', import.meta.url).pathname;
const routes = [['company', `/companies/${data.company_id}`, `/companies/${data.company_id}`, data.token], ['opportunity', `/opportunities/${data.opportunity_id}`, `/opportunities/${data.opportunity_id}`, data.token], ['task', `/tasks/${data.task_id}`, `/tasks/${data.task_id}`, data.token], ['agent', `/agents/${data.agent_run_id}`, `/agent-runs/${data.agent_run_id}`, data.token], ['eval', `/admin/evals/${data.eval_run_id}`, `/admin/evals/runs/${data.eval_run_id}`, data.admin_token]];
const browser = await chromium.launch();
const checks = [];
try {
    for (const [name, path, api, token] of routes) {
        const context = await browser.newContext();
        await context.route('**/*', r => new URL(r.request().url()).hostname === '127.0.0.1' ? r.continue() : r.abort());
        await context.addInitScript(t => localStorage.setItem('yance_token', t), token);
        const page = await context.newPage();
        const allowed = await context.request.get(base + '/api/v1' + api, { headers: { Authorization: 'Bearer ' + token } });
        expect(allowed.status(), name).toBe(200);
        const denied = await context.request.get(base + '/api/v1' + api, { headers: { Authorization: 'Bearer ' + (name === 'eval' ? data.token : other.token) } });
        expect([403, 404], name).toContain(denied.status());
        for (const width of [390, 768, 1440]) {
            await page.setViewportSize({ width, height: 900 });
            await page.goto(base + path);
            await expect(page.locator('main h1').first()).toBeVisible();
            const overflow = await page.evaluate(() => document.documentElement.scrollWidth > innerWidth);
            if (overflow)
                console.log(name, width, await page.evaluate(() => [...document.querySelectorAll('main *')].filter(e => e.getBoundingClientRect().right > innerWidth + 1).slice(0, 12).map(e => ({ tag: e.tagName, cls: e.className, width: e.getBoundingClientRect().width }))));
            expect(overflow).toBe(false);
            await page.screenshot({ path: output + `${name}-${width}.png` });
            checks.push({ name, width, allowed: allowed.status(), denied: denied.status(), overflow: false });
        }
        await context.close();
    }
    await writeFile(output + 'details-results.json', JSON.stringify(checks, null, 2));
    console.log('15 detail viewport checks and 5 authorization checks passed');
}
finally {
    await browser.close();
}
