"use client";

import { useCallback, useEffect, useState } from "react";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { EmptyState } from "@/components/ui/EmptyState";
import { InlineAlert } from "@/components/ui/InlineAlert";
import { LoadingState } from "@/components/ui/LoadingState";
import { PageHeader } from "@/components/ui/PageHeader";
import AppShell from "@/components/workspace/AppShell";
import content from "@/components/workspace/WorkspaceContent.module.css";
import api, { type NotificationItem } from "@/lib/api";

const SEVERITY_TONE = { info: "neutral", warning: "warning", critical: "danger" } as const;

export default function NotificationsPage() {
  const [items, setItems] = useState<NotificationItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [scanning, setScanning] = useState(false);

  const load = useCallback(async () => {
    setError("");
    try {
      setItems(await api.getNotifications());
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : "通知加载失败");
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

  const markRead = async (id: string) => {
    try {
      await api.markNotificationRead(id);
      setItems((previous) =>
        previous.map((item) =>
          item.id === id ? { ...item, read_at: new Date().toISOString() } : item,
        ),
      );
    } catch (markError) {
      setError(markError instanceof Error ? markError.message : "操作失败");
    }
  };

  const markAll = async () => {
    try {
      await api.markAllNotificationsRead();
      setItems((previous) =>
        previous.map((item) => ({ ...item, read_at: new Date().toISOString() })),
      );
    } catch (markError) {
      setError(markError instanceof Error ? markError.message : "操作失败");
    }
  };

  const scan = async () => {
    setScanning(true);
    setError("");
    try {
      const result = await api.scanDeadlineNotifications();
      await load();
      if (result.created === 0) setError("暂无新的截止提醒（所有在管项目均在安全窗口内）");
    } catch (scanError) {
      setError(scanError instanceof Error ? scanError.message : "检查失败");
    } finally {
      setScanning(false);
    }
  };

  if (loading) return <AppShell><LoadingState label="正在加载通知" /></AppShell>;

  const unread = items.filter((item) => !item.read_at).length;

  return (
    <AppShell>
      <PageHeader
        eyebrow="Notifications"
        title="通知"
        description="截止日提醒（T-30/14/7/3/1）与管道动态，全部由服务端扫描真实记录生成，不展示推测信息。"
        actions={
          <>
            <Button variant="secondary" onClick={scan} disabled={scanning}>
              {scanning ? "检查中…" : "立即检查截止日"}
            </Button>
            {unread > 0 ? <Button onClick={markAll}>全部标为已读</Button> : null}
          </>
        }
      />
      {error ? <InlineAlert tone="info">{error}</InlineAlert> : null}
      {items.length === 0 ? (
        <EmptyState
          icon="—"
          title="暂无通知"
          description="创建带截止日期的申报或运行政策扫描后，截止提醒会自动出现在这里。"
        />
      ) : (
        <div className={content.stack}>
          {items.map((item) => (
            <article
              key={item.id}
              className={content.card}
              style={item.read_at ? { opacity: 0.62 } : undefined}
            >
              <div className={content.rowBetween} style={{ gap: 12, flexWrap: "wrap" }}>
                <div style={{ minWidth: 0, flex: 1 }}>
                  <div style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap" }}>
                    <Badge tone={SEVERITY_TONE[item.severity] || "neutral"}>{item.severity}</Badge>
                    <strong style={{ fontSize: 14.5 }}>{item.title}</strong>
                  </div>
                  {item.body ? (
                    <div className={content.subtle} style={{ marginTop: 6, fontSize: 13 }}>{item.body}</div>
                  ) : null}
                  <div className={content.meta} style={{ marginTop: 6 }}>
                    {new Date(item.created_at).toLocaleString("zh-CN")}
                  </div>
                </div>
                {!item.read_at ? (
                  <Button variant="secondary" onClick={() => void markRead(item.id)}>标为已读</Button>
                ) : (
                  <Badge tone="neutral">已读</Badge>
                )}
              </div>
            </article>
          ))}
        </div>
      )}
    </AppShell>
  );
}
