/** Deterministic structural comparison; no model calls or content interpretation. */
function canonical(value: unknown): string {
  if (value === undefined) return '（字段不存在）';
  if (value === null) return 'null';
  if (Array.isArray(value)) return `[${value.map(canonical).join(',')}]`;
  if (typeof value === 'object') return `{${Object.entries(value as Record<string, unknown>).sort(([a], [b]) => a.localeCompare(b)).map(([key, item]) => `${JSON.stringify(key)}:${canonical(item)}`).join(',')}}`;
  return JSON.stringify(value);
}

const labels: Record<string, string> = {
  title: '标题', executive_summary: '摘要', company_name: '企业', eligibility: '资格判断',
  criteria: '资格条件', requirements: '材料清单', evidence: '政策证据', disclaimer: '使用说明',
};

export function compareArtifactContent(before: Record<string, unknown>, after: Record<string, unknown>) {
  return [...new Set([...Object.keys(before), ...Object.keys(after)])].sort().flatMap(key => {
    const oldValue = canonical(before[key]);
    const newValue = canonical(after[key]);
    return oldValue === newValue ? [] : [{ key, label: labels[key] || key, before: oldValue, after: newValue }];
  });
}
