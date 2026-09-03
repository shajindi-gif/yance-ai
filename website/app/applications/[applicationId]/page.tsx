"use client";

import { useParams, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { ButtonLink } from "@/components/ui/ButtonLink";
import { InlineAlert } from "@/components/ui/InlineAlert";
import { LoadingState } from "@/components/ui/LoadingState";
import { PageHeader } from "@/components/ui/PageHeader";
import AppShell from "@/components/workspace/AppShell";
import flow from "@/components/workspace/CoreWorkflow.module.css";
import content from "@/components/workspace/WorkspaceContent.module.css";
import api, { type ApplicationDetail } from "@/lib/api";

type Tab = "overview" | "requirements" | "activity";

const STATUS_LABELS: Record<string, string> = {
  draft: "草稿",
  preparing: "材料准备",
  review: "待复核",
  revision_requested: "需修改",
  approved: "已批准",
  submitted: "已提交",
  completed: "已完成",
  cancelled: "已取消",
};

const NEXT_STATUS: Record<string, { status: string; label: string }[]> = {
  draft: [{ status: "preparing", label: "开始准备" }],
  preparing: [{ status: "review", label: "提交复核" }],
  review: [
    { status: "approved", label: "批准" },
    { status: "revision_requested", label: "退回修改" },
  ],
  revision_requested: [{ status: "preparing", label: "继续准备" }],
  approved: [{ status: "submitted", label: "标记已提交" }],
  submitted: [{ status: "completed", label: "标记已完成" }],
};

const REQUIREMENT_STATUS = [
  ["missing", "缺失"],
  ["collecting", "收集中"],
  ["ready", "已准备"],
  ["approved", "已核准"],
  ["not_applicable", "不适用"],
] as const;

export default function ApplicationWorkspacePage() {
  const params = useParams<{ applicationId: string }>();
  const router = useRouter();
  const applicationId = params.applicationId;
  const [application, setApplication] = useState<ApplicationDetail | null>(null);
  const [tab, setTab] = useState<Tab>("overview");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  const load = async () => {
    setApplication(await api.getApplication(applicationId));
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
          setError(loadError instanceof Error ? loadError.message : "申报工作区加载失败");
        }
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [applicationId, router]);

  const transition = async (status: string) => {
    setSaving(true);
    setError("");
    try {
      await api.updateApplicationStatus(applicationId, status);
      await load();
    } catch (updateError) {
      setError(updateError instanceof Error ? updateError.message : "状态更新失败");
    } finally {
      setSaving(false);
    }
  };

  const updateRequirement = async (requirementId: string, status: string) => {
    setSaving(true);
    setError("");
    try {
      await api.updateRequirementStatus(applicationId, requirementId, status);
      await load();
    } catch (updateError) {
      setError(updateError instanceof Error ? updateError.message : "材料状态更新失败");
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <AppShell>
        <LoadingState label="正在加载申报工作区" />
      </AppShell>
    );
  }

  if (!application) {
    return (
      <AppShell>
        <PageHeader title="申报工作区不可用" description="记录不存在、无权访问或暂时无法加载。" />
        {error && <InlineAlert>{error}</InlineAlert>}
        <ButtonLink href="/applications" variant="secondary">返回申报项目</ButtonLink>
      </AppShell>
    );
  }

  const nextStatuses = NEXT_STATUS[application.status] || [];
  const readyCount = application.requirements.filter((item) => item.status === "ready" || item.status === "approved" || item.status === "not_applicable").length;

  return (
    <AppShell>
      <PageHeader
        eyebrow="Application workspace"
        title={application.title}
        description={`${application.company_name} · 持久化申报状态、材料清单与活动记录。`}
        actions={
          <div className={flow.toolbarActions}>
            <ButtonLink href="/applications" variant="secondary">返回列表</ButtonLink>
            {nextStatuses.map((next) => (
              <Button key={next.status} type="button" variant={next.status === "revision_requested" ? "secondary" : "primary"} onClick={() => transition(next.status)} disabled={saving}>
                {next.label}
              </Button>
            ))}
          </div>
        }
      />
      {error && <InlineAlert>{error}</InlineAlert>}

      <div className={flow.metricGrid}>
        <div className={flow.metric}><strong>{application.progress}%</strong><span>工作区进度</span></div>
        <div className={flow.metric}><strong>{readyCount}/{application.requirements.length}</strong><span>材料已就绪</span></div>
        <div className={flow.metric}><strong>{application.opportunity ? `${Math.round((application.opportunity.score || 0) * 100)}%` : "—"}</strong><span>机会相关性</span></div>
        <div className={flow.metric}><Badge tone={application.status === "completed" ? "success" : "info"}>{STATUS_LABELS[application.status] || application.status}</Badge><span>项目状态</span></div>
      </div>

      <div className={flow.tabs} role="tablist" aria-label="申报工作区">
        {([
          ["overview", "Overview"],
          ["requirements", `Requirements (${application.requirements.length})`],
          ["activity", "Activity"],
        ] as const).map(([key, label]) => (
          <button key={key} type="button" role="tab" aria-selected={tab === key} className={`${flow.tab} ${tab === key ? flow.tabActive : ""}`} onClick={() => setTab(key)}>{label}</button>
        ))}
      </div>

      {tab === "overview" && (
        <div className={flow.detailGrid} role="tabpanel">
          <section className={content.card}>
            <h2>项目概览</h2>
            <dl className={flow.definitionList}>
              <div><dt>企业</dt><dd>{application.company_name}</dd></div>
              <div><dt>状态</dt><dd>{STATUS_LABELS[application.status] || application.status}</dd></div>
              <div><dt>负责人</dt><dd>{application.owner_user_id ? "当前创建人" : "未指派"}</dd></div>
              <div><dt>截止日期</dt><dd>{application.due_at ? new Date(application.due_at).toLocaleDateString("zh-CN") : "尚未设置"}</dd></div>
              <div><dt>复核状态</dt><dd>{application.review_status}</dd></div>
              <div><dt>创建时间</dt><dd>{new Date(application.created_at).toLocaleString("zh-CN")}</dd></div>
            </dl>
          </section>
          <section className={content.card}>
            <h2>机会判断</h2>
            {application.opportunity ? (
              <>
                <p className={content.cardIntro}>{application.opportunity.policy_snapshot_json.title || application.opportunity.title}</p>
                <div className={content.section}>
                  <Badge tone="neutral">{application.opportunity.eligibility_status}</Badge>
                </div>
                <div className={content.section}>
                  <ButtonLink href={`/opportunities/${application.opportunity.id}`} variant="secondary">查看机会快照</ButtonLink>
                </div>
              </>
            ) : <p className={content.cardIntro}>此项目未绑定政策机会。</p>}
          </section>
        </div>
      )}

      {tab === "requirements" && (
        <section className={content.card} role="tabpanel">
          <h2>Required Documents</h2>
          <p className={content.cardIntro}>当前清单来自扫描关键词，尚未经过 Phase 5 的政策条款与企业资料双向证据核验。</p>
          {application.requirements.length === 0 ? (
            <p className={content.cardIntro}>暂无材料要求。</p>
          ) : application.requirements.map((requirement) => (
            <div className={flow.requirement} key={requirement.id}>
              <div><strong>{requirement.title}</strong><p>{requirement.description || "无说明"}</p></div>
              <select aria-label={`更新 ${requirement.title} 的状态`} value={requirement.status} onChange={(event) => updateRequirement(requirement.id, event.target.value)} disabled={saving}>
                {REQUIREMENT_STATUS.map(([value, label]) => <option key={value} value={value}>{label}</option>)}
              </select>
            </div>
          ))}
        </section>
      )}

      {tab === "activity" && (
        <section className={content.card} role="tabpanel">
          <h2>Activity</h2>
          {application.activities.length === 0 ? <p className={content.cardIntro}>暂无活动记录。</p> : application.activities.map((activity) => (
            <div className={flow.activity} key={activity.id}><strong>{activity.summary}</strong><time>{new Date(activity.occurred_at).toLocaleString("zh-CN")}</time></div>
          ))}
        </section>
      )}
    </AppShell>
  );
}
