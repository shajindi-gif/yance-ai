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
      return {
        tenant,
        companies,
        opportunities,
        applications,
        documents,
        scans,
        agentRuns,
        firstProfile,
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
  const maxScore = Math.max(0, ...data.opportunities.map((item) => item.score || 0));

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
        eyebrow="Home"
        title="工作台"
        description={`${data.tenant.name} · 所有指标来自当前租户的服务端记录。`}
      />
      {error && <InlineAlert>{error}</InlineAlert>}

      <div className={flow.metricGrid}>
        <div className={flow.metric}><strong>{Math.round(maxScore * 100)}%</strong><span>最高机会相关性</span></div>
        <div className={flow.metric}><strong>{data.opportunities.length}</strong><span>已匹配机会</span></div>
        <div className={flow.metric}><strong>{activeApplications.length}</strong><span>进行中申报</span></div>
        <div className={flow.metric}><strong>{pendingDocuments.length}</strong><span>未完成摄取资料</span></div>
      </div>

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
