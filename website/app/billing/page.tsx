"use client";

import { useCallback, useEffect, useState } from "react";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { ButtonLink } from "@/components/ui/ButtonLink";
import { EmptyState } from "@/components/ui/EmptyState";
import { InlineAlert } from "@/components/ui/InlineAlert";
import { LoadingState } from "@/components/ui/LoadingState";
import { PageHeader } from "@/components/ui/PageHeader";
import AppShell from "@/components/workspace/AppShell";
import styles from "@/components/workspace/Enterprise.module.css";
import api, { type BillingOverview, type InvoiceItem, type PlanCatalogItem } from "@/lib/api";

const METER_LABELS: Record<string, string> = { policy_scans: "政策扫描", companies: "企业", reports: "报告", documents: "资料", generated_documents: "生成文档", agent_runs: "Agent Runs", users: "用户", storage_bytes: "存储" };
const INVOICE_STATUS: Record<string, { label: string; tone: "success" | "warning" | "danger" | "neutral" }> = {
  requested: { label: "待开具", tone: "warning" },
  issued: { label: "已开具", tone: "success" },
  rejected: { label: "已驳回", tone: "danger" },
  generated: { label: "付款凭证", tone: "neutral" },
  sent: { label: "已送达", tone: "success" },
};
function amount(value: number, currency: string) { return new Intl.NumberFormat("zh-CN", { style: "currency", currency }).format(value); }
function usageValue(meter: string, value: number) { return meter === "storage_bytes" ? `${(value / 1024 / 1024).toFixed(1)} MB` : value.toLocaleString("zh-CN"); }

function InvoiceSection({ orders }: { orders: BillingOverview["orders"] }) {
  const [invoices, setInvoices] = useState<InvoiceItem[]>([]);
  const [orderId, setOrderId] = useState("");
  const [title, setTitle] = useState("");
  const [taxNumber, setTaxNumber] = useState("");
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const reload = useCallback(() => { api.getInvoices().then(setInvoices).catch(() => undefined); }, []);
  useEffect(reload, [reload]);
  const paidWithoutInvoice = orders.filter((o) => o.status === "paid" && !invoices.some((inv) => inv.order_id === o.id && inv.status !== "rejected"));
  const submit = async () => {
    setBusy(true); setError(""); setMessage("");
    try {
      await api.createInvoice({ order_id: orderId || paidWithoutInvoice[0]?.id || "", title: title.trim(), tax_number: taxNumber.trim() });
      setMessage("开票申请已提交，运营在电子税务局开具后可在下方下载数电票。");
      setOrderId(""); setTitle(""); setTaxNumber("");
      reload();
    } catch (e) { setError(e instanceof Error ? e.message : "提交失败"); }
    finally { setBusy(false); }
  };
  const download = async (inv: InvoiceItem) => {
    try {
      const blob = await api.downloadInvoiceVoucher(inv.id);
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url; a.download = inv.voucher_filename || `电子发票_${inv.invoice_no}.pdf`;
      document.body.appendChild(a); a.click(); a.remove();
      setTimeout(() => URL.revokeObjectURL(url), 4000);
    } catch (e) { setError(e instanceof Error ? e.message : "下载失败"); }
  };
  return <section className={styles.panel}>
    <div className={styles.panelHeader}><div><h2>发票（数电票）</h2><p>已支付订单可申请开票；运营通过电子税务局开具数电票后，在此下载发票文件。</p></div></div>
    {error ? <InlineAlert tone="error">{error}</InlineAlert> : null}
    {message ? <InlineAlert tone="info">{message}</InlineAlert> : null}
    {paidWithoutInvoice.length ? <div className={styles.rows}>
      <div className={styles.row}>
        <select aria-label="选择订单" value={orderId} onChange={(e) => setOrderId(e.target.value)} style={{ padding: "8px 10px", borderRadius: 8, border: "1px solid #e2e8f0" }}>
          <option value="">选择已支付订单：{paidWithoutInvoice[0] ? `${paidWithoutInvoice[0].product_code} · ${amount(paidWithoutInvoice[0].amount, paidWithoutInvoice[0].currency)}` : ""}</option>
          {paidWithoutInvoice.map((o) => <option key={o.id} value={o.id}>{o.product_code} · {o.order_no} · {amount(o.amount, o.currency)}</option>)}
        </select>
      </div>
      <div className={styles.row}><input placeholder="发票抬头（公司全称）" value={title} onChange={(e) => setTitle(e.target.value)} style={{ padding: "8px 10px", borderRadius: 8, border: "1px solid #e2e8f0", flex: 1 }} /></div>
      <div className={styles.row}><input placeholder="纳税人识别号（15-20 位）" value={taxNumber} onChange={(e) => setTaxNumber(e.target.value)} style={{ padding: "8px 10px", borderRadius: 8, border: "1px solid #e2e8f0", flex: 1 }} /></div>
      <div className={styles.row}><Button type="button" disabled={busy || !title.trim() || taxNumber.trim().length < 15} onClick={submit}>{busy ? "提交中…" : "申请开票"}</Button></div>
    </div> : <EmptyState icon="—" title="暂无可开票订单" description="完成支付后可在此申请数电票。" />}
    {invoices.length ? <div className={styles.rows}>{invoices.map((inv) => {
      const st = INVOICE_STATUS[inv.status] || { label: inv.status, tone: "neutral" as const };
      return <div className={styles.row} key={inv.id}>
        <strong>{inv.title}<small className={styles.muted}> · {inv.invoice_no} · {amount(inv.total_amount, "CNY")}</small></strong>
        <span style={{ display: "flex", gap: 8, alignItems: "center" }}>
          <Badge tone={st.tone}>{st.label}</Badge>
          {inv.status === "rejected" && inv.review_note ? <small className={styles.muted} title={inv.review_note}>原因：{inv.review_note}</small> : null}
          {inv.status === "issued" ? <Button type="button" variant="secondary" onClick={() => download(inv)}>下载发票</Button> : null}
        </span>
      </div>;
    })}</div> : null}
  </section>;
}

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
      {overview.metering_policy?.manual_artifact_revisions_consume_generation === false ? <InlineAlert tone="info">当前规则下，人工编辑和接受人工建议不会新增生成工作稿额度消耗；历史用量记录保留，新生成与重新生成仍按额度计量。</InlineAlert> : null}
      <section className={styles.panel}><div className={styles.panelHeader}><div><h2>{overview.plan.name}</h2><p>{new Date(overview.subscription.current_period_start).toLocaleDateString("zh-CN")} — {new Date(overview.subscription.current_period_end).toLocaleDateString("zh-CN")}</p></div><Badge tone={overview.subscription.status === "active" ? "success" : "warning"}>{{ active: "订阅有效", past_due: "待付款", canceled: "已取消", trialing: "试用中" }[overview.subscription.status] || overview.subscription.status}</Badge></div><div className={styles.usageList}>{overview.usage.map((item) => { const ratio = item.limit ? Math.min(100, item.used / item.limit * 100) : 0; return <div className={styles.usageItem} key={item.meter}><div className={styles.usageMeta}><strong>{METER_LABELS[item.meter] || item.meter}</strong><span>{usageValue(item.meter, item.used)} / {item.limit == null ? "合同定义" : usageValue(item.meter, item.limit)}</span></div><div className={styles.track}><span style={{ width: `${ratio}%` }} /></div></div>; })}</div></section>
      <section><div className={styles.panelHeader}><div><h2>套餐目录</h2><p>限制来自数据库；付费价格未配置时仅展示联系销售。</p></div></div><div className={styles.grid}>{plans.map((plan) => <article className={styles.card} key={plan.code}><Badge tone={plan.code === overview.plan.code ? "success" : "neutral"}>{plan.code === overview.plan.code ? "当前套餐" : plan.sales_motion}</Badge><h2>{plan.name}</h2><p>{plan.description}</p><div className={styles.price}>{plan.price ? plan.price.unit_amount === 0 ? "免费" : amount(plan.price.unit_amount, plan.price.currency) : "价格未配置"}</div><ul className={styles.featureList}>{plan.features.map((feature) => <li key={feature}>✓ {feature}</li>)}</ul></article>)}</div></section>
      {!overview.paid_plan_checkout_available ? <InlineAlert tone="info">付费订阅尚无已启用的服务端 PriceVersion。当前不会创建模拟订阅或显示静态月费。</InlineAlert> : null}
      <section className={styles.panel}><div className={styles.panelHeader}><div><h2>最近交易</h2><p>支付状态只由已验证的服务商回调或受控财务流程更新。</p></div></div>{overview.orders.length ? <div className={styles.rows}>{overview.orders.map((order) => <div className={styles.row} key={order.id}><strong>{order.product_code}<small className={styles.muted}> · {order.order_no}</small></strong><span>{amount(order.amount, order.currency)}</span><Badge tone={order.status === "paid" ? "success" : "neutral"}>{order.status}</Badge></div>)}</div> : <EmptyState icon="—" title="暂无真实交易" description="当前工作区没有订单或付款记录。" />}</section>
      <InvoiceSection orders={overview.orders} />
    </div> : null}
  </AppShell>;
}
