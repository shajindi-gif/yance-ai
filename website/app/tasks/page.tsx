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
import content from "@/components/workspace/WorkspaceContent.module.css";
import api, { type TaskSummary } from "@/lib/api";

type BadgeTone = "neutral" | "info" | "success" | "warning" | "danger";

const STATUS_MAP: Record<string, { label: string; tone: BadgeTone }> = {
  queued: { label: "排队中", tone: "warning" },
  running: { label: "执行中", tone: "info" },
  delivered: { label: "待验收", tone: "success" },
  accepted: { label: "已验收", tone: "success" },
  failed: { label: "失败", tone: "danger" },
  revision_requested: { label: "修改中", tone: "warning" },
  awaiting_payment: { label: "待支付", tone: "warning" },
};

export default function TasksPage() {
  const router = useRouter();
  const [tasks, setTasks] = useState<TaskSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!api.isAuthenticated()) {
      router.push("/login");
      return;
    }

    let cancelled = false;
    let refreshTimer: number | undefined;
    const load = async () => {
      try {
        const result = await api.getTasks();
        if (!cancelled) {
          setTasks(result);
          setError("");
          if (result.some((task) => task.status === "running" || task.status === "queued")) {
            refreshTimer = window.setTimeout(load, 5000);
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
  }, [router]);

  if (loading) {
    return (
      <AppShell>
        <LoadingState label="正在加载任务与申报" />
      </AppShell>
    );
  }

  return (
    <AppShell>
      <PageHeader
        eyebrow="Applications"
        title="任务与申报"
        description="查看真实任务状态、执行进度、版本交付与人工验收。"
      />

      {error && <InlineAlert>{error}</InlineAlert>}

      {tasks.length === 0 ? (
        <EmptyState
          icon="◎"
          title="暂无任务"
          description="先在工作台创建企业并完成一次政策扫描；任务建立后会显示在这里。"
          action={<ButtonLink href="/dashboard">返回工作台</ButtonLink>}
        />
      ) : (
        <div className={content.stack}>
          {tasks.map((task) => {
            const status = STATUS_MAP[task.status] || {
              label: task.status,
              tone: "neutral" as const,
            };
            const progress = task.progress || 0;
            const active = task.status === "running" || task.status === "queued";
            return (
              <Link key={task.id} href={`/tasks/${task.id}`} className={content.listCard}>
                <div className={content.listCardHeader}>
                  <span className={content.itemTitle}>{task.title}</span>
                  <Badge tone={status.tone}>{status.label}</Badge>
                </div>
                {active && (
                  <div className={content.progressBlock}>
                    <div className={content.progressTrack}>
                      <div className={content.progressFill} style={{ width: `${progress}%` }} />
                    </div>
                    <div className={content.progressMeta}>
                      <span>{task.current_stage || "处理中"}</span>
                      <span>{progress}%</span>
                    </div>
                  </div>
                )}
                <div className={content.meta}>
                  {new Date(task.created_at).toLocaleString("zh-CN")}
                </div>
              </Link>
            );
          })}
        </div>
      )}
    </AppShell>
  );
}
