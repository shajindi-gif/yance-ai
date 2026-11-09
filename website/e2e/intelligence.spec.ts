import {readFileSync} from 'node:fs';
import {test,expect} from '@playwright/test';

test.beforeEach(async ({page,baseURL})=>{
  expect(new URL(baseURL!).hostname).toBe('127.0.0.1');
  await page.route('**/*',r=>new URL(r.request().url()).hostname==='127.0.0.1'?r.continue():r.abort());
});

test('transaction review keeps draft text in this page and totals the current list',async({page})=>{
  await page.goto('/');
  await page.getByRole('link',{name:'交易审查',exact:true}).click();
  await page.getByLabel('采购文件原文').fill('须提供资质。验收后结算。');
  await expect(page.locator('dd').filter({hasText:'须提供资质'})).toBeVisible();
  await page.getByRole('button',{name:'合同条款'}).click();
  await page.getByLabel('合同条款原文').fill('付款期限由双方确认。');
  await expect(page.locator('dd').filter({hasText:'付款期限'})).toBeVisible();
  await page.getByRole('button',{name:'应收账款'}).click();
  await page.getByLabel('合同或项目简称').fill('合成合同');
  await page.getByLabel('约定到期日').fill('2027-01-01');
  await page.getByLabel('应收总额').fill('500.10');
  await page.getByLabel('累计实收').fill('600');
  await expect(page.getByRole('button',{name:'加入本次清单'})).toBeDisabled();
  await page.getByLabel('累计实收').fill('299.99');
  await page.getByRole('button',{name:'加入本次清单'}).click();
  await expect(page.getByText('合计待收 ¥200.11')).toBeVisible();
  await expect(page.getByRole('button',{name:'加入本次清单'})).toBeDisabled();
  await page.getByRole('button',{name:'地区规则'}).click();
  await page.getByLabel('地区一的规则与来源').fill('合成条款甲');
  await page.getByLabel('地区二的规则与来源').fill('合成条款乙');
  await page.getByRole('button',{name:'采购文件',exact:true}).click();
  await expect(page.getByLabel('采购文件原文')).toHaveValue('须提供资质。验收后结算。');
  for(const width of [390,768,1440]){
    await page.setViewportSize({width,height:900});
    expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
  }
});

test('industry sample is retrieved from the authenticated local evidence API',async({page})=>{
  test.skip(!process.env.YANCE_V2_FIXTURE,'Requires local synthetic fixture');
  const data=JSON.parse(readFileSync(process.env.YANCE_V2_FIXTURE!,'utf8'));
  await page.addInitScript(t=>localStorage.setItem('yance_token',t),data.token);
  await page.goto('/intelligence#industry');
  await page.getByLabel('产业关键词').fill('合成');
  await page.getByRole('button',{name:'查看地域分布'}).click();
  await expect(page.locator('#industry [role=status]')).toContainText(/命中 [1-9]/);
  await expect(page.locator('#industry ul').first().getByRole('listitem').first()).toContainText('份');
});
