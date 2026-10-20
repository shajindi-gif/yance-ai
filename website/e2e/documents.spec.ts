import { expect, test } from '@playwright/test';

test('authenticated documents workspace renders the verified ingestion controls', async ({
  page,
  request,
}) => {
  const apiBase =
    process.env.PLAYWRIGHT_API_BASE_URL ||
    process.env.NEXT_PUBLIC_API_URL ||
    'http://127.0.0.1:8011/api/v1';
  const suffix = `${Date.now()}-${Math.random().toString(16).slice(2)}`;
  const companyName = `Browser Document Company ${suffix}`;
  const registration = await request.post(`${apiBase}/auth/register`, {
    data: {
      company_name: companyName,
      industry: '人工智能',
      province: '上海市',
      city: '上海市',
      owner_email: `browser-document-${suffix}@example.com`,
      owner_name: 'Browser Owner',
      owner_password: 'browser-integration-password-123',
      agreed_terms_version: 'test-terms',
    },
  });
  expect(registration.ok()).toBeTruthy();
  const { access_token: token } = await registration.json();
  await page.addInitScript((value) => localStorage.setItem('yance_token', value), token);

  const failedResponses: string[] = [];
  page.on('requestfailed', (request) => failedResponses.push(`NETWORK ${request.url()}`));
  page.on('response', (response) => {
    if (response.status() >= 400) failedResponses.push(`${response.status()} ${response.url()}`);
  });
  await page.goto('/documents');
  await expect(page.getByRole('heading', { name: '企业资料' })).toBeVisible();
  await expect(page.getByLabel('所属企业')).toContainText(companyName);
  await expect(page.getByLabel('选择文件')).toHaveAttribute(
    'accept',
    '.pdf,.docx,.xlsx,.csv,.txt',
  );
  await expect(page.getByRole('button', { name: '上传资料' })).toBeDisabled();
  await expect(page.getByLabel('或从公开网页导入')).toHaveAttribute('type', 'url');
  await expect(page.getByRole('button', { name: '导入网页' })).toBeDisabled();
  await expect(page.getByText('暂无资料')).toBeVisible();
  await expect(page.getByText(/扫描版 PDF 会进入受限 OCR 流程/)).toBeVisible();
  await expect(page.getByText(/仅允许公开 HTTPS 地址/)).toBeVisible();
  expect(failedResponses).toEqual([]);
  await expect(
    page.locator('[data-nextjs-dialog], .vite-error-overlay, #webpack-dev-server-client-overlay'),
  ).toHaveCount(0);
});
