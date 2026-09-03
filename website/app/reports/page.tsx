"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { Button } from "@/components/ui/Button";
import { ButtonLink } from "@/components/ui/ButtonLink";
import { EmptyState } from "@/components/ui/EmptyState";
import { InlineAlert } from "@/components/ui/InlineAlert";
import { LoadingState } from "@/components/ui/LoadingState";
import { PageHeader } from "@/components/ui/PageHeader";
import { Surface } from "@/components/ui/Surface";
import AppShell from "@/components/workspace/AppShell";
import content from "@/components/workspace/WorkspaceContent.module.css";
import api, { type Entitlement } from "@/lib/api";

export default function ReportsPage() {
  const router = useRouter();
  const [entitlements, setEntitlements] = useState<Entitlement[]>([]);
  const [loading, setLoading] = useState(true);
  const [downloading, setDownloading] = useState<string | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!api.isAuthenticated()) {
      router.push("/login");
      return;
    }
    let cancelled = false;
    api
      .getEntitlements()
      .then((result) => {
        if (!cancelled) setEntitlements(result);
      })
      .catch((loadError) => {
        if (!cancelled) {
          setError(loadError instanceof Error ? loadError.message : "报告加载失败");
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [router]);

  const handleDownload = async (companyId: string) => {
    setDownloading(companyId);
    setError("");
    try {
      const blob = await api.downloadReport(companyId);
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = `政策机会分析报告_${new Date().toISOString().slice(0, 10)}.pdf`;
      anchor.click();
      URL.revokeObjectURL(url);
    } catch (downloadError) {
      setError(downloadError instanceof Error ? downloadError.message : "报告下载失败");
    } finally {
      setDownloading(null);
    }
  };

  if (loading) {
    return (
      <AppShell>
        <LoadingState label="正在加载报告" />
      </AppShell>
    );
  }

  const reports = entitlements.filter((entitlement) => entitlement.resource_type === "report");

  return (
    <AppShell>
      <PageHeader
        eyebrow="Reports"
        title="报告"
        description="仅显示当前工作区已经获得有效服务端权益的报告。"
      />

      {error && <InlineAlert>{error}</InlineAlert>}

      {reports.length === 0 ? (
        <EmptyState
          icon="▤"
          title="暂无可下载报告"
          description="当前没有报告权益。完成政策匹配并通过真实订单获得授权后，报告会出现在这里。"
          action={<ButtonLink href="/dashboard">开始政策匹配</ButtonLink>}
        />
      ) : (
        <div className={content.stack}>
          {reports.map((entitlement) => (
            <Surface key={entitlement.id} className={content.rowBetween}>
              <div>
                <div className={content.itemTitle}>{entitlement.product_name}</div>
                <div className={content.meta}>
                  授权于 {new Date(entitlement.created_at).toLocaleDateString("zh-CN")}
                </div>
              </div>
              <Button
                type="button"
                onClick={() => entitlement.resource_id && handleDownload(entitlement.resource_id)}
                disabled={!entitlement.resource_id || downloading === entitlement.resource_id}
              >
                {downloading === entitlement.resource_id ? "下载中…" : "下载 PDF"}
              </Button>
            </Surface>
          ))}
        </div>
      )}

      <div className={content.section}>
        <InlineAlert tone="info">
          申报诊断与材料生成将在具体机会工作区开放；当前页面不会创建未绑定机会的空任务。
        </InlineAlert>
      </div>
    </AppShell>
  );
}
