"use client";

import { useEffect, useState } from "react";
import { Badge } from "@/components/ui/Badge";
import { ButtonLink } from "@/components/ui/ButtonLink";
import { InlineAlert } from "@/components/ui/InlineAlert";
import { LoadingState } from "@/components/ui/LoadingState";
import { PageHeader } from "@/components/ui/PageHeader";
import AppShell from "@/components/workspace/AppShell";
import styles from "@/components/workspace/AdminDashboard.module.css";
import api, { type InvestorMetrics } from "@/lib/api";

const METRICS: Array<[keyof InvestorMetrics["totals"], string, string]> = [
  ["total_users", "Total Users", "users"],
  ["active_users_30d", "Active Users", "30-day server events"],
  ["organizations", "Organizations", "tenants"],
  ["companies", "Companies", "persisted companies"],
  ["policy_scans", "Policy Scans", "all statuses"],
  ["applications", "Applications", "all workspaces"],
  ["reports_generated", "Reports", "server events"],
  ["agent_runs", "Agent Runs", "all statuses"],
  ["successful_runs", "Successful Runs", "completed"],
  ["failed_runs", "Failed Runs", "failed"],
  ["documents_generated", "Documents Generated", "artifact versions"],
  ["poc_accounts", "PoC Accounts", "explicit classification"],
  ["paying_customers", "Paying Customers", "paid-order tenants"],
  ["llm_cost_usd", "LLM Cost", "USD, persisted"],
  ["cost_per_run_usd", "Cost / Run", "USD, all runs"],
];

function metricValue(key: keyof InvestorMetrics["totals"], value: number | null): string {
  if (value == null) return "—";
  if (key === "llm_cost_usd" || key === "cost_per_run_usd") return `$${value.toFixed(6)}`;
  return value.toLocaleString("zh-CN");
}

export default function InvestorMetricsPage() {
  const [metrics, setMetrics] = useState<InvestorMetrics | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!api.isAuthenticated()) {
      setError("请先登录平台管理员账号。");
      setLoading(false);
      return;
    }
    api.getInvestorMetrics()
      .then(setMetrics)
      .catch((loadError) => setError(loadError instanceof Error ? loadError.message : "融资指标加载失败"))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <AppShell><LoadingState label="正在核对融资指标" /></AppShell>;
  if (!metrics) return <AppShell><PageHeader eyebrow="Investor Metrics" title="无法访问融资指标" description="该页面仅限明确授权的平台管理员。" />{error ? <InlineAlert tone="error">{error}</InlineAlert> : null}<ButtonLink href="/dashboard" variant="secondary">返回工作台</ButtonLink></AppShell>;

  const maxFunnel = Math.max(1, ...metrics.funnel.map((step) => step.organizations));
  const maxRuns = Math.max(1, ...metrics.agent_trend_30d.map((point) => point.runs));

  return <AppShell>
    <PageHeader eyebrow="Investor Metrics · Internal" title="融资数据" description={`全平台数据库快照 · ${new Date(metrics.generated_at).toLocaleString("zh-CN")} · 不包含估算、Demo 或手工补数`} actions={<ButtonLink href="/admin" variant="secondary">返回 Admin</ButtonLink>} />
    {error ? <InlineAlert tone="error">{error}</InlineAlert> : null}

    <div className={styles.metricGrid}>
      {METRICS.map(([key, label, note]) => <div className={styles.metricCard} key={key}><strong>{metricValue(key, metrics.totals[key])}</strong><span>{label}</span><small>{note}</small></div>)}
      {metrics.revenue_by_currency.length ? metrics.revenue_by_currency.map((item) => <div className={styles.metricCard} key={item.currency}><strong>{item.amount.toLocaleString("zh-CN", { maximumFractionDigits: 2 })}</strong><span>Revenue · {item.currency}</span><small>paid orders only</small></div>) : <div className={styles.metricCard}><strong>0</strong><span>Revenue</span><small>No paid orders</small></div>}
    </div>

    <div className={styles.twoColumn}>
      <section className={styles.panel}>
        <div className={styles.panelHeader}><div><h2>Conversion Funnel</h2><p>Distinct organizations per server-owned milestone. This is not a cohort-retention funnel.</p></div><Badge tone="info">All time</Badge></div>
        <div className={styles.funnel}>
          {metrics.funnel.map((step) => <div className={styles.funnelRow} key={step.event}><div className={styles.funnelLabel}><strong>{step.label}</strong><small>{step.event}</small></div><div className={styles.funnelTrack}><div className={styles.funnelFill} style={{ width: `${step.organizations / maxFunnel * 100}%` }} /></div><span className={styles.funnelValue}>{step.organizations} orgs · {step.conversion_from_previous == null ? "—" : `${Math.round(step.conversion_from_previous * 100)}%`}</span></div>)}
        </div>
      </section>
      <section className={styles.panel}>
        <div className={styles.panelHeader}><div><h2>Agent Execution</h2><p>Trailing 30 days · persisted runs</p></div><Badge tone="neutral">UTC</Badge></div>
        <div className={styles.trend} aria-label="30-day Agent execution trend">
          {metrics.agent_trend_30d.map((point) => <span key={point.date} className={`${styles.trendBar} ${point.failed ? styles.trendBarFailed : ""}`} style={{ height: `${Math.max(point.runs ? 8 : 1, point.runs / maxRuns * 100)}%` }} data-label={`${point.date}: ${point.runs} runs, $${point.cost_usd}`} />)}
        </div>
      </section>
    </div>

    <section className={styles.panel}>
      <div className={styles.panelHeader}><div><h2>Metric Definitions</h2><p>Definitions are shown beside the dashboard so diligence readers can reproduce each number.</p></div><Badge tone="success">Database sourced</Badge></div>
      <dl className={styles.definitions}>{Object.entries(metrics.definitions).map(([name, definition]) => <div key={name}><dt>{name}</dt><dd>{definition}</dd></div>)}</dl>
      <div className={styles.availability}>{Object.entries(metrics.availability).filter(([, available]) => !available).map(([name]) => <div className={styles.unavailable} key={name}><strong>{name}</strong><p>Not tracked. No value is displayed or inferred.</p></div>)}</div>
    </section>
  </AppShell>;
}
