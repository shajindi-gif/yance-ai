/** Show safe server explanations without dumping validation inputs or objects. */
export function apiErrorMessage(detail: unknown, fallback: string): string {
  if (typeof detail === 'string' && detail.trim()) return detail;
  if (Array.isArray(detail)) {
    const messages = detail.flatMap(item => item && typeof item === 'object' && typeof item.msg === 'string' ? [item.msg] : []);
    return messages.slice(0, 3).join('；') || fallback;
  }
  if (detail && typeof detail === 'object') {
    const value = detail as Record<string, unknown>;
    if (typeof value.message === 'string' && value.message.trim()) return value.message;
    if (value.code === 'quota_exceeded') {
      const names: Record<string, string> = { generated_documents: '生成工作稿', reports: '报告', policy_scans: '政策扫描', companies: '企业', documents: '资料', users: '成员', agent_runs: '任务' };
      return `当前${names[String(value.meter)] || '操作'}额度不足，请在“用量与账单”查看剩余额度。`;
    }
  }
  return fallback;
}
