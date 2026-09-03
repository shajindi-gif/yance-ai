"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { ButtonLink } from "@/components/ui/ButtonLink";
import { EmptyState } from "@/components/ui/EmptyState";
import { InlineAlert } from "@/components/ui/InlineAlert";
import { LoadingState } from "@/components/ui/LoadingState";
import { PageHeader } from "@/components/ui/PageHeader";
import AppShell from "@/components/workspace/AppShell";
import flow from "@/components/workspace/CoreWorkflow.module.css";
import content from "@/components/workspace/WorkspaceContent.module.css";
import api, { type Company, type Opportunity, type PolicyScan } from "@/lib/api";

const ELIGIBILITY = {
  ELIGIBLE: { label: "符合", tone: "success" as const },
  POTENTIALLY_ELIGIBLE: { label: "可能符合", tone: "warning" as const },
  NOT_ELIGIBLE: { label: "不符合", tone: "danger" as const },
  NEED_MORE_INFORMATION: { label: "需要更多信息", tone: "neutral" as const },
};

export default function OpportunitiesPage() {
  const router = useRouter();
  const [companies, setCompanies] = useState<Company[]>([]);
  const [companyId, setCompanyId] = useState("");
  const [opportunities, setOpportunities] = useState<Opportunity[]>([]);
  const [scans, setScans] = useState<PolicyScan[]>([]);
  const [loading, setLoading] = useState(true);
  const [scanning, setScanning] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

  const load = async (filterCompanyId?: string) => {
    const [companyResult, opportunityResult, scanResult] = await Promise.all([
      api.getCompanies(),
      api.getOpportunities(filterCompanyId ? { companyId: filterCompanyId } : undefined),
      api.getPolicyScans(filterCompanyId),
    ]);
    setCompanies(companyResult);
    setOpportunities(opportunityResult);
    setScans(scanResult);
    setCompanyId((current) => current || filterCompanyId || companyResult[0]?.id || "");
  };

  useEffect(() => {
    if (!api.isAuthenticated()) {
      router.push("/login");
      return;
    }
    let active = true;
    load()
      .catch((loadError) => {
        if (active) {
          setError(loadError instanceof Error ? loadError.message : "政策机会加载失败");
        }
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [router]);

  const filterCompany = async (nextCompanyId: string) => {
    setCompanyId(nextCompanyId);
    setError("");
    try {
      const [opportunityResult, scanResult] = await Promise.all([
        api.getOpportunities(nextCompanyId ? { companyId: nextCompanyId } : undefined),
        api.getPolicyScans(nextCompanyId || undefined),
      ]);
      setOpportunities(opportunityResult);
      setScans(scanResult);
    } catch (filterError) {
      setError(filterError instanceof Error ? filterError.message : "筛选失败");
    }
  };

  const startScan = async () => {
    if (!companyId) return;
    setScanning(true);
    setError("");
    setMessage("");
    try {
      const key = globalThis.crypto?.randomUUID?.() || `${Date.now()}-${companyId}`;
      const scan = await api.createPolicyScan(companyId, key);
      setScans((current) => [scan, ...current.filter((item) => item.id !== scan.id)]);
      setMessage("扫描请求已创建。当前执行器为进程内任务，Phase 4 将替换为可恢复队列。 ");
      window.setTimeout(() => {
        load(companyId).catch(() => undefined);
      }, 3500);
    } catch (scanError) {
      setError(scanError instanceof Error ? scanError.message : "扫描启动失败");
    } finally {
      setScanning(false);
    }
  };

  if (loading) {
    return (
      <AppShell>
        <LoadingState label="正在加载政策机会" />
      </AppShell>
    );
  }

  const latestScan = scans[0];

  return (
    <AppShell>
      <PageHeader
        eyebrow="Opportunities"
        title="政策机会"
        description="匹配分表示相关性，不等于申报资格；资格在证据核验前保持“需要更多信息”。"
        actions={
          <Button type="button" onClick={startScan} disabled={scanning || !companyId}>
            {scanning ? "创建扫描中…" : "开始政策扫描"}
          </Button>
        }
      />
      {error && <InlineAlert>{error}</InlineAlert>}
      {message && <InlineAlert tone="info">{message}</InlineAlert>}

      {companies.length === 0 ? (
        <EmptyState
          icon="▦"
          title="请先创建企业"
          description="政策扫描必须固定引用一个已发布的企业画像版本。"
          action={<ButtonLink href="/companies">创建企业</ButtonLink>}
        />
      ) : (
        <>
          <div className={flow.toolbar}>
            <select aria-label="按企业筛选政策机会" value={companyId} onChange={(event) => filterCompany(event.target.value)}>
              <option value="">全部企业</option>
              {companies.map((company) => <option key={company.id} value={company.id}>{company.name}</option>)}
            </select>
            {latestScan && (
              <div className={flow.inlineMeta}>
                <Badge tone={latestScan.status === "completed" ? "success" : latestScan.status === "failed" ? "danger" : "info"}>
                  最近扫描：{latestScan.status}
                </Badge>
                {latestScan.task_id && <ButtonLink href={`/tasks/${latestScan.task_id}`} variant="secondary">查看执行任务</ButtonLink>}
              </div>
            )}
          </div>

          {opportunities.length === 0 ? (
            <EmptyState
              icon="◎"
              title="暂无政策机会"
              description="完善并发布企业画像后开始扫描；没有命中时系统保持空状态。"
              action={companyId ? <ButtonLink href={`/companies/${companyId}`}>检查企业画像</ButtonLink> : undefined}
            />
          ) : (
            <div className={content.stack}>
              {opportunities.map((opportunity) => {
                const eligibility = ELIGIBILITY[opportunity.eligibility_status];
                const snapshot = opportunity.policy_snapshot_json;
                return (
                  <Link key={opportunity.id} href={`/opportunities/${opportunity.id}`} className={content.listCard}>
                    <div className={content.listCardHeader}>
                      <span className={content.itemTitle}>{snapshot.title || opportunity.title}</span>
                      <div className={flow.inlineMeta}>
                        <Badge tone="info">匹配 {Math.round((opportunity.score || 0) * 100)}%</Badge>
                        <Badge tone={eligibility.tone}>{eligibility.label}</Badge>
                      </div>
                    </div>
                    <div className={content.meta}>
                      {[snapshot.issuing_authority, snapshot.jurisdiction, snapshot.support_amount, snapshot.deadline ? `截止 ${new Date(snapshot.deadline).toLocaleDateString("zh-CN")}` : null].filter(Boolean).join(" · ") || "政策元数据待补齐"}
                    </div>
                  </Link>
                );
              })}
            </div>
          )}
        </>
      )}
    </AppShell>
  );
}
