"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { EmptyState } from "@/components/ui/EmptyState";
import { InlineAlert } from "@/components/ui/InlineAlert";
import { LoadingState } from "@/components/ui/LoadingState";
import { PageHeader } from "@/components/ui/PageHeader";
import PolicyEvidenceSearch from "@/components/workspace/PolicyEvidenceSearch";
import AppShell from "@/components/workspace/AppShell";
import content from "@/components/workspace/WorkspaceContent.module.css";
import flow from "@/components/workspace/CoreWorkflow.module.css";
import api, { type Company, type Policy } from "@/lib/api";
import pageStyles from './page.module.css';

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
  const [cityFilter, setCityFilter] = useState("");
  const [fundingFilter, setFundingFilter] = useState("");
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
      window.location.href = `/login?next=${encodeURIComponent("/discover")}`;
      return;
    }
    void load();
  }, [load]);

  const cityOptions = useMemo(
    () => [...new Set(policies.map((policy) => policy.city).filter((city): city is string => Boolean(city)))].sort((a, b) => a.localeCompare(b, "zh-CN")),
    [policies],
  );
  const fundingOptions = useMemo(() => {
    const present = new Set(policies.map((policy) => policy.funding_type).filter(Boolean));
    return Object.entries(FUNDING_TYPE_LABELS).filter(([key]) => present.has(key));
  }, [policies]);

  const visible = useMemo(() => {
    const text = query.trim().toLowerCase();
    return policies
      .filter((policy) => policy.status === "published")
      .filter((policy) => (levelFilter ? policy.level === levelFilter : true))
      .filter((policy) => (cityFilter ? policy.city === cityFilter : true))
      .filter((policy) => (fundingFilter ? policy.funding_type === fundingFilter : true))
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
  }, [policies, query, levelFilter, cityFilter, fundingFilter]);

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
        title="政策检索"
        description="在已收录并发布的政策目录中查找。城市、层级和支持类型只过滤当前列表，不改变资格扫描规则。资格结论以企业画像扫描为准。"
        actions={
          companies.length ? (
            <Button onClick={runScan} disabled={scanning}>
              {scanning ? "启动中…" : "为企业扫描资格"}
            </Button>
          ) : (
            <Link className={["yc-btn-primary", pageStyles.link].filter(Boolean).join(' ')} href="/companies" >先创建企业档案</Link>
          )
        }
      />
      {error ? <InlineAlert tone="error">{error}</InlineAlert> : null}
      {scanMessage ? <InlineAlert tone="info">{scanMessage}</InlineAlert> : null}

      <PolicyEvidenceSearch />

      <div className={flow.toolbar}>
        <input
          aria-label="搜索资金目录"
          placeholder="搜索政策名称、发文机关、行业或城市"
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          className={pageStyles.section}
        />
        <select
          aria-label="按层级筛选"
          value={levelFilter}
          onChange={(event) => setLevelFilter(event.target.value)}
          className={pageStyles.section2}
        >
          <option value="">全部层级</option>
          {Object.entries(LEVEL_LABELS).map(([key, label]) => (
            <option key={key} value={key}>{label}</option>
          ))}
        </select>
        {cityOptions.length > 0 ? (
          <select aria-label="按城市筛选" value={cityFilter} onChange={(event) => setCityFilter(event.target.value)} className={pageStyles.section2}>
            <option value="">全部城市</option>
            {cityOptions.map((city) => <option key={city} value={city}>{city}</option>)}
          </select>
        ) : null}
        {fundingOptions.length > 0 ? (
          <select aria-label="按支持类型筛选" value={fundingFilter} onChange={(event) => setFundingFilter(event.target.value)} className={pageStyles.section2}>
            <option value="">全部支持类型</option>
            {fundingOptions.map(([key, label]) => <option key={key} value={key}>{label}</option>)}
          </select>
        ) : null}
      </div>

      {visible.length === 0 ? (
        <EmptyState
          icon="—"
          title={query || levelFilter || cityFilter || fundingFilter ? "没有匹配的政策条目" : "政策目录暂无已发布条目"}
          description={query || levelFilter || cityFilter || fundingFilter ? "换个关键词或清除筛选试试。筛选只影响当前列表。" : "已发布条目会显示在这里。"}
        />
      ) : (
        <div className={content.stack}>
          {visible.map((policy) => {
            const amount = fundingLabel(policy);
            const deadline = policy.deadline ? new Date(policy.deadline) : null;
            const daysLeft = deadline ? Math.ceil((deadline.getTime() - Date.now()) / 86400000) : null;
            return (
              <article key={policy.id} className={content.card}>
                <div className={[content.rowBetween, pageStyles.section3].filter(Boolean).join(' ')} >
                  <div className={pageStyles.section4}>
                    <div className={pageStyles.layout}>
                      <strong className={pageStyles.section5}>{policy.title}</strong>
                      {policy.level ? <Badge tone="neutral">{LEVEL_LABELS[policy.level] || policy.level}</Badge> : null}
                      {policy.funding_type ? (
                        <Badge tone="info">{FUNDING_TYPE_LABELS[policy.funding_type] || policy.funding_type}</Badge>
                      ) : null}
                    </div>
                    <div className={[content.meta, pageStyles.section6].filter(Boolean).join(' ')} >
                      {[policy.issuing_authority, policy.province, policy.city, policy.industry]
                        .filter(Boolean)
                        .join(" · ") || "发布机关待补充"}
                    </div>
                    {policy.support_amount && !policy.funding_amount_max ? (
                      <div className={[content.subtle, pageStyles.section7].filter(Boolean).join(' ')} >
                        官方金额表述：{policy.support_amount}（尚未结构化为数值，以原文为准）
                      </div>
                    ) : null}
                  </div>
                  <div className={pageStyles.section8}>
                    {amount ? <div className={flow.metric}><strong>{amount}</strong></div> : <div className={[content.subtle, pageStyles.section9].filter(Boolean).join(' ')} >金额：见官方条款</div>}
                    {daysLeft != null ? (
                      <div className={pageStyles.section6}>
                        <Badge tone={daysLeft < 0 ? "neutral" : daysLeft <= 14 ? "warning" : "success"}>
                          {daysLeft < 0 ? "本轮已截止" : `剩 ${daysLeft} 天`}
                        </Badge>
                      </div>
                    ) : null}
                  </div>
                </div>
                <div className={[content.actionRow, pageStyles.section10].filter(Boolean).join(' ')} >
                  {policy.source_url ? (
                    <a href={policy.source_url} target="_blank" rel="noopener noreferrer" className={flow.link}>
                      查看官方原文
                    </a>
                  ) : (
                    <span className={[content.subtle, pageStyles.section9].filter(Boolean).join(' ')} >原文链接待运营补充</span>
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
