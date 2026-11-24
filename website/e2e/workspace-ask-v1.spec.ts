import {readFileSync} from 'node:fs';
import {expect, test} from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';

test.use({trace:'off', video:'off', screenshot:'off'});
for (const width of [390, 768, 1440]) {
  test(`real isolated Ask workspace, citations and old routes at ${width}px`, async ({page, baseURL}) => {
    test.skip(!process.env.YANCE_ASK_FIXTURE, 'Requires local synthetic fixture + offline model adapter');
    expect(new URL(baseURL!).hostname).toMatch(/^(localhost|127\.0\.0\.1)$/);
    const fixture = JSON.parse(readFileSync(process.env.YANCE_ASK_FIXTURE!, 'utf8')) as {token:string; application_id:string};
    await page.route('**/*', route => ['localhost','127.0.0.1'].includes(new URL(route.request().url()).hostname) ? route.continue() : route.abort());
    await page.addInitScript(token => localStorage.setItem('yance_token', token), fixture.token);
    await page.setViewportSize({width, height:1000});
    const errors: string[] = []; page.on('pageerror', error => errors.push(error.message));
    await page.goto('/dashboard');
    await expect(page.getByRole('heading', {name:'问衍策', exact:true})).toBeVisible();
    if (width <= 900) await page.getByRole('button', {name:'打开工作区导航'}).click();
    await expect(page.getByRole('navigation', {name:'工作区导航'}).getByRole('link')).toHaveCount(5);
    if (width <= 900) await page.locator('[data-drawer-close]').click();
    await page.getByRole('textbox', {name:'向衍策提问'}).fill('人工智能企业条件');
    await page.getByRole('button', {name:'发送问题', exact:true}).click();
    const quote = page.getByRole('button', {name:/查看引用 1/});
    await expect(quote).toBeVisible();
    await expect(page.getByText('回答已保存 · 请核对条款与企业证明', {exact:true})).toBeVisible();
    await page.screenshot({path:`../docs/workspace-ask-v1/ask-${width}.png`, fullPage:true});
    await quote.click();
    await expect(page.getByRole('dialog')).toBeVisible();
    await expect(page.getByRole('dialog').locator('mark')).toContainText('人工智能');
    await page.screenshot({path:`../docs/workspace-ask-v1/source-${width}.png`, fullPage:true});
    const accessibility = await new AxeBuilder({page}).withTags(['wcag2a','wcag2aa','wcag21aa','wcag22aa']).analyze();
    expect(accessibility.violations).toEqual([]);
    await page.keyboard.press('Escape');
    await expect(page.getByRole('dialog')).toHaveCount(0);
    await expect(quote).toBeFocused();
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
    for (const route of ['/tasks', '/agents']) {
      const response = await page.goto(route); expect(response?.status()).toBe(200);
    }
    await page.goto(`/applications/${fixture.application_id}`);
    await page.getByRole('tab', {name:'执行记录',exact:true}).click();
    await expect(page.getByRole('heading', {name:'执行记录',exact:true})).toBeVisible();
    expect(errors).toEqual([]);
  });
}
