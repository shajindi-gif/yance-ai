"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { EmptyState } from "@/components/ui/EmptyState";
import { InlineAlert } from "@/components/ui/InlineAlert";
import { LoadingState } from "@/components/ui/LoadingState";
import { PageHeader } from "@/components/ui/PageHeader";
import AppShell from "@/components/workspace/AppShell";
import content from "@/components/workspace/WorkspaceContent.module.css";
import flow from "@/components/workspace/CoreWorkflow.module.css";
import api, { type Company, type Policy } from "@/lib/api";

const LEVEL_LABELS: Record<string, string> = {
  national: "国家级",
  provincial: "省级",
  municipal: "市级",
  district: "区级",
};

const FUNDING_TYPE_LABELS: Record<string, string> = {
  grant: "资助/补贴",
  tax_incentive: "税收优惠",
  loan_discount: "贷款贴息",
  voucher: "创新券",
  talent: "人才项目",
  competition: "赛事奖励",
  equity: "产业基金",
  service: "服务支持",
};

function fundingLabel(policy: Policy): string | null {
  if (policy.funding_amount_max != null) {
    if (policy.funding_amount_min != null && policy.funding_amount_min !== policy.funding_amount_max) {
      return `${policy.funding_amount_min}-${policy.funding_amount_max} 万元`;
    }
    return `最高 ${policy.funding_amount_max} 万元`;
  }
  return policy.support_amount || null;
}

export default function DiscoverPage() {
  const [policies, setPolicies] = useState<Policy[]>([]);
  const [companies, setCompanies] = useState<Company[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [query, setQuery] = useState("");
  const [levelFilter, setLevelFilter] = useState("");
  const [scanning, setScanning] = useState(false);
  const [scanMessage, setScanMessage] = useState("");

  const load = useCallback(async () => {
    setError("");
    try {
      const [all, comps] = await Promise.all([api.getPolicies(), api.getCompanies()]);
      setPolicies(all);
      setCompanies(comps);
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : "资金目录加载失败");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (!api.isAuthenticated()) {
      window.location.href = "/login";
      return;
    }
    void load();
  }, [load]);

  const visible = useMemo(() => {
    const text = query.trim().toLowerCase();
    return policies
      .filter((policy) => policy.status === "published")
      .filter((policy) => (levelFilter ? policy.level === levelFilter : true))
      .filter((policy) =>
        text
          ? [policy.title, policy.issuing_authority, policy.industry, policy.support_type, policy.city]
              .filter(Boolean)
              .some((field) => String(field).toLowerCase().includes(text))
          : true,
      )
      .sort((a, b) => {
        const deadlineOf = (p: Policy) => (p.deadline ? new Date(p.deadline).getTime() : Infinity);
        return deadlineOf(a) - deadlineOf(b);
      });
  }, [policies, query, levelFilter]);

  const runScan = async () => {
    const company = companies[0];
    if (!company || scanning) return;
    setScanning(true);
    setScanMessage("");
    try {
      await api.createPolicyScan(company.id, `discover-${Date.now()}`);
      setScanMessage("资格扫描已在后台启动，可在「我的机会」查看逐条资格结论。");
    } catch (scanError) {
      setScanMessage(scanError instanceof Error ? scanError.message : "扫描启动失败");
    } finally {
      setScanning(false);
    }
  };

  if (loading) return <AppShell><LoadingState label="正在加载资金目录" /></AppShell>;

  return (
    <AppShell>
      <PageHeader
        eyebrow="Discover"
        title="发现资金"
        description="政策、补贴、基金、人才项目与赛事奖励的统一目录。所有内容来自已收录的官方文件，资格结论以你的企业画像扫描为准。"
        actions={
          companies.length ? (
            <Button onClick={runScan} disabled={scanning}>
              {scanning ? "启动中…" : "为企业扫描资格"}
            </Button>
          ) : (
            <Link className="yc-btn-primary" href="/companies" style={{ textDecoration: "none" }}>先创建企业档案</Link>
          )
        }
      />
      {error ? <InlineAlert tone="error">{error}</InlineAlert> : null}
      {scanMessage ? <InlineAlert tone="info">{scanMessage}</InlineAlert> : null}

      <div className={flow.toolbar}>
        <input
          aria-label="搜索资金目录"
          placeholder="搜索政策名称、发文机关、行业…"
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          style={{ flex: 1, minWidth: 220, padding: "9px 12px", border: "1px solid #dde3eb", borderRadius: 8, fontSize: 13 }}
        />
        <select
          aria-label="按层级筛选"
          value={levelFilter}
          onChange={(event) => setLevelFilter(event.target.value)}
          style={{ padding: "9px 12px", border: "1px solid #dde3eb", borderRadius: 8, fontSize: 13, background: "#fff" }}
        >
          <option value="">全部层级</option>
          {Object.entries(LEVEL_LABELS).map(([key, label]) => (
            <option key={key} value={key}>{label}</option>
          ))}
        </select>
      </div>

      {visible.length === 0 ? (
        <EmptyState
          icon="—"
          title={query || levelFilter ? "没有匹配的资金条目" : "资金目录暂无已发布条目"}
          description={query || levelFilter ? "换个关键词或清除筛选试试。" : "运营团队正在收录官方政策文件，已发布条目会显示在这里。"}
        />
      ) : (
        <div className={content.stack}>
          {visible.map((policy) => {
            const amount = fundingLabel(policy);
            const deadline = policy.deadline ? new Date(policy.deadline) : null;
            const daysLeft = deadline ? Math.ceil((deadline.getTime() - Date.now()) / 86400000) : null;
            return (
              <article key={policy.id} className={content.card}>
                <div className={content.rowBetween} style={{ gap: 12, flexWrap: "wrap" }}>
                  <div style={{ minWidth: 0, flex: 1 }}>
                    <div style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap" }}>
                      <strong style={{ fontSize: 15 }}>{policy.title}</strong>
                      {policy.level ? <Badge tone="neutral">{LEVEL_LABELS[policy.level] || policy.level}</Badge> : null}
                      {policy.funding_type ? (
                        <Badge tone="info">{FUNDING_TYPE_LABELS[policy.funding_type] || policy.funding_type}</Badge>
                      ) : null}
                    </div>
                    <div className={content.meta} style={{ marginTop: 6 }}>
                      {[policy.issuing_authority, policy.province, policy.city, policy.industry]
                        .filter(Boolean)
                        .join(" · ") || "发布机关待补充"}
                    </div>
                    {policy.support_amount && !policy.funding_amount_max ? (
                      <div className={content.subtle} style={{ marginTop: 6, fontSize: 12 }}>
                        官方金额表述：{policy.support_amount}（尚未结构化为数值，以原文为准）
                      </div>
                    ) : null}
                  </div>
                  <div style={{ textAlign: "right", flexShrink: 0 }}>
                    {amount ? <div className={flow.metric}><strong>{amount}</strong></div> : <div className={content.subtle} style={{ fontSize: 12 }}>金额：见官方条款</div>}
                    {daysLeft != null ? (
                      <div style={{ marginTop: 6 }}>
                        <Badge tone={daysLeft < 0 ? "neutral" : daysLeft <= 14 ? "warning" : "success"}>
                          {daysLeft < 0 ? "本轮已截止" : `剩 ${daysLeft} 天`}
                        </Badge>
                      </div>
                    ) : null}
                  </div>
                </div>
                <div className={content.actionRow} style={{ marginTop: 12 }}>
                  {policy.source_url ? (
                    <a href={policy.source_url} target="_blank" rel="noopener noreferrer" className={flow.link}>
                      查看官方原文
                    </a>
                  ) : (
                    <span className={content.subtle} style={{ fontSize: 12 }}>原文链接待运营补充</span>
                  )}
                </div>
              </article>
            );
          })}
        </div>
      )}
    </AppShell>
  );
}
