import { readFileSync } from 'node:fs';
import { expect, test } from '@playwright/test';

test.use({trace:'off',video:'off',screenshot:'off'});
test.beforeEach(async ({page,baseURL}) => {
  expect(new URL(baseURL!).hostname).toMatch(/^(localhost|127\.0\.0\.1)$/);
  await page.route('**/*', route => ['localhost','127.0.0.1'].includes(new URL(route.request().url()).hostname) ? route.continue() : route.abort());
});
const fixture = () => JSON.parse(readFileSync(process.env.YANCE_ROLES_FIXTURE!, 'utf8')) as {token:string;application_id:string};

test('public design: real product image, readable mobile menu, focus containment and Escape',async ({page}) => {
  await page.setViewportSize({width:390,height:844});
  await page.emulateMedia({reducedMotion:'reduce'});
  await page.goto('/');
  await expect(page.getByRole('heading',{level:1})).toContainText('找到有依据的');
  const image = page.getByRole('img',{name:/隔离合成项目的真实资格矩阵/});
  await image.scrollIntoViewIfNeeded();
  await expect(image).toBeVisible();
  await expect.poll(() => image.evaluate((node:HTMLImageElement) => node.naturalWidth)).toBeGreaterThan(0);
  const toggle=page.getByRole('button',{name:'打开菜单',exact:true});
  await toggle.click();
  const menu=page.getByRole('navigation',{name:'移动端导航'});
  await expect(menu.getByRole('button',{name:'关闭菜单 ×'})).toBeFocused();
  await page.keyboard.press('Shift+Tab');
  await expect(menu.getByRole('link',{name:'免费开始'})).toBeFocused();
  await page.keyboard.press('Tab');
  await expect(menu.getByRole('button',{name:'关闭菜单 ×'})).toBeFocused();
  await page.keyboard.press('Escape');
  await expect(menu).toBeHidden();
  await expect(page.getByRole('button',{name:'打开菜单',exact:true})).toBeFocused();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  expect(await page.evaluate(() => getComputedStyle(document.documentElement).scrollBehavior)).toBe('auto');
});

test('pricing error recovers into the real server catalogue without a purchase',async ({page}) => {
  let first=true;
  await page.route('**/api/v1/products',route => { if(first){first=false;return route.fulfill({status:503,json:{detail:'Synthetic outage'}});}return route.continue(); });
  await page.goto('/pricing');
  await expect(page.getByRole('alert').filter({hasText:'当前无法读取'})).toContainText('当前无法读取');
  await page.getByRole('button',{name:'重新加载产品目录'}).click();
  await expect(page.locator('.pricing-card').first()).toBeVisible();
  await expect(page.getByRole('alert').filter({hasText:'当前无法读取'})).toHaveCount(0);
});

test('real workspace: keyboard tabs, unsaved edit protection and mobile navigation',async ({page}) => {
  test.skip(!process.env.YANCE_ROLES_FIXTURE,'Requires isolated synthetic fixture');
  const data=fixture();
  await page.addInitScript(token => localStorage.setItem('yance_token',token),data.token);
  await page.goto(`/applications/${data.application_id}`);
  const first=page.getByRole('tab',{name:'资格矩阵',exact:true});
  await first.focus();
  await page.keyboard.press('ArrowRight');
  await expect(page.getByRole('tab',{name:'项目概览',exact:true})).toBeFocused();
  await expect(page.getByRole('tabpanel')).toHaveAttribute('aria-labelledby','application-tab-overview');
  await page.keyboard.press('End');
  await expect(page.getByRole('tab',{name:'动态',exact:true})).toBeFocused();
  await page.getByRole('textbox',{name:'添加协作评论'}).fill('尚未保存的合成意见');
  let protectedNavigation=false;
  page.once('dialog',async dialog => {protectedNavigation=true;await dialog.dismiss();});
  await page.getByRole('link',{name:'返回列表',exact:true}).click();
  expect(protectedNavigation).toBe(true);
  await expect(page).toHaveURL(new RegExp(`/applications/${data.application_id}$`));
  await expect(page.getByRole('textbox',{name:'添加协作评论'})).toHaveValue('尚未保存的合成意见');
  await page.getByRole('textbox',{name:'添加协作评论'}).fill('');
  await page.setViewportSize({width:390,height:844});
  await page.getByRole('button',{name:'打开工作区导航'}).click();
  await expect(page.getByRole('button',{name:'关闭工作区导航'}).first()).toBeFocused();
  await page.keyboard.press('Escape');
  await expect(page.getByRole('button',{name:'打开工作区导航'})).toBeFocused();
  await first.click();
  const table=page.getByRole('region',{name:'可横向滚动的数据表'});
  await table.focus();
  await expect(table).toBeFocused();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
});

test('real workspace route sweep preserves existing core and billing entrances on mobile',async ({page}) => {
  test.skip(!process.env.YANCE_ROLES_FIXTURE,'Requires isolated synthetic fixture');
  const data=fixture();
  await page.addInitScript(token => localStorage.setItem('yance_token',token),data.token);
  await page.setViewportSize({width:390,height:844});
  const errors:string[]=[];
  page.on('pageerror',error => errors.push(error.message));
  for(const path of ['/dashboard','/companies','/discover','/opportunities','/applications','/projects','/documents','/reports','/orders','/billing','/team','/settings','/tasks','/agents','/notifications']) {
    const response=await page.goto(path);
    expect(response?.status(),path).toBe(200);
    await expect(page.locator('main h1').first()).toBeVisible();
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth),path).toBe(true);
  }
  expect(errors).toEqual([]);
});

test('real isolated workflow: customer reviews a source-bound version, then downloads DOCX',async ({page}) => {
  test.skip(!process.env.YANCE_ROLES_FIXTURE,'Requires isolated synthetic fixture');
  const data=JSON.parse(readFileSync(process.env.YANCE_ROLES_FIXTURE!, 'utf8')) as {export_token:string;export_application_id:string};
  test.skip(!data.export_token,'Requires the guarded review/export fixture');
  await page.addInitScript(token => localStorage.setItem('yance_token',token),data.export_token);
  await page.goto(`/applications/${data.export_application_id}`);
  await page.getByRole('button',{name:'开始准备',exact:true}).click();
  await expect(page.getByRole('button',{name:'提交复核',exact:true})).toBeEnabled();
  await page.getByRole('button',{name:'提交复核',exact:true}).click();
  await page.getByRole('tab',{name:/工作稿/}).click();
  await page.getByRole('button',{name:'批准工作稿',exact:true}).click();
  await expect(page.getByText('approved',{exact:true})).toBeVisible();
  const result=page.waitForResponse(response => response.url().includes('/download?format=docx'));
  const download=page.waitForEvent('download');
  await page.getByRole('button',{name:'DOCX',exact:true}).click();
  expect((await result).status()).toBe(200);
  const file=await download;
  expect(file.suggestedFilename()).toMatch(/\.docx$/);
  const detail=await page.request.get(`/api/v1/applications/${data.export_application_id}`,{headers:{Authorization:`Bearer ${data.export_token}`}});
  const record=await detail.json();
  expect(record.status).toBe('review');
  expect(record.generated[0].status).toBe('approved');
  expect(record.generated[0].content.disclaimer).toContain('客户本人或其授权团队成员');
});

test('login and registration fields expose their visible Chinese labels',async ({page}) => {
  await page.goto('/login');
  await expect(page.getByLabel('邮箱',{exact:true})).toBeVisible();
  await expect(page.getByLabel('密码',{exact:true})).toHaveAttribute('autocomplete','current-password');
  await page.getByRole('button',{name:'免费注册',exact:true}).click();
  await expect(page.getByLabel('企业全称',{exact:false})).toBeVisible();
  await expect(page.getByLabel('行业',{exact:true})).toBeVisible();
  await expect(page.getByLabel('联系人姓名',{exact:false})).toBeVisible();
  await expect(page.getByLabel('工作邮箱',{exact:false})).toHaveAttribute('autocomplete','email');
  await expect(page.getByLabel('密码',{exact:false})).toHaveAttribute('autocomplete','new-password');
});
