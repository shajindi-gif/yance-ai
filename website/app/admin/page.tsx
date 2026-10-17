"use client";

import Link from "next/link";
import { useCallback, useEffect, useRef, useState } from "react";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { ButtonLink } from "@/components/ui/ButtonLink";
import { DataTable } from "@/components/ui/DataTable";
import { EmptyState } from "@/components/ui/EmptyState";
import { InlineAlert } from "@/components/ui/InlineAlert";
import { LoadingState } from "@/components/ui/LoadingState";
import { PageHeader } from "@/components/ui/PageHeader";
import AppShell from "@/components/workspace/AppShell";
import styles from "@/components/workspace/AdminDashboard.module.css";
import type { AdminInvoicePage, AdminOverview, AdminResourcePage } from "@/lib/api";
import api from "@/lib/api";

const RESOURCES = [
  ["users", "Users"], ["organizations", "Organizations"], ["companies", "Companies"],
  ["agent_runs", "Agent Runs"], ["workflow_runs", "Workflow Runs"], ["llm_usage", "LLM Usage"],
  ["costs", "Costs"], ["documents", "Documents"], ["policies", "Policies"],
  ["document_ingestion_runs", "Document Ingestion"],
  ["evals", "Evals"], ["errors", "Errors"], ["billing", "Billing"],
  ["invoices", "发票待办"],
  ["feedback", "Feedback"], ["analytics", "Analytics"],
] as const;

type Resource = typeof RESOURCES[number][0];

const COLUMNS: Record<Resource, string[]> = {
  users: ["email", "full_name", "role", "is_active", "is_platform_admin", "tenant_id", "created_at"],
  organizations: ["name", "slug", "account_stage", "is_active", "id", "created_at"],
  companies: ["name", "industry", "province", "tenant_id", "created_at"],
  agent_runs: ["agent_name", "status", "model", "total_tokens", "cost_usd", "latency_ms", "tenant_id", "created_at"],
  workflow_runs: ["status", "current_step", "cost_usd", "latency_ms", "error_code", "tenant_id", "created_at"],
  llm_usage: ["agent_name", "model", "total_tokens", "cost_usd", "latency_ms", "tenant_id", "created_at"],
  costs: ["agent_name", "model", "cost_usd", "total_tokens", "tenant_id", "created_at"],
  documents: ["filename", "content_type", "size_bytes", "status", "ingestion_status", "tenant_id", "created_at"],
  document_ingestion_runs: ["document_id", "attempt", "status", "parser_version", "error_code", "safe_message", "metrics", "tenant_id", "created_at"],
  policies: ["title", "issuing_authority", "jurisdiction", "status", "tenant_id", "created_at"],
  evals: ["eval_type", "status", "target_key", "target_version", "scorer_version", "requested_cases", "passed_cases", "error_cases", "release_gate_passed", "created_at"],
  errors: ["code", "category", "safe_message", "retryable", "agent_run_id", "tenant_id", "occurred_at"],
  billing: ["order_no", "product_code", "amount", "currency", "status", "tenant_id", "created_at"],
  invoices: ["invoice_no", "title", "tax_number", "total_amount", "invoice_type", "status", "voucher_filename", "tenant_id", "created_at"],
  feedback: ["category", "message", "route", "status", "tenant_id", "created_at"],
  analytics: ["name", "source", "event_key", "request_id", "tenant_id", "occurred_at"],
};

const STAGES = ["unclassified", "poc", "customer", "churned", "internal"];
const FEEDBACK_STATES = ["open", "reviewing", "resolved", "dismissed"];

function displayValue(value: unknown): string {
  if (value == null || value === "") return "—";
  if (typeof value === "boolean") return value ? "Yes" : "No";
  if (typeof value === "number") return String(value);
  if (typeof value === "string" && /^\d{4}-\d{2}-\d{2}T/.test(value)) {
    return new Date(value).toLocaleString("zh-CN");
  }
  if (typeof value === "object") return JSON.stringify(value);
  return String(value);
}

function InvoiceQueue() {
  const [items, setItems] = useState<AdminInvoicePage["items"]>([]);
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const filesRef = useRef<Record<string, File | null>>({});
  const reload = useCallback(() => {
    api.getAdminInvoices("requested").then((page) => setItems(page.items)).catch(() => undefined);
  }, []);
  useEffect(reload, [reload]);
  const issue = async (id: string) => {
    const file = filesRef.current[id];
    if (!file) { setError("请先选择从电子税务局下载的数电票文件（PDF/OFD 截图）"); return; }
    setBusy(id); setError(""); setNotice("");
    try {
      await api.issueInvoice(id, file);
      setNotice(`发票 ${id.slice(0, 8)}… 已开具，用户会收到站内通知和邮件。`);
      reload();
    } catch (e) { setError(e instanceof Error ? e.message : "开具失败"); }
    finally { setBusy(null); }
  };
  const reject = async (id: string) => {
    const reason = window.prompt("驳回原因（会展示给用户）", "请核对抬头与税号后重新申请");
    if (!reason) return;
    setBusy(id); setError("");
    try { await api.rejectInvoice(id, reason); reload(); }
    catch (e) { setError(e instanceof Error ? e.message : "驳回失败"); }
    finally { setBusy(null); }
  };
  return <section className={styles.panel}>
    <div className={styles.panelHeader}><div><h2>数电票开具待办</h2><p>流程：用户在账单页申请 → 你在电子税务局开票 → 在此上传发票文件并开具（自动通知用户）。</p></div><Badge tone={items.length ? "warning" : "success"}>{items.length ? `${items.length} 待处理` : "无待办"}</Badge></div>
    {error ? <InlineAlert tone="error">{error}</InlineAlert> : null}
    {notice ? <InlineAlert tone="info">{notice}</InlineAlert> : null}
    {items.length ? <ul style={{ listStyle: "none", padding: 0, margin: 0, display: "grid", gap: 10 }}>
      {items.map((inv) => <li key={inv.id} style={{ display: "flex", flexWrap: "wrap", alignItems: "center", gap: 10, padding: "10px 12px", border: "1px solid #e2e8f0", borderRadius: 10 }}>
        <strong>{inv.title}</strong>
        <span className={styles.muted}>{inv.tax_number} · ¥{inv.total_amount.toFixed(2)} · {inv.invoice_no} · {new Date(inv.created_at).toLocaleString("zh-CN")}</span>
        <span style={{ marginLeft: "auto", display: "flex", alignItems: "center", gap: 8 }}>
          <input type="file" accept=".pdf,.ofd,.png,.jpg,.jpeg" aria-label={`选择 ${inv.title} 的发票文件`} onChange={(e) => { filesRef.current[inv.id] = e.target.files?.[0] || null; }} />
          <Button type="button" disabled={busy === inv.id} onClick={() => issue(inv.id)}>{busy === inv.id ? "处理中…" : "上传并开具"}</Button>
          <Button type="button" variant="secondary" disabled={busy === inv.id} onClick={() => reject(inv.id)}>驳回</Button>
        </span>
      </li>)}
    </ul> : <EmptyState icon="✓" title="暂无开票申请" description="用户提交申请后会出现在这里。" />}
  </section>;
}

export default function AdminPage() {
  const [overview, setOverview] = useState<AdminOverview | null>(null);
  const [resource, setResource] = useState<Resource>("users");
  const [page, setPage] = useState<AdminResourcePage | null>(null);
  const [loading, setLoading] = useState(true);
  const [resourceLoading, setResourceLoading] = useState(false);
  const [error, setError] = useState("");

  const loadResource = useCallback(async (next: Resource, offset: number = 0) => {
    setResourceLoading(true);
    setError("");
    try {
      const result = await api.getAdminResource(next, offset);
      setResource(next);
      setPage(result);
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : "后台资源读取失败");
    } finally {
      setResourceLoading(false);
    }
  }, []);

  const refreshOverview = useCallback(async () => {
    const result = await api.getAdminOverview();
    setOverview(result);
  }, []);

  useEffect(() => {
    if (!api.isAuthenticated()) {
      setError("请先登录平台管理员账号。");
      setLoading(false);
      return;
    }
    Promise.all([api.getAdminOverview(), api.getAdminResource("users")])
      .then(([overviewResult, resourceResult]) => {
        setOverview(overviewResult);
        setPage(resourceResult);
      })
      .catch((loadError) => {
        setError(loadError instanceof Error ? loadError.message : "平台管理后台加载失败");
      })
      .finally(() => setLoading(false));
  }, []);

  const mutateRow = async (operation: () => Promise<void>) => {
    setResourceLoading(true);
    setError("");
    try {
      await operation();
      await Promise.all([loadResource(resource, page?.offset || 0), refreshOverview()]);
    } catch (mutationError) {
      setError(mutationError instanceof Error ? mutationError.message : "更新失败");
      setResourceLoading(false);
    }
  };

  if (loading) return <AppShell><LoadingState label="正在读取平台运营数据" /></AppShell>;
  if (!overview) {
    return <AppShell><PageHeader eyebrow="Platform Admin" title="无法访问管理后台" description="该页面仅限明确授权的平台管理员。租户 Owner/Admin 不自动获得平台权限。" />{error ? <InlineAlert tone="error">{error}</InlineAlert> : null}<ButtonLink href="/dashboard" variant="secondary">返回工作台</ButtonLink></AppShell>;
  }

  const totals = overview.totals;
  const maxRuns = Math.max(1, ...overview.agent_trend_30d.map((point) => point.runs));
  const columns = COLUMNS[resource];

  return <AppShell>
    <PageHeader eyebrow="Platform Admin" title="运营控制台" description={`全平台服务端记录 · 刷新于 ${new Date(overview.generated_at).toLocaleString("zh-CN")}`} actions={<><ButtonLink href="/admin/evals" variant="secondary">Eval Dashboard</ButtonLink><ButtonLink href="/admin/investor-metrics">Investor Metrics</ButtonLink></>} />
    {error ? <InlineAlert tone="error">{error}</InlineAlert> : null}

    <div className={styles.metricGrid}>
      <div className={styles.metricCard}><strong>{totals.organizations}</strong><span>Organizations</span><small>tenants</small></div>
      <div className={styles.metricCard}><strong>{totals.active_users_30d}</strong><span>Active Users</span><small>30-day server events</small></div>
      <div className={styles.metricCard}><strong>{totals.agent_runs}</strong><span>Agent Runs</span><small>{totals.failed_runs} failed</small></div>
      <div className={styles.metricCard}><strong>{totals.applications}</strong><span>Applications</span><small>persisted workspaces</small></div>
      <div className={styles.metricCard}><strong>{totals.paying_customers}</strong><span>Paying Customers</span><small>paid-order tenants</small></div>
      <div className={styles.metricCard}><strong>${totals.llm_cost_usd.toFixed(4)}</strong><span>LLM Cost</span><small>persisted Agent Runs</small></div>
    </div>

    <div className={styles.twoColumn}>
      <section className={styles.panel}>
        <div className={styles.panelHeader}><div><h2>Agent Runs · 30 days</h2><p>Daily persisted run volume; red bars contain failures.</p></div><Badge tone="neutral">UTC</Badge></div>
        <div className={styles.trend} aria-label="30-day Agent Run trend">
          {overview.agent_trend_30d.map((point) => <span key={point.date} className={`${styles.trendBar} ${point.failed ? styles.trendBarFailed : ""}`} style={{ height: `${Math.max(point.runs ? 8 : 1, point.runs / maxRuns * 100)}%` }} data-label={`${point.date}: ${point.runs} runs, ${point.failed} failed`} />)}
        </div>
      </section>
      <section className={styles.panel}>
        <div className={styles.panelHeader}><div><h2>System Health</h2><p>{new Date(overview.system_health.checked_at).toLocaleString("zh-CN")}</p></div><Badge tone={overview.system_health.database === "ready" ? "success" : "danger"}>{overview.system_health.database}</Badge></div>
        <dl className={styles.healthList}>
          <div><dt>Agent queue</dt><dd>{overview.system_health.agent_queue.queued}</dd></div>
          <div><dt>Running / stale</dt><dd>{overview.system_health.agent_queue.running} / {overview.system_health.agent_queue.stale_running}</dd></div>
          <div><dt>Errors · 24h</dt><dd>{overview.system_health.errors_24h}</dd></div>
          <div><dt>Failed ingestion</dt><dd>{overview.system_health.documents.failed_ingestion}</dd></div>
          <div><dt>Open feedback</dt><dd>{overview.system_health.open_feedback}</dd></div>
        </dl>
      </section>
    </div>

    <InvoiceQueue />

    <section className={styles.panel}>
      <div className={styles.panelHeader}><div><h2>Platform Resources</h2><p>Safe operational projections; raw secrets, payment payloads and Agent inputs are excluded.</p></div><Badge tone="info">{page?.total || 0} records</Badge></div>
      <div className={styles.resourceTabs} role="tablist" aria-label="Admin resources">
        {RESOURCES.map(([key, label]) => <button key={key} type="button" role="tab" aria-selected={resource === key} className={`${styles.resourceTab} ${resource === key ? styles.resourceTabActive : ""}`} onClick={() => loadResource(key)}>{label}{overview.resources[key] != null ? ` (${overview.resources[key]})` : ""}</button>)}
      </div>
      {resourceLoading ? <LoadingState label="正在读取资源" /> : page?.available === false || !page?.items.length ? <EmptyState icon="—" title={page?.message || "暂无记录"} description="没有可展示的真实数据库记录。" /> : <>
        <DataTable><table className={styles.table}><thead><tr>{columns.map((column) => <th key={column}>{column}</th>)}</tr></thead><tbody>{page.items.map((item) => <tr key={String(item.id)}>{columns.map((column) => <td key={column}>{resource === "organizations" && column === "account_stage" ? <select aria-label={`更新 ${String(item.name)} 的账户阶段`} value={String(item.account_stage)} onChange={(event) => mutateRow(() => api.updateOrganizationStage(String(item.id), event.target.value))}>{STAGES.map((stage) => <option key={stage}>{stage}</option>)}</select> : resource === "feedback" && column === "status" ? <select aria-label="更新反馈状态" value={String(item.status)} onChange={(event) => mutateRow(() => api.updateFeedbackStatus(String(item.id), event.target.value))}>{FEEDBACK_STATES.map((state) => <option key={state}>{state}</option>)}</select> : displayValue(item[column])}</td>)}</tr>)}</tbody></table></DataTable>
        <div className={styles.pager}><Button type="button" variant="secondary" disabled={page.offset === 0} onClick={() => loadResource(resource, Math.max(0, page.offset - page.limit))}>上一页</Button><span className={styles.muted}>{page.offset + 1}–{Math.min(page.offset + page.items.length, page.total)} / {page.total}</span><Button type="button" variant="secondary" disabled={page.offset + page.limit >= page.total} onClick={() => loadResource(resource, page.offset + page.limit)}>下一页</Button></div>
      </>}
    </section>

    <p className={styles.muted}>平台管理员权限独立于租户角色。<Link href="/admin/investor-metrics">查看指标定义与融资数据</Link></p>
  </AppShell>;
}
