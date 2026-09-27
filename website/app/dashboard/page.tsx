"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { Badge } from "@/components/ui/Badge";
import { ButtonLink } from "@/components/ui/ButtonLink";
import { EmptyState } from "@/components/ui/EmptyState";
import { InlineAlert } from "@/components/ui/InlineAlert";
import { LoadingState } from "@/components/ui/LoadingState";
import { PageHeader } from "@/components/ui/PageHeader";
import AppShell from "@/components/workspace/AppShell";
import flow from "@/components/workspace/CoreWorkflow.module.css";
import content from "@/components/workspace/WorkspaceContent.module.css";
import api, {
  type ApplicationSummary,
  type AgentRunSummary,
  type Company,
  type CompanyProfile,
  type DocumentRecord,
  type FundingSummary,
  type Opportunity,
  type PolicyScan,
  type Tenant,
} from "@/lib/api";

interface DashboardState {
  tenant: Tenant;
  companies: Company[];
  opportunities: Opportunity[];
  applications: ApplicationSummary[];
  documents: DocumentRecord[];
  scans: PolicyScan[];
  agentRuns: AgentRunSummary[];
  firstProfile: CompanyProfile | null;
  funding: FundingSummary | null;
}

export default function DashboardPage() {
  const router = useRouter();
  const [data, setData] = useState<DashboardState | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!api.isAuthenticated()) {
      router.push("/login");
      return;
    }
    let active = true;
    const load = async () => {
      const [tenant, companies, opportunities, applications, documents, scans, agentRuns] =
        await Promise.all([
          api.getTenant(),
          api.getCompanies(),
          api.getOpportunities(),
          api.getApplications(),
          api.getDocuments(),
          api.getPolicyScans(),
          api.getAgentRuns(5),
        ]);
      const firstProfile = companies[0]
        ? await api.getCompanyProfile(companies[0].id)
        : null;
      const funding = companies.length
        ? await api.getFundingSummary(companies[0].id).catch(() => null)
        : null;
      return {
        tenant,
        companies,
        opportunities,
        applications,
        documents,
        scans,
        agentRuns,
        firstProfile,
        funding,
      };
    };
    load()
      .then((result) => {
        if (!active) return;
        setData(result);
        setError("");
      })
      .catch((loadError) => {
        if (!active) return;
        setError(loadError instanceof Error ? loadError.message : "工作台加载失败");
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [router]);

  if (loading) {
    return (
      <AppShell>
        <LoadingState label="正在加载企业工作台" />
      </AppShell>
    );
  }

  if (!data) {
    return (
      <AppShell>
        <PageHeader title="工作台暂不可用" description="未能读取当前工作区数据。" />
        {error && <InlineAlert>{error}</InlineAlert>}
      </AppShell>
    );
  }

  const activeApplications = data.applications.filter(
    (application) => !["completed", "cancelled"].includes(application.status),
  );
  const pendingDocuments = data.documents.filter(
    (document) => document.ingestion_status !== "completed",
  );
  const now = Date.now();
  const nextThirtyDays = now + 30 * 24 * 60 * 60 * 1000;
  const upcomingDeadlines = data.opportunities.filter((opportunity) => {
    const deadline = opportunity.policy_snapshot_json.deadline;
    if (!deadline) return false;
    const timestamp = new Date(deadline).getTime();
    return timestamp >= now && timestamp <= nextThirtyDays;
  });

  let nextAction = {
    title: "查看政策机会",
    description: "继续处理当前工作区的机会与申报项目。",
    href: "/opportunities",
  };
  if (data.companies.length === 0) {
    nextAction = {
      title: "创建企业档案",
      description: "建立第一家企业，开始形成结构化画像。",
      href: "/companies",
    };
  } else if (!data.firstProfile?.published_version) {
    nextAction = {
      title: "完善并发布企业画像",
      description: "扫描必须固定使用一个已发布的画像版本。",
      href: `/companies/${data.companies[0].id}`,
    };
  } else if (data.documents.length === 0) {
    nextAction = {
      title: "导入企业资料",
      description: "上传营业执照、财务摘要或知识产权清单。",
      href: "/documents",
    };
  } else if (data.scans.length === 0) {
    nextAction = {
      title: "开始政策扫描",
      description: "使用已发布画像创建可追踪的扫描请求。",
      href: "/opportunities",
    };
  } else if (data.opportunities.length > 0 && data.applications.length === 0) {
    nextAction = {
      title: "选择机会并开始申报",
      description: "查看匹配依据后，为合适的机会创建申报工作区。",
      href: `/opportunities/${data.opportunities[0].id}`,
    };
  }

  return (
    <AppShell workspaceName={data.tenant.name}>
      <PageHeader
        eyebrow="Funding Command Center"
        title="指挥中心"
        description={`${data.tenant.name} · 所有指标来自当前租户的服务端记录；金额为官方条款结构化值，非预测。`}
      />
      {error && <InlineAlert>{error}</InlineAlert>}

      <div className={flow.metricGrid}>
        <div className={flow.metric}>
          <strong>
            {data.funding
              ? data.funding.estimated_funding_available_wan > 0
                ? `¥${data.funding.estimated_funding_available_wan.toLocaleString("zh-CN")} 万`
                : "见条款"
              : "—"}
          </strong>
          <span>可申请材料资金上限合计</span>
        </div>
        <div className={flow.metric}><strong>{data.funding?.eligible_count ?? data.opportunities.length}</strong><span>合格/潜在合格机会</span></div>
        <div className={flow.metric}><strong>{data.funding?.high_match_count ?? 0}</strong><span>高匹配（≥70 分）</span></div>
        <div className={flow.metric}><strong>{data.funding?.deadlines_in_30_days ?? upcomingDeadlines.length}</strong><span>30 天内截止</span></div>
        <div className={flow.metric}><strong>{data.funding?.applications_in_progress ?? activeApplications.length}</strong><span>进行中申报</span></div>
        <div className={flow.metric}><strong>{data.funding?.missing_evidence_count ?? pendingDocuments.length}</strong><span>缺失关键证据</span></div>
      </div>

      {data.funding ? (
        <div className={flow.gridTwo}>
          <section className={content.card}>
            <div className={content.cardHeader}>
              <div><h2>资金管道</h2><p className={content.cardIntro}>按申报状态统计的真实管道；画像完成度 {data.funding.profile_completeness}%。</p></div>
              <Badge tone={data.funding.unread_notifications ? "warning" : "neutral"}>{data.funding.unread_notifications} 未读</Badge>
            </div>
            {Object.keys(data.funding.pipeline).length === 0 ? (
              <p className={content.cardIntro}>尚无申报进入管道。</p>
            ) : (
              <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
                {Object.entries(data.funding.pipeline).map(([status, count]) => (
                  <Badge key={status} tone={status === "completed" ? "success" : status === "cancelled" ? "neutral" : "info"}>
                    {status} · {count}
                  </Badge>
                ))}
              </div>
            )}
            <div className={content.actionRow} style={{ marginTop: 12 }}>
              <Link href="/projects" className={flow.link}>查看完整管道与里程碑</Link>
              <Link href="/notifications" className={flow.link}>通知中心</Link>
            </div>
          </section>

          <section className={content.card}>
            <div className={content.cardHeader}>
              <div><h2>推荐机会</h2><p className={content.cardIntro}>来自最近一次资格扫描的高分结果。</p></div>
              <Link href="/opportunities" className={flow.link}>全部</Link>
            </div>
            {data.funding.recommended_opportunities.length === 0 ? (
              <p className={content.cardIntro}>暂无合格推荐，先运行政策扫描。</p>
            ) : (
              data.funding.recommended_opportunities.map((item) => (
                <Link key={item.id} href={`/opportunities/${item.id}`} className={content.activityRow}>
                  <span>{item.title}</span>
                  <span className={content.activityLatency}>{item.score != null ? `${Math.round(item.score)} 分` : ""}</span>
                </Link>
              ))
            )}
          </section>
        </div>
      ) : null}

      {data.funding && data.funding.upcoming_tasks.length > 0 ? (
        <section className={content.card} style={{ marginBottom: 20 }}>
          <div className={content.cardHeader}>
            <div><h2>近期任务</h2><p className={content.cardIntro}>未完成里程碑按截止日排序。</p></div>
            <Link href="/projects" className={flow.link}>管理</Link>
          </div>
          {data.funding.upcoming_tasks.slice(0, 5).map((task) => (
            <div key={task.id} className={content.activityRow}>
              <span>{task.title}</span>
              <span className={content.activityLatency}>
                {task.due_at ? new Date(task.due_at).toLocaleDateString("zh-CN") : "无期限"} · {task.status}
              </span>
            </div>
          ))}
        </section>
      ) : null}

      <div className={flow.gridTwo}>
        <section className={content.card}>
          <div className={content.cardHeader}>
            <div><h2>Next Best Action</h2><p className={content.cardIntro}>基于当前持久状态生成，不使用虚构成功数据。</p></div>
            <Badge tone="info">建议</Badge>
          </div>
          <div className={content.nextAction}>
            <div><strong>{nextAction.title}</strong><small>{nextAction.description}</small></div>
            <ButtonLink href={nextAction.href}>继续</ButtonLink>
          </div>
        </section>

        <section className={content.card}>
          <div className={content.cardHeader}>
            <div><h2>未来 30 天截止</h2><p className={content.cardIntro}>仅统计扫描快照中存在明确截止日期的机会。</p></div>
            <Badge tone={upcomingDeadlines.length ? "warning" : "neutral"}>{upcomingDeadlines.length}</Badge>
          </div>
          {upcomingDeadlines.length === 0 ? (
            <p className={content.cardIntro}>暂无已记录的临近截止机会。</p>
          ) : upcomingDeadlines.slice(0, 4).map((opportunity) => (
            <Link key={opportunity.id} href={`/opportunities/${opportunity.id}`} className={content.activityRow}>
              <span>{opportunity.policy_snapshot_json.title || opportunity.title}</span>
              <span className={content.activityLatency}>{new Date(opportunity.policy_snapshot_json.deadline as string).toLocaleDateString("zh-CN")}</span>
            </Link>
          ))}
        </section>
      </div>

      <section className={content.section}>
        <div className={content.sectionHeading}>
          <h2>最近 Agent Runs</h2>
          <p>显示持久化执行状态、步骤阶段与可复查运行轨迹。</p>
        </div>
        {data.agentRuns.length === 0 ? (
          <EmptyState icon="◎" title="暂无 Agent Run" description="创建政策扫描后，后台执行轨迹会出现在这里。" />
        ) : (
          <div className={content.stack}>
            {data.agentRuns.map((run) => (
              <Link key={run.id} href={`/agents/${run.id}`} className={content.listCard}>
                <div className={content.listCardHeader}><span className={content.itemTitle}>{run.agent_name} · {run.prompt_version || "未记录版本"}</span><Badge tone={run.status === "failed" ? "danger" : run.status === "completed" ? "success" : "info"}>{run.status}</Badge></div>
                <div className={content.meta}>{run.current_step || "等待执行"} · {new Date(run.created_at).toLocaleString("zh-CN")}</div>
              </Link>
            ))}
          </div>
        )}
      </section>
    </AppShell>
  );
}
