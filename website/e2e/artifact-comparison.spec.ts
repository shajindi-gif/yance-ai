import { expect, test } from '@playwright/test';

test('synthetic UI contract: compare saved versions and bind a version comment', async ({ page }) => {
  const artifact = (version: number, summary: string) => ({ id: `draft-${version}`, version, title: '合成工作稿', status: 'draft', generation_method: 'synthetic', checksum_sha256: 'abc', content: { executive_summary: summary }, source_snapshot: { profile: version === 3 ? 'v2' : 'v1' } });
  const comments: Array<{ id: string; artifact_id: string; body: string; created_at: string }> = [];
  const application = { id: 'synthetic', title: '合成项目', company_name: '合成企业', status: 'draft', review_status: 'pending', documents: [], requirements: [], activities: [], evidence: [], tasks: [], comments, generated: [artifact(3, '<script>window.injected=true</script>'), artifact(2, '旧摘要'), artifact(1, '初稿')], readiness: { blockers: [], can_submit_for_review: false } };
  const writes: string[] = [];
  await page.addInitScript(() => localStorage.setItem('yance_token', 'synthetic-contract-only'));
  await page.route('**/*', async route => {
    const url = new URL(route.request().url());
    if (!['localhost', '127.0.0.1'].includes(url.hostname)) return route.abort();
    if (url.pathname.startsWith('/api/')) {
      if (route.request().method() !== 'GET') {
        writes.push(url.pathname);
        const payload = route.request().postDataJSON();
        comments.push({ id: 'comment-1', artifact_id: payload.artifact_id, body: payload.body, created_at: '2026-10-23T00:00:00Z' });
      }
      const data = url.pathname.includes('/applications/') ? application : url.pathname.includes('/documents') ? [] : { id: 'synthetic', full_name: '合成用户', role: 'owner' };
      return route.fulfill({ json: data });
    }
    return route.continue();
  });
  await page.goto('/applications/synthetic');
  await page.getByRole('tab', { name: /工作稿/ }).click();
  const panel = page.getByRole('region', { name: '工作稿版本比较' });
  await expect(panel.getByRole('status')).toContainText('v2 → v3：1 项内容变化');
  await expect(panel.getByRole('status')).toContainText('来源快照已变化');
  await panel.getByText('摘要 · 已修改', { exact: true }).click();
  await expect(panel.getByText('旧摘要', { exact: false }).last()).toBeVisible();
  expect(await page.evaluate(() => (window as unknown as { injected?: boolean }).injected)).toBeUndefined();
  await panel.getByRole('combobox').selectOption('draft-1');
  await expect(panel.getByRole('status')).toContainText('v1 → v3');
  await page.setViewportSize({ width: 390, height: 844 });
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  expect(writes).toEqual([]);
  await page.getByRole('tab', { name: '动态', exact: true }).click();
  await page.getByRole('combobox', { name: '评论关联版本' }).selectOption('draft-1');
  await page.getByRole('textbox', { name: '添加协作评论' }).fill('复核初稿证据');
  await page.getByRole('button', { name: '发送', exact: true }).click();
  await expect(page.getByText('工作区成员 · 工作稿 v1', { exact: true })).toBeVisible();
  await expect(page.getByText('复核初稿证据', { exact: true })).toBeVisible();
  expect(writes).toEqual(['/api/v1/applications/synthetic/comments']);
});
