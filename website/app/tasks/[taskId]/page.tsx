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
import content from "@/components/workspace/WorkspaceContent.module.css";
import api, { type NextAction, type TaskDetail } from "@/lib/api";

const STAGES = [
  { key: 10, label: "企业画像读取" },
  { key: 30, label: "政策检索与匹配" },
  { key: 60, label: "申报条件分析" },
  { key: 80, label: "报告文件生成" },
  { key: 100, label: "交付物生成" },
];

type BadgeTone = "neutral" | "info" | "success" | "warning" | "danger";

const STATUS_MAP: Record<string, { label: string; tone: BadgeTone }> = {
  queued: { label: "排队中", tone: "warning" },
  running: { label: "执行中", tone: "info" },
  delivered: { label: "待验收", tone: "success" },
  accepted: { label: "已验收", tone: "success" },
  failed: { label: "执行失败", tone: "danger" },
  revision_requested: { label: "修改中", tone: "warning" },
};

export default function TaskDetailPage() {
  const params = useParams<{ taskId: string }>();
  const router = useRouter();
  const taskId = params.taskId;
  const [task, setTask] = useState<TaskDetail | null>(null);
  const [actions, setActions] = useState<NextAction[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [downloading, setDownloading] = useState(false);
  const [revisionOpen, setRevisionOpen] = useState(false);
  const [revisionText, setRevisionText] = useState("");
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (!api.isAuthenticated()) {
      router.push("/login");
      return;
    }

    let cancelled = false;
    let refreshTimer: number | undefined;
    const load = async () => {
      try {
        const result = await api.getTask(taskId);
        if (!cancelled) {
          setTask(result);
          setError("");
          if (result.status === "running" || result.status === "queued") {
            refreshTimer = window.setTimeout(load, 3000);
          }
        }
      } catch (loadError) {
        if (!cancelled) {
          setError(loadError instanceof Error ? loadError.message : "任务加载失败");
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    };

    void load();
    return () => {
      cancelled = true;
      if (refreshTimer) window.clearTimeout(refreshTimer);
    };
  }, [router, taskId]);

  useEffect(() => {
    if (!task || (task.status !== "delivered" && task.status !== "accepted")) return;
    let cancelled = false;
    api
      .getNextActions(taskId)
      .then((result) => {
        if (!cancelled) setActions(result);
      })
      .catch(() => {
        if (!cancelled) setActions([]);
      });
    return () => {
      cancelled = true;
    };
  }, [task?.status, taskId]);

  const handleDownload = async () => {
    setDownloading(true);
    setError("");
    try {
      const blob = await api.downloadTask(taskId);
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = "政策分析报告.pdf";
      anchor.click();
      URL.revokeObjectURL(url);
    } catch (downloadError) {
      setError(downloadError instanceof Error ? downloadError.message : "交付物下载失败");
    } finally {
      setDownloading(false);
    }
  };

  const handleAccept = async () => {
    setSubmitting(true);
    setError("");
    try {
      await api.acceptTask(taskId);
      setTask((current) => (current ? { ...current, status: "accepted" } : current));
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : "验收失败");
    } finally {
      setSubmitting(false);
    }
  };

  const handleRevision = async () => {
    const deliverable = task?.deliverables[0];
    if (!deliverable || revisionText.trim().length < 5) {
      setError("请填写至少 5 个字符的具体修改要求");
      return;
    }
    setSubmitting(true);
    setError("");
    try {
      await api.requestTaskRevision(taskId, deliverable.id, revisionText.trim());
      setTask((current) =>
        current ? { ...current, status: "revision_requested" } : current,
      );
      setRevisionOpen(false);
      setRevisionText("");
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : "修改请求提交失败");
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) {
    return (
      <AppShell>
        <LoadingState label="正在加载任务详情" />
      </AppShell>
    );
  }

  if (!task) {
    return (
      <AppShell>
        <PageHeader title="任务不可用" description="该任务不存在、无权访问或暂时无法加载。" />
        {error && <InlineAlert>{error}</InlineAlert>}
        <ButtonLink href="/tasks" variant="secondary">
          返回任务列表
        </ButtonLink>
      </AppShell>
    );
  }

  const running = task.status === "running" || task.status === "queued";
  const done = task.status === "delivered" || task.status === "accepted";
  const progress = task.progress || 0;
  const status = STATUS_MAP[task.status] || { label: task.status, tone: "neutral" as const };

  return (
    <AppShell>
      <PageHeader
        eyebrow="Application task"
        title={task.title}
        description="查看当前执行状态、交付版本和真实执行记录。关键材料必须由用户验收。"
        actions={
          <ButtonLink href="/tasks" variant="secondary">
            返回列表
          </ButtonLink>
        }
      />

      {error && <InlineAlert>{error}</InlineAlert>}

      <div className={content.stack}>
        <section className={content.card}>
          <div className={content.cardHeader}>
            <div>
              <h1>{task.company_name || "未命名企业"}</h1>
              <div className={content.detailMeta}>
                <span>Task ID: {task.id}</span>
                <span>{new Date(task.created_at).toLocaleString("zh-CN")}</span>
              </div>
            </div>
            <Badge tone={status.tone}>{status.label}</Badge>
          </div>
          {task.description && <p className={content.cardIntro}>{task.description}</p>}
        </section>

        {(running || done) && (
          <section className={content.card}>
            <div className={content.rowBetween}>
              <h2>执行进度</h2>
              <span className={content.amount}>{progress}%</span>
            </div>
            <div className={content.progressBlock}>
              <div className={content.progressTrack}>
                <div className={content.progressFill} style={{ width: `${progress}%` }} />
              </div>
              <div className={content.progressMeta}>
                <span>{task.current_stage || (done ? "已完成" : "处理中")}</span>
                {running && <span>页面每 3 秒刷新</span>}
              </div>
            </div>
            <div className={content.stageList}>
              {STAGES.map((stage, index) => {
                const stageDone = progress >= stage.key;
                const stageActive =
                  !stageDone && progress >= (STAGES[index - 1]?.key || 0);
                return (
                  <div
                    key={stage.key}
                    className={`${content.stage} ${
                      stageDone ? content.stageDone : stageActive ? content.stageActive : ""
                    }`}
                  >
                    <span className={content.stageDot}>
                      {stageDone ? "✓" : stageActive ? "●" : "○"}
                    </span>
                    <span>{stage.label}</span>
                  </div>
                );
              })}
            </div>
          </section>
        )}

        {done && task.deliverables.length > 0 && (
          <section className={content.card}>
            <h2>交付物</h2>
            {task.deliverables.map((deliverable) => (
              <div key={deliverable.id} className={content.deliverableRow}>
                <div>
                  <strong>
                    {deliverable.title} · V{deliverable.version}
                  </strong>
                  <small>
                    {deliverable.generated_at
                      ? new Date(deliverable.generated_at).toLocaleString("zh-CN")
                      : "生成时间未记录"}
                    {deliverable.quality_score !== null
                      ? ` · 已记录评测分 ${deliverable.quality_score}`
                      : " · 尚无评测数据"}
                  </small>
                </div>
                <Button type="button" onClick={handleDownload} disabled={downloading}>
                  {downloading ? "下载中…" : "下载 PDF"}
                </Button>
              </div>
            ))}

            {task.status === "delivered" && (
              <>
                <div className={content.actionRow}>
                  <Button type="button" onClick={handleAccept} disabled={submitting}>
                    确认验收
                  </Button>
                  <Button
                    type="button"
                    variant="secondary"
                    onClick={() => setRevisionOpen((open) => !open)}
                    disabled={submitting}
                  >
                    提交修改要求
                  </Button>
                </div>
                {revisionOpen && (
                  <div className={content.revisionForm}>
                    <label htmlFor="revision-request">具体修改要求</label>
                    <textarea
                      id="revision-request"
                      value={revisionText}
                      onChange={(event) => setRevisionText(event.target.value)}
                      maxLength={2000}
                      placeholder="说明需要调整的章节、事实、措辞或证据。"
                    />
                    <div className={content.formActions}>
                      <Button
                        type="button"
                        variant="secondary"
                        onClick={() => setRevisionOpen(false)}
                      >
                        取消
                      </Button>
                      <Button type="button" onClick={handleRevision} disabled={submitting}>
                        {submitting ? "提交中…" : "提交修改"}
                      </Button>
                    </div>
                  </div>
                )}
              </>
            )}
          </section>
        )}

        {done && actions.length > 0 && (
          <section className={content.card}>
            <h2>Next Best Action</h2>
            <p className={content.cardIntro}>由当前规则结果生成，具体资格仍需核对政策原文。</p>
            {actions.map((action, index) => (
              <div key={`${action.action}-${index}`} className={content.nextAction}>
                <div>
                  <strong>
                    {index + 1}. {action.action}
                  </strong>
                  <small>{action.desc}</small>
                </div>
                {action.href ? (
                  <ButtonLink href={action.href} variant="secondary">
                    {action.cta}
                  </ButtonLink>
                ) : action.product_code ? (
                  <ButtonLink href="/pricing" variant="secondary">
                    查看服务范围
                  </ButtonLink>
                ) : (
                  <Badge tone="neutral">{action.cta}</Badge>
                )}
              </div>
            ))}
          </section>
        )}

        {task.agent_runs.length > 0 && (
          <section className={content.card}>
            <h2>执行记录</h2>
            <p className={content.cardIntro}>仅展示服务端已持久化的运行状态和延迟。</p>
            {task.agent_runs.map((run, index) => (
              <div key={`${run.agent}-${index}`} className={content.activityRow}>
                <span className={content.activityStatus} aria-hidden="true">
                  {run.status === "completed" ? "✓" : "●"}
                </span>
                <span>{run.agent}</span>
                <Badge tone={run.status === "completed" ? "success" : "info"}>
                  {run.status}
                </Badge>
                {run.latency_ms != null && (
                  <span className={content.activityLatency}>{run.latency_ms} ms</span>
                )}
              </div>
            ))}
          </section>
        )}
      </div>
    </AppShell>
  );
}
