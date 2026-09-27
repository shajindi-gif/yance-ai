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
import api, { type ApplicationSummary, type MilestoneItem } from "@/lib/api";

const STAGES: { key: string; label: string; statuses: string[] }[] = [
  { key: "pipeline", label: "准备中", statuses: ["draft", "preparing", "revision_requested"] },
  { key: "review", label: "评审/就绪", statuses: ["review", "approved"] },
  { key: "submitted", label: "已提交", statuses: ["submitted"] },
  { key: "awarded", label: "获批/执行", statuses: ["completed"] },
];

const MILESTONE_TONE = { todo: "neutral", doing: "info", done: "success", blocked: "danger" } as const;

export default function ProjectsPage() {
  const [applications, setApplications] = useState<ApplicationSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [selectedId, setSelectedId] = useState("");
  const [milestones, setMilestones] = useState<MilestoneItem[]>([]);
  const [milestoneLoading, setMilestoneLoading] = useState(false);
  const [newTitle, setNewTitle] = useState("");
  const [newDue, setNewDue] = useState("");

  const load = useCallback(async () => {
    setError("");
    try {
      const rows = await api.getApplications();
      setApplications(rows);
      setSelectedId((current) => current || (rows[0]?.id ?? ""));
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : "项目加载失败");
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

  const loadMilestones = useCallback(async (applicationId: string) => {
    if (!applicationId) {
      setMilestones([]);
      return;
    }
    setMilestoneLoading(true);
    try {
      setMilestones(await api.listMilestones(applicationId));
    } catch {
      setMilestones([]);
    } finally {
      setMilestoneLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadMilestones(selectedId);
  }, [selectedId, loadMilestones]);

  const grouped = useMemo(
    () =>
      STAGES.map((stage) => ({
        ...stage,
        items: applications.filter((application) => stage.statuses.includes(application.status)),
      })),
    [applications],
  );

  const addMilestone = async () => {
    if (!selectedId || newTitle.trim().length < 2) return;
    try {
      await api.createMilestone(selectedId, {
        title: newTitle.trim(),
        due_at: newDue ? new Date(newDue).toISOString() : null,
      });
      setNewTitle("");
      setNewDue("");
      await loadMilestones(selectedId);
    } catch (addError) {
      setError(addError instanceof Error ? addError.message : "添加失败");
    }
  };

  const cycleStatus = async (milestone: MilestoneItem) => {
    const next = milestone.status === "todo" ? "doing" : milestone.status === "doing" ? "done" : "todo";
    try {
      await api.updateMilestone(milestone.id, { status: next });
      await loadMilestones(selectedId);
    } catch (cycleError) {
      setError(cycleError instanceof Error ? cycleError.message : "更新失败");
    }
  };

  if (loading) return <AppShell><LoadingState label="正在加载项目管道" /></AppShell>;

  const selected = applications.find((application) => application.id === selectedId);

  return (
    <AppShell>
      <PageHeader
        eyebrow="Projects"
        title="项目管道"
        description="从准备到获批后管理的完整生命周期。获批（完成）的申报进入验收里程碑管理。"
      />
      {error ? <InlineAlert tone="error">{error}</InlineAlert> : null}
      {applications.length === 0 ? (
        <EmptyState
          icon="—"
          title="还没有申报项目"
          description="从「我的机会」选择符合条件的政策创建申报，管道与里程碑管理会自动开启。"
          action={<Link href="/opportunities" className={flow.link}>去创建</Link>}
        />
      ) : (
        <>
          <div className={flow.gridTwo}>
            {grouped.map((stage) => (
              <section key={stage.key} className={content.card}>
                <div className={content.cardHeader}>
                  <strong>{stage.label}</strong>
                  <Badge tone="neutral">{stage.items.length}</Badge>
                </div>
                {stage.items.length === 0 ? (
                  <div className={content.subtle} style={{ fontSize: 13, padding: "8px 0" }}>暂无</div>
                ) : (
                  <div className={content.rows}>
                    {stage.items.map((application) => (
                      <button
                        key={application.id}
                        type="button"
                        onClick={() => setSelectedId(application.id)}
                        className={content.row}
                        style={{
                          textAlign: "left",
                          cursor: "pointer",
                          border: selectedId === application.id ? "1px solid #126a9a" : undefined,
                          background: selectedId === application.id ? "#f2f8fc" : undefined,
                        }}
                      >
                        <div style={{ minWidth: 0 }}>
                          <strong>{application.title}</strong>
                          <div className={content.subtle} style={{ fontSize: 12 }}>
                            {application.due_at
                              ? `截止 ${new Date(application.due_at).toLocaleDateString("zh-CN")}`
                              : "未设截止日"}
                            {` · 进度 ${application.progress ?? 0}%`}
                          </div>
                        </div>
                        <Badge tone={stage.key === "submitted" ? "info" : stage.key === "awarded" ? "success" : "warning"}>
                          {application.status}
                        </Badge>
                      </button>
                    ))}
                  </div>
                )}
              </section>
            ))}
          </div>

          {selected ? (
            <section className={content.card} style={{ marginTop: 20 }}>
              <div className={content.cardHeader}>
                <div>
                  <strong>里程碑 · {selected.title}</strong>
                  <div className={content.subtle} style={{ fontSize: 12, marginTop: 4 }}>
                    {selected.status === "completed" || selected.status === "submitted"
                      ? "获批/提交后在此管理验收材料、报告义务与拨款节点。"
                      : "为准备过程添加可跟踪的节点，截止提醒会自动进入通知。"}
                  </div>
                </div>
                <Link href={`/applications/${selected.id}`} className={flow.link}>
                  进入申报工作区
                </Link>
              </div>
              <div style={{ display: "flex", gap: 10, flexWrap: "wrap", marginBottom: 14 }}>
                <input
                  value={newTitle}
                  onChange={(event) => setNewTitle(event.target.value)}
                  placeholder="里程碑名称（如：提交软著申请）"
                  style={{ flex: 1, minWidth: 220, padding: "10px 12px", border: "1px solid #dde3eb", borderRadius: 8, fontSize: 13 }}
                />
                <input
                  type="date"
                  value={newDue}
                  onChange={(event) => setNewDue(event.target.value)}
                  aria-label="计划完成日期"
                  style={{ padding: "9px 12px", border: "1px solid #dde3eb", borderRadius: 8, fontSize: 13 }}
                />
                <Button onClick={addMilestone} disabled={newTitle.trim().length < 2}>添加</Button>
              </div>
              {milestoneLoading ? (
                <div className={content.subtle} style={{ fontSize: 13 }}>加载里程碑…</div>
              ) : milestones.length === 0 ? (
                <div className={content.subtle} style={{ fontSize: 13 }}>暂无里程碑。</div>
              ) : (
                <div className={content.rows}>
                  {milestones.map((milestone) => (
                    <div key={milestone.id} className={content.row}>
                      <div style={{ minWidth: 0 }}>
                        <strong style={{ textDecoration: milestone.status === "done" ? "line-through" : undefined }}>
                          {milestone.title}
                        </strong>
                        <div className={content.subtle} style={{ fontSize: 12 }}>
                          {milestone.due_at ? `计划 ${new Date(milestone.due_at).toLocaleDateString("zh-CN")}` : "无期限"}
                          {milestone.completion_note ? ` · ${milestone.completion_note}` : ""}
                        </div>
                      </div>
                      <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
                        <Badge tone={MILESTONE_TONE[milestone.status] || "neutral"}>{milestone.status}</Badge>
                        <Button variant="secondary" onClick={() => void cycleStatus(milestone)}>
                          {milestone.status === "todo" ? "开始" : milestone.status === "doing" ? "完成" : "重开"}
                        </Button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </section>
          ) : null}
        </>
      )}
    </AppShell>
  );
}
