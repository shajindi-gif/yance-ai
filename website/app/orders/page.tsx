"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { Badge } from "@/components/ui/Badge";
import { ButtonLink } from "@/components/ui/ButtonLink";
import { DataTable } from "@/components/ui/DataTable";
import { EmptyState } from "@/components/ui/EmptyState";
import { InlineAlert } from "@/components/ui/InlineAlert";
import { LoadingState } from "@/components/ui/LoadingState";
import { PageHeader } from "@/components/ui/PageHeader";
import AppShell from "@/components/workspace/AppShell";
import content from "@/components/workspace/WorkspaceContent.module.css";
import api, { type Order } from "@/lib/api";

type BadgeTone = "neutral" | "info" | "success" | "warning" | "danger";

const PRODUCT_NAMES: Record<string, string> = {
  POLICY_REPORT: "企业政策 AI 体检报告",
  POLICY_DIAGNOSIS: "单项目申报诊断",
  APPLICATION_PLAN: "AI 申报方案包",
  APPLICATION_DRAFT: "AI 申报材料初稿",
};

const STATUS_LABELS: Record<string, { text: string; tone: BadgeTone }> = {
  created: { text: "待支付", tone: "warning" },
  pending: { text: "待支付", tone: "warning" },
  paid: { text: "已支付", tone: "success" },
  completed: { text: "已完成", tone: "success" },
  cancelled: { text: "已取消", tone: "neutral" },
  refunded: { text: "已退款", tone: "info" },
};

function formatMoney(amount: number, currency: string): string {
  return new Intl.NumberFormat("zh-CN", {
    style: "currency",
    currency: currency || "CNY",
    minimumFractionDigits: 2,
  }).format(amount);
}

export default function OrdersPage() {
  const router = useRouter();
  const [orders, setOrders] = useState<Order[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!api.isAuthenticated()) {
      router.push("/login");
      return;
    }
    let cancelled = false;
    api
      .getOrders()
      .then((result) => {
        if (!cancelled) setOrders(result);
      })
      .catch((loadError) => {
        if (!cancelled) {
          setError(loadError instanceof Error ? loadError.message : "订单加载失败");
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [router]);

  if (loading) {
    return (
      <AppShell>
        <LoadingState label="正在加载订单" />
      </AppShell>
    );
  }

  return (
    <AppShell>
      <PageHeader
        eyebrow="Billing"
        title="订单与账单"
        description="金额与状态来自服务端交易记录；支付结果以已校验的服务商回调为准。"
      />

      {error && <InlineAlert>{error}</InlineAlert>}

      {orders.length === 0 ? (
        <EmptyState
          icon="¥"
          title="暂无订单"
          description="当前工作区没有真实订单。开始政策匹配不会自动产生收费记录。"
          action={<ButtonLink href="/dashboard">返回工作台</ButtonLink>}
        />
      ) : (
        <div className={content.tableSurface}>
          <DataTable>
            <table className={content.table}>
              <thead>
                <tr>
                  <th>订单号</th>
                  <th>产品</th>
                  <th className={content.alignRight}>金额</th>
                  <th className={content.alignCenter}>状态</th>
                  <th className={content.alignRight}>日期</th>
                </tr>
              </thead>
              <tbody>
                {orders.map((order) => {
                  const status = STATUS_LABELS[order.status] || {
                    text: order.status,
                    tone: "neutral" as const,
                  };
                  return (
                    <tr key={order.id}>
                      <td>
                        <span className={content.mono}>{order.order_no || order.id}</span>
                      </td>
                      <td>{PRODUCT_NAMES[order.product_code] || order.product_code}</td>
                      <td className={content.alignRight}>
                        <span className={content.amount}>
                          {formatMoney(order.amount, order.currency)}
                        </span>
                      </td>
                      <td className={content.alignCenter}>
                        <Badge tone={status.tone}>{status.text}</Badge>
                      </td>
                      <td className={`${content.alignRight} ${content.subtle}`}>
                        {new Date(order.created_at).toLocaleDateString("zh-CN")}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </DataTable>
        </div>
      )}
    </AppShell>
  );
}
