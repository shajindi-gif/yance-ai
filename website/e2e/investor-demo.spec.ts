import { expect, test } from '@playwright/test';

test('investor demo proves the persisted evidence-first workflow and downloads a deliverable', async ({
  page,
}) => {
  const failedResponses: string[] = [];
  page.on('response', (response) => {
    if (response.status() >= 400) failedResponses.push(`${response.status()} ${response.url()}`);
  });

  await page.goto('/demo');
  await expect(page.getByRole('heading', { name: /AI 完成一次企业政策与申报工作/ })).toBeVisible();
  await expect(page.getByText('DEMO · SYNTHETIC')).toBeVisible();
  await expect(page.getByText(/所有公司、政策、机构、权益和结果均为 DEMO 示例/)).toBeVisible();
  await expect(page.getByText('Workflow').locator('..').getByText('7 / 7')).toBeVisible();

  const stages = [
    'Company Intelligence',
    'Policy / Opportunity Scan',
    '四态资格判断',
    'Evidence Engine',
    'Application Workspace',
    '版本化交付物',
  ];
  for (const title of stages) {
    await page.getByRole('button', { name: '继续演示' }).click();
    await expect(page.getByRole('heading', { name: new RegExp(title) })).toBeVisible();
    if (title === 'Evidence Engine') {
      await expect(page.getByText('Exact span verified')).toBeVisible();
    }
  }

  await expect(page.getByText('Agent Run')).toBeVisible();
  await expect(page.getByText(/deterministic demo/)).toBeVisible();

  const downloadPromise = page.waitForEvent('download');
  await page.getByRole('button', { name: '下载 DOCX' }).click();
  const download = await downloadPromise;
  expect(download.suggestedFilename()).toMatch(/^demo-.+\.docx$/);
  expect(failedResponses).toEqual([]);
});
