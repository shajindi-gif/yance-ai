"use client";

import { useEffect, useState } from "react";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { ButtonLink } from "@/components/ui/ButtonLink";
import { EmptyState } from "@/components/ui/EmptyState";
import { InlineAlert } from "@/components/ui/InlineAlert";
import { LoadingState } from "@/components/ui/LoadingState";
import { PageHeader } from "@/components/ui/PageHeader";
import AppShell from "@/components/workspace/AppShell";
import styles from "@/components/workspace/Enterprise.module.css";
import api, { type BillingOverview, type PlanCatalogItem } from "@/lib/api";

const METER_LABELS: Record<string, string> = { policy_scans: "政策扫描", companies: "企业", reports: "报告", documents: "资料", generated_documents: "生成文档", agent_runs: "Agent Runs", users: "用户", storage_bytes: "存储" };
function amount(value: number, currency: string) { return new Intl.NumberFormat("zh-CN", { style: "currency", currency }).format(value); }
function usageValue(meter: string, value: number) { return meter === "storage_bytes" ? `${(value / 1024 / 1024).toFixed(1)} MB` : value.toLocaleString("zh-CN"); }

export default function BillingPage() {
  const [overview, setOverview] = useState<BillingOverview | null>(null);
  const [plans, setPlans] = useState<PlanCatalogItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [retryNonce, setRetryNonce] = useState(0);
  useEffect(() => {
    let active = true;
    setLoading(true);
    setError("");
    if (!api.isAuthenticated()) { setError("请先登录工作区。"); setLoading(false); return; }
    Promise.all([api.getBillingOverview(), api.getPlans()])
      .then(([nextOverview, nextPlans]) => { if (active) { setOverview(nextOverview); setPlans(nextPlans); } })
      .catch((loadError) => { if (active) setError(loadError instanceof Error ? loadError.message : "账单数据加载失败"); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [retryNonce]);
  if (loading) return <AppShell><LoadingState label="正在读取套餐与真实用量" /></AppShell>;
  return <AppShell>
    <PageHeader eyebrow="Billing · Server Source" title="用量与账单" description="套餐、周期、用量、订单和付款凭证均读取服务端记录；没有 PriceVersion 时不会展示虚构价格。" actions={<ButtonLink href="/orders" variant="secondary">查看全部订单</ButtonLink>} />
    {error ? <InlineAlert tone="error">{error}</InlineAlert> : null}
    {error && !overview ? <Button type="button" variant="secondary" onClick={() => setRetryNonce((value) => value + 1)}>重新加载账单数据</Button> : null}
    {overview ? <div className={styles.stack}>
      <section className={styles.panel}><div className={styles.panelHeader}><div><h2>{overview.plan.name}</h2><p>{new Date(overview.subscription.current_period_start).toLocaleDateString("zh-CN")} — {new Date(overview.subscription.current_period_end).toLocaleDateString("zh-CN")}</p></div><Badge tone={overview.subscription.status === "active" ? "success" : "warning"}>{overview.subscription.status}</Badge></div><div className={styles.usageList}>{overview.usage.map((item) => { const ratio = item.limit ? Math.min(100, item.used / item.limit * 100) : 0; return <div className={styles.usageItem} key={item.meter}><div className={styles.usageMeta}><strong>{METER_LABELS[item.meter] || item.meter}</strong><span>{usageValue(item.meter, item.used)} / {item.limit == null ? "合同定义" : usageValue(item.meter, item.limit)}</span></div><div className={styles.track}><span style={{ width: `${ratio}%` }} /></div></div>; })}</div></section>
      <section><div className={styles.panelHeader}><div><h2>套餐目录</h2><p>限制来自数据库；付费价格未配置时仅展示联系销售。</p></div></div><div className={styles.grid}>{plans.map((plan) => <article className={styles.card} key={plan.code}><Badge tone={plan.code === overview.plan.code ? "success" : "neutral"}>{plan.code === overview.plan.code ? "当前套餐" : plan.sales_motion}</Badge><h2>{plan.name}</h2><p>{plan.description}</p><div className={styles.price}>{plan.price ? plan.price.unit_amount === 0 ? "免费" : amount(plan.price.unit_amount, plan.price.currency) : "价格未配置"}</div><ul className={styles.featureList}>{plan.features.map((feature) => <li key={feature}>✓ {feature}</li>)}</ul></article>)}</div></section>
      {!overview.paid_plan_checkout_available ? <InlineAlert tone="info">付费订阅尚无已启用的服务端 PriceVersion。当前不会创建模拟订阅或显示静态月费。</InlineAlert> : null}
      <section className={styles.panel}><div className={styles.panelHeader}><div><h2>最近交易</h2><p>支付状态只由已验证的服务商回调或受控财务流程更新。</p></div></div>{overview.orders.length ? <div className={styles.rows}>{overview.orders.map((order) => <div className={styles.row} key={order.id}><strong>{order.product_code}<small className={styles.muted}> · {order.order_no}</small></strong><span>{amount(order.amount, order.currency)}</span><Badge tone={order.status === "paid" ? "success" : "neutral"}>{order.status}</Badge></div>)}</div> : <EmptyState icon="—" title="暂无真实交易" description="当前工作区没有订单或付款记录。" />}</section>
    </div> : null}
  </AppShell>;
}
