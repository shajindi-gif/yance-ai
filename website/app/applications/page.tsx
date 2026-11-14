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
import api, { type ApplicationSummary } from "@/lib/api";

const STATUS: Record<string, { label: string; tone: "neutral" | "info" | "success" | "warning" | "danger" }> = {
  draft: { label: "草稿", tone: "neutral" },
  preparing: { label: "材料准备", tone: "info" },
  review: { label: "待复核", tone: "warning" },
  revision_requested: { label: "需修改", tone: "warning" },
  approved: { label: "已批准", tone: "success" },
  submitted: { label: "已提交", tone: "info" },
  completed: { label: "已完成", tone: "success" },
  cancelled: { label: "已取消", tone: "danger" },
};

export default function ApplicationsPage() {
  const router = useRouter();
  const [applications, setApplications] = useState<ApplicationSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!api.isAuthenticated()) {
      router.push("/login");
      return;
    }
    let active = true;
    api
      .getApplications()
      .then((result) => {
        if (active) setApplications(result);
      })
      .catch((loadError) => {
        if (active) {
          setError(loadError instanceof Error ? loadError.message : "申报项目加载失败");
        }
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
        <LoadingState label="正在加载申报项目" />
      </AppShell>
    );
  }

  return (
    <AppShell>
      <PageHeader
        eyebrow="Applications"
        title="申报项目"
        description="每个工作区绑定一项真实政策机会，并保留材料状态和活动历史。"
      />
      {error && <InlineAlert>{error}</InlineAlert>}
      {applications.length === 0 ? (
        <EmptyState
          icon="▣"
          title="暂无申报项目"
          description="从一项政策机会开始申报，系统会创建持久工作区。"
          action={<ButtonLink href="/opportunities">查看政策机会</ButtonLink>}
        />
      ) : (
        <div className={content.stack}>
          {applications.map((application) => {
            const status = STATUS[application.status] || { label: application.status, tone: "neutral" as const };
            return (
              <Link key={application.id} href={`/applications/${application.id}`} className={content.listCard}>
                <div className={content.listCardHeader}>
                  <span className={content.itemTitle}>{application.title}</span>
                  <Badge tone={status.tone}>{status.label}</Badge>
                </div>
                <div className={content.progressBlock}>
                  <div className={content.progressTrack}><div className={content.progressFill} style={{ width: `${application.progress}%` }} /></div>
                  <div className={content.progressMeta}><span>工作区进度</span><span>{application.progress}%</span></div>
                </div>
                <div className={content.meta}>{new Date(application.created_at).toLocaleString("zh-CN")}</div>
              </Link>
            );
          })}
        </div>
      )}
    </AppShell>
  );
}
