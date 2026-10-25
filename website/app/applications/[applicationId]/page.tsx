"use client";

import { useParams, useRouter } from "next/navigation";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { ButtonLink } from "@/components/ui/ButtonLink";
import { InlineAlert } from "@/components/ui/InlineAlert";
import { LoadingState } from "@/components/ui/LoadingState";
import { PageHeader } from "@/components/ui/PageHeader";
import { ArtifactComparison } from "@/components/workspace/ArtifactComparison";
import { EvidenceMatrix } from "@/components/workspace/EvidenceMatrix";
import AppShell from "@/components/workspace/AppShell";
import flow from "@/components/workspace/CoreWorkflow.module.css";
import content from "@/components/workspace/WorkspaceContent.module.css";
import api, { type ApplicationAgentResponse, type ApplicationDetail, type DocumentRecord } from "@/lib/api";

type Tab = "matrix" | "overview" | "requirements" | "documents" | "generated" | "tasks" | "evidence" | "activity";

const STATUS_LABELS: Record<string, string> = {
  draft: "草稿", preparing: "材料准备", review: "待复核", revision_requested: "需修改",
  approved: "已批准", submitted: "已提交", completed: "已完成", cancelled: "已取消",
};
const NEXT_STATUS: Record<string, { status: string; label: string }[]> = {
  draft: [{ status: "preparing", label: "开始准备" }],
  preparing: [{ status: "review", label: "提交复核" }],
  review: [{ status: "approved", label: "批准项目" }, { status: "revision_requested", label: "退回修改" }],
  revision_requested: [{ status: "preparing", label: "继续准备" }],
  approved: [{ status: "submitted", label: "标记已提交" }, { status: "revision_requested", label: "返回修改" }],
  submitted: [{ status: "completed", label: "标记已完成" }],
};
const REQUIREMENT_STATUS = [
  ["missing", "缺失"], ["collecting", "收集中"], ["ready", "已准备"],
  ["approved", "已核准"], ["not_applicable", "不适用"],
] as const;
const TABS: { key: Tab; label: string }[] = [
  { key: "matrix", label: "资格矩阵" }, { key: "overview", label: "项目概览" }, { key: "requirements", label: "材料清单" },
  { key: "documents", label: "企业资料" }, { key: "generated", label: "工作稿" },
  { key: "tasks", label: "任务" }, { key: "evidence", label: "证据" },
  { key: "activity", label: "动态" },
];
const ARTIFACT_WRITE_STATES = new Set(["draft", "preparing", "revision_requested"]);

export default function ApplicationWorkspacePage() {
  const params = useParams<{ applicationId: string }>();
  const router = useRouter();
  const applicationId = params.applicationId;
  const [role, setRole] = useState("");
  const canEdit = ["owner", "admin", "member"].includes(role);
  const canReview = ["owner", "admin"].includes(role);
  const [application, setApplication] = useState<ApplicationDetail | null>(null);
  const [availableDocuments, setAvailableDocuments] = useState<DocumentRecord[]>([]);
  const [tab, setTab] = useState<Tab>("matrix");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [agentResult, setAgentResult] = useState<ApplicationAgentResponse | null>(null);
  const [question, setQuestion] = useState("");
  const [reviewNote, setReviewNote] = useState("");
  const commentSubmission = useRef<{ signature: string; id: string } | null>(null);
  const [comment, setComment] = useState("");
  const [proposedSummary, setProposedSummary] = useState("");
  const [commentArtifact, setCommentArtifact] = useState("");
  const [selectedDocument, setSelectedDocument] = useState("");
  const [selectedRequirement, setSelectedRequirement] = useState("");
  const [editSummary, setEditSummary] = useState("");

  const load = useCallback(async () => {
    const [workspace, documents, me] = await Promise.all([api.getApplication(applicationId), api.getDocuments(), api.getMe()]);
    setRole(me.role);
    setApplication(workspace);
    setAvailableDocuments(documents.filter((item) => !item.company_id || item.company_id === workspace.company_id));
  }, [applicationId]);

  useEffect(() => {
    if (!api.isAuthenticated()) { router.push("/login"); return; }
    let active = true;
    load().catch((loadError) => {
      if (active) setError(loadError instanceof Error ? loadError.message : "申报工作区加载失败");
    }).finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [load, router]);

  const hasUnsavedChanges = Boolean(editSummary.trim() || comment.trim() || proposedSummary.trim());
  useEffect(() => {
    if (!hasUnsavedChanges) return;
    const onUnload = (event: BeforeUnloadEvent) => { event.preventDefault(); event.returnValue = ''; };
    const onLink = (event: MouseEvent) => {
      if (!(event.target instanceof Element)) return;
      const anchor = event.target.closest('a[href]') as HTMLAnchorElement | null;
      if (!anchor || anchor.target === '_blank' || anchor.hasAttribute('download')) return;
      const target = new URL(anchor.href);
      if (target.pathname === location.pathname && target.origin === location.origin) return;
      if (!window.confirm('还有未保存的摘要或评论。确认离开当前项目？')) { event.preventDefault(); event.stopPropagation(); }
    };
    window.addEventListener('beforeunload', onUnload);
    document.addEventListener('click', onLink, true);
    return () => { window.removeEventListener('beforeunload', onUnload); document.removeEventListener('click', onLink, true); };
  }, [hasUnsavedChanges]);

  const latestArtifact = application?.generated[0] || null;
  const canWriteArtifacts = application ? canEdit && ARTIFACT_WRITE_STATES.has(application.status) : false;
  const canFixArtifact = Boolean(
    canEdit && application?.status === "revision_requested" && latestArtifact?.status === "rejected",
  );
  const linkedDocumentIds = useMemo(
    () => new Set(application?.documents.map((item) => item.document_id) || []),
    [application?.documents],
  );

  const perform = async (operation: () => Promise<unknown>, fallback: string) => {
    setSaving(true); setError("");
    try { await operation(); await load(); }
    catch (operationError) { setError(operationError instanceof Error ? operationError.message : fallback); }
    finally { setSaving(false); }
  };
  const transition = (status: string) => perform(() => api.updateApplicationStatus(applicationId, status), "状态更新失败");
  const updateRequirement = (requirementId: string, status: string) => perform(() => api.updateRequirementStatus(applicationId, requirementId, status), "材料状态更新失败");

  const runAgentAction = async (action: ApplicationAgentResponse["action"]) => {
    setSaving(true); setError("");
    try {
      const result = await api.runApplicationAction(applicationId, action, {
        question: action === "ask" ? question : undefined,
        instruction: action === "fix" ? reviewNote : undefined,
      });
      setAgentResult(result); await load();
      if (result.artifact) setTab("generated");
    } catch (actionError) { setError(actionError instanceof Error ? actionError.message : "工作区动作执行失败"); }
    finally { setSaving(false); }
  };

  const download = async (artifactId: string, format: "docx" | "pdf" | "xlsx" | "json") => {
    setSaving(true); setError("");
    try {
      const blob = await api.downloadApplicationArtifact(applicationId, artifactId, format);
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = url; anchor.download = `${application?.title || "application"}.${format}`; anchor.click();
      URL.revokeObjectURL(url);
    } catch (downloadError) { setError(downloadError instanceof Error ? downloadError.message : "文件下载失败"); }
    finally { setSaving(false); }
  };

  if (loading) return <AppShell><LoadingState label="正在加载申报工作区" /></AppShell>;
  if (!application) return <AppShell><PageHeader title="申报工作区不可用" description="记录不存在、无权访问或暂时无法加载。" />{error ? <InlineAlert>{error}</InlineAlert> : null}<ButtonLink href="/applications" variant="secondary">返回申报项目</ButtonLink></AppShell>;

  return <AppShell>
    <PageHeader eyebrow="项目 / 证据工作台" title={application.title} description={`${application.company_name} · 证据、材料、版本、任务与客户复核均保存在同一工作区。`} actions={<div className={flow.toolbarActions}><ButtonLink href="/applications" variant="secondary">返回列表</ButtonLink>{(NEXT_STATUS[application.status] || []).map((next) => <Button key={next.status} type="button" variant={next.status === "revision_requested" ? "secondary" : "primary"} onClick={() => transition(next.status)} disabled={!canEdit || saving || (next.status === "approved" && !canReview)}>{next.label}</Button>)}</div>} />
    <p className={content.cardIntro}>企业资料由客户提供；请由客户本人或其授权成员核对政策原文、事实与材料。客户确认不代表政府认定或获批。</p>
    {!canEdit ? <InlineAlert tone="info">当前为只读成员：可查看资料与工作稿，无法编辑、评论或审批。</InlineAlert> : !canReview ? <InlineAlert tone="info">当前可编辑材料；批准和退回工作稿需由客户团队管理员操作；衍策不提供人工业务审核。</InlineAlert> : null}
    {error ? <InlineAlert tone="error">{error}</InlineAlert> : null}
    <div className={`${flow.metricGrid} ${flow.projectMetrics}`}>
      <div className={flow.metric}><strong>{application.progress}%</strong><span>工作区进度</span></div>
      <div className={flow.metric}><strong>{application.readiness.requirement_ready}/{application.requirements.length}</strong><span>材料已就绪</span></div>
      <div className={flow.metric}><strong>{application.readiness.verified_evidence}</strong><span>已核验证据</span></div>
      <div className={flow.metric}><Badge tone={application.status === "completed" ? "success" : "info"}>{STATUS_LABELS[application.status] || application.status}</Badge><span>项目状态</span></div>
    </div>
    <div className={flow.workspaceBody}>
      <nav className={flow.stageNavigation} aria-label="项目工作内容">
        <span className={flow.stageLabel}>项目工作内容</span>
        <div className={flow.tabs} role="tablist" aria-label="申报工作区">{TABS.map(({ key, label }, index) => <button key={key} id={`application-tab-${key}`} aria-controls={`application-panel-${key}`} tabIndex={tab === key ? 0 : -1} type="button" role="tab" aria-selected={tab === key} className={`${flow.tab} ${tab === key ? flow.tabActive : ""}`} onClick={() => setTab(key)} onKeyDown={event => {
          const offset = ['ArrowRight', 'ArrowDown'].includes(event.key) ? 1 : ['ArrowLeft', 'ArrowUp'].includes(event.key) ? -1 : 0;
          if (!offset && !['Home', 'End'].includes(event.key)) return;
          event.preventDefault();
          const next = event.key === 'Home' ? TABS[0] : event.key === 'End' ? TABS[TABS.length - 1] : TABS[(index + offset + TABS.length) % TABS.length];
          setTab(next.key); document.getElementById(`application-tab-${next.key}`)?.focus();
        }}><span aria-hidden="true">{String(index + 1).padStart(2, '0')}</span>{label}{key === "requirements" ? ` (${application.requirements.length})` : key === "generated" ? ` (${application.generated.length})` : ""}</button>)}</div>
        <p className={flow.stageNote}>工作内容可随时切换。复核与导出取决于实际证据、版本和权限。</p>
      </nav>
    <div className={`${flow.applicationLayout} ${tab === "matrix" ? flow.evidenceLayout : ""}`}>

      <div className={flow.applicationMain} role="tabpanel" id={`application-panel-${tab}`} aria-labelledby={`application-tab-${tab}`} tabIndex={0}>


        {tab === "matrix" ? <EvidenceMatrix matrix={application.evidence_matrix} busy={saving} canWrite={canWriteArtifacts} onCollect={() => perform(async () => { await api.createEvidenceTasks(applicationId); setTab("requirements"); }, "创建补证待办失败")} /> : null}
        {tab === "overview" ? <div className={flow.gridTwo}><section className={content.card}><h2>项目概览</h2><dl className={flow.definitionList}><div><dt>企业</dt><dd>{application.company_name}</dd></div><div><dt>状态</dt><dd>{STATUS_LABELS[application.status] || application.status}</dd></div><div><dt>截止日期</dt><dd>{application.due_at ? new Date(application.due_at).toLocaleDateString("zh-CN") : "尚未设置"}</dd></div><div><dt>复核状态</dt><dd>{application.review_status}</dd></div><div><dt>资料关联</dt><dd>{application.documents.length} 份</dd></div><div><dt>工作稿版本</dt><dd>{latestArtifact ? `v${latestArtifact.version}` : "尚未生成"}</dd></div></dl></section><section className={content.card}><h2>复核准备情况</h2><Badge tone={application.readiness.can_submit_for_review ? "success" : "warning"}>{application.readiness.can_submit_for_review ? "可提交复核" : "仍有阻塞项"}</Badge><div className={flow.gapList}>{application.readiness.blockers.length ? application.readiness.blockers.map((item) => <span key={item}>• {item}</span>) : <span>资格与硬门槛检查已通过。</span>}</div></section></div> : null}

        {tab === "requirements" ? <section className={content.card}><h2>补证与材料清单</h2><p className={content.cardIntro}>政策来源清单保留条款证据；关键词候选项会继续标注为未核验。</p>{application.requirements.length === 0 ? <p className={content.cardIntro}>暂无材料要求。</p> : application.requirements.map((item) => <div className={flow.requirement} key={item.id}><div><strong>{item.title}</strong><p>{item.description || "无说明"}</p><div className={flow.inlineMeta}>{item.is_hard_gate ? <Badge tone="warning">硬门槛</Badge> : null}<Badge tone={item.source.policy_version_id ? "success" : "neutral"}>{item.source.policy_version_id ? "政策原文" : "候选项"}</Badge></div></div><select aria-label={`更新 ${item.title} 的状态`} value={item.status} onChange={(event) => updateRequirement(item.id, event.target.value)} disabled={!canEdit || saving}>{REQUIREMENT_STATUS.map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></div>)}</section> : null}

        {tab === "documents" ? <section className={content.card}><h2>企业资料</h2><p className={content.cardIntro}>只显示真实上传与摄取状态；关联不代表内容已经解析。</p><div className={flow.linkDocumentForm}><select disabled={!canEdit} aria-label="选择企业资料" value={selectedDocument} onChange={(event) => setSelectedDocument(event.target.value)}><option value="">选择尚未关联的资料</option>{availableDocuments.filter((item) => !linkedDocumentIds.has(item.id)).map((item) => <option key={item.id} value={item.id}>{item.filename}</option>)}</select><select disabled={!canEdit} aria-label="关联材料要求" value={selectedRequirement} onChange={(event) => setSelectedRequirement(event.target.value)}><option value="">不关联特定要求</option>{application.requirements.map((item) => <option key={item.id} value={item.id}>{item.title}</option>)}</select><Button type="button" onClick={() => perform(() => api.linkApplicationDocument(applicationId, selectedDocument, selectedRequirement || undefined), "资料关联失败")} disabled={!canEdit || saving || !selectedDocument}>关联资料</Button></div>{application.documents.length === 0 ? <p className={content.cardIntro}>暂无已关联资料。</p> : application.documents.map((item) => <div className={flow.requirement} key={item.link_id}><div><strong>{item.filename}</strong><p>{item.content_type}</p></div><div className={flow.inlineMeta}><Badge tone={item.status === "uploaded" ? "success" : "neutral"}>{item.status}</Badge><Badge tone="neutral">摄取：{item.ingestion_status}</Badge></div></div>)}</section> : null}

        {tab === "generated" ? <section className={content.card}><div className={flow.sectionHeading}><div><h2>材料工作稿</h2><p className={content.cardIntro}>生成、修复或编辑都会创建新版本，旧版本不会被覆盖。</p></div><Button type="button" onClick={() => runAgentAction("generate")} disabled={!canEdit || saving || !canWriteArtifacts}>重新生成</Button></div><ArtifactComparison artifacts={application.generated} />{application.generated.length === 0 ? <p className={content.cardIntro}>尚无工作稿。可使用“起草材料”创建证据型工作稿。</p> : application.generated.map((artifact, index) => <article className={flow.artifactCard} key={artifact.id}><div><strong>{artifact.title}</strong><p>v{artifact.version} · {artifact.generation_method} · 校验和 {artifact.checksum_sha256.slice(0, 12)}</p></div>{artifact.source_state && !artifact.source_state.current ? <InlineAlert tone="info">来源需重新复核：{artifact.source_state.reasons.join("；")}</InlineAlert> : null}<div className={flow.inlineMeta}><Badge tone={artifact.status === "approved" ? "success" : artifact.status === "rejected" ? "danger" : "neutral"}>{artifact.status}</Badge>{(["docx", "pdf", "xlsx", "json"] as const).map((format) => <button className={flow.textButton} type="button" key={format} onClick={() => download(artifact.id, format)} disabled={saving}>{format.toUpperCase()}</button>)}</div>{index === 0 ? <div className={flow.artifactActions}><textarea disabled={!canEdit} aria-label="人工编辑摘要" value={editSummary} placeholder={String(artifact.content.executive_summary || "编辑摘要后创建新版本")} onChange={(event) => setEditSummary(event.target.value)} /><Button type="button" variant="secondary" disabled={!canEdit || saving || !canWriteArtifacts || !editSummary.trim()} onClick={() => perform(async () => { await api.editApplicationArtifact(applicationId, artifact.id, editSummary); setEditSummary(""); }, "编辑失败")}>保存为新版本</Button><Button type="button" variant="secondary" disabled={!canReview || saving || application.status !== "review" || !reviewNote.trim()} onClick={() => perform(() => api.reviewApplicationArtifact(applicationId, artifact.id, "reject", reviewNote), "退回失败")}>退回修改</Button><Button type="button" disabled={!canReview || saving || application.status !== "review" || artifact.source_state?.current === false} onClick={() => perform(() => api.reviewApplicationArtifact(applicationId, artifact.id, "approve", reviewNote), "批准失败")}>批准工作稿</Button></div> : null}</article>)}</section> : null}

        {tab === "tasks" ? <section className={content.card}><h2>执行任务</h2>{application.tasks.length === 0 ? <p className={content.cardIntro}>暂无执行任务。</p> : application.tasks.map((task) => <div className={flow.requirement} key={task.id}><div><strong>{task.title}</strong><p>{task.current_stage || "未设置阶段"}</p></div><Badge tone="neutral">{task.status} · {task.progress}%</Badge></div>)}</section> : null}
        {tab === "evidence" ? <section className={content.card}><h2>原文与证据</h2>{application.evidence.length === 0 ? <p className={content.cardIntro}>暂无可核验证据，不会展示无来源结论。</p> : application.evidence.map((item) => <blockquote className={flow.evidenceQuote} key={item.id}><p>“{item.quote}”</p><footer>{[item.issuer, item.article].filter(Boolean).join(" · ") || item.source_title}<Badge tone={item.verified ? "success" : "warning"}>{item.verified ? "原文已核验" : "未核验"}</Badge></footer></blockquote>)}</section> : null}
        {tab === "activity" ? <section className={content.card}><h2>协作评论与动态</h2><div className={flow.commentForm}><label>评论关联<select disabled={!canEdit} aria-label="评论关联版本" value={commentArtifact} onChange={event => setCommentArtifact(event.target.value)}><option value="">项目整体</option>{application.generated.map(item => <option key={item.id} value={item.id}>工作稿 v{item.version} · {item.title}</option>)}</select></label><textarea aria-label="建议替换摘要（可选）" placeholder="可选：建议替换的完整摘要；先选择关联版本" value={proposedSummary} disabled={!canEdit || !commentArtifact} onChange={event => setProposedSummary(event.target.value)} /><textarea disabled={!canEdit} value={comment} onChange={(event) => setComment(event.target.value)} placeholder="添加协作评论" aria-label="添加协作评论" /><Button type="button" disabled={!canEdit || saving || !comment.trim()} onClick={() => perform(async () => { const proposal = commentArtifact && proposedSummary.trim() ? proposedSummary : undefined; const signature = JSON.stringify([applicationId, comment, commentArtifact, proposal]); if (commentSubmission.current?.signature !== signature) commentSubmission.current = {signature, id: crypto.randomUUID()}; await api.addApplicationComment(applicationId, comment, commentArtifact || undefined, proposal, commentSubmission.current.id); commentSubmission.current = null; setComment(""); setProposedSummary(""); }, "评论提交失败")}>发送</Button></div>{application.comments.map((item) => <div className={flow.comment} key={item.id}><strong>工作区成员 · {item.artifact_id ? `工作稿 v${application.generated.find(draft => draft.id === item.artifact_id)?.version ?? "（历史版本）"}` : "项目整体"}</strong><p>{item.body}</p>{item.proposed_summary ? <div><p>建议替换摘要：{item.proposed_summary}</p>{item.resolution ? <p>{item.resolution.decision === "accept" ? "已接受并生成新稿，仍须人工复核" : "已拒绝"}</p> : <div><p>接受会生成新工作稿并使用一次文档额度，不代表批准或提交。</p><Button type="button" disabled={!canEdit || saving} onClick={() => perform(() => api.decideSuggestion(applicationId, item.id, "accept"), "接受失败；请核对版本与来源")}>接受摘要建议</Button><Button type="button" variant="secondary" disabled={!canEdit || saving} onClick={() => perform(() => api.decideSuggestion(applicationId, item.id, "reject"), "拒绝失败")}>拒绝建议</Button></div>}</div> : null}<time>{new Date(item.created_at).toLocaleString("zh-CN")}</time></div>)}{application.activities.map((activity) => <div className={flow.activity} key={activity.id}><strong>{activity.summary}</strong><time>{new Date(activity.occurred_at).toLocaleString("zh-CN")}</time></div>)}</section> : null}
      </div>

      <aside className={flow.agentPanel} aria-label="项目证据助手"><div className={flow.agentHeader}><div><span>项目辅助</span><strong>依据当前证据工作</strong></div><Badge tone="success">可用</Badge></div><p>根据当前工作区的事实和原文整理材料与解释；结果绑定具体证据版本。</p><textarea disabled={!canEdit} value={question} onChange={(event) => setQuestion(event.target.value)} placeholder="询问资格、材料或下一步" aria-label="询问工作区" /><div className={flow.agentActions}><Button type="button" variant="secondary" onClick={() => runAgentAction("ask")} disabled={!canEdit || saving || !question.trim()}>询问</Button><Button type="button" onClick={() => runAgentAction("generate")} disabled={!canEdit || saving || !canWriteArtifacts}>起草材料</Button><Button type="button" variant="secondary" onClick={() => runAgentAction("check")} disabled={!canEdit || saving}>检查缺口</Button><Button type="button" variant="secondary" onClick={() => runAgentAction("fix")} disabled={!canEdit || saving || !canFixArtifact || (!reviewNote.trim() && !latestArtifact?.review_note)}>按意见修订</Button><Button type="button" variant="secondary" onClick={() => runAgentAction("explain")} disabled={!canEdit || saving}>解释依据</Button></div><textarea disabled={!canEdit} value={reviewNote} onChange={(event) => setReviewNote(event.target.value)} placeholder="客户复核意见或修订要求" aria-label="复核意见" />{agentResult ? <div className={flow.agentResult}><strong>{agentResult.action.toUpperCase()}</strong><p>{agentResult.message}</p>{agentResult.readiness?.blockers.map((item) => <span key={item}>• {item}</span>)}</div> : <p className={flow.agentEmpty}>尚无本次会话结果。</p>}</aside>
    </div>
    </div>
  </AppShell>;
}
