"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { Badge } from "@/components/ui/Badge";
import { EmptyState } from "@/components/ui/EmptyState";
import { InlineAlert } from "@/components/ui/InlineAlert";
import { LoadingState } from "@/components/ui/LoadingState";
import { PageHeader } from "@/components/ui/PageHeader";
import AppShell from "@/components/workspace/AppShell";
import flow from "@/components/workspace/CoreWorkflow.module.css";
import content from "@/components/workspace/WorkspaceContent.module.css";
import api, { type AgentDefinitionSummary, type AgentRunSummary } from "@/lib/api";

interface AgentOperationsState {
  agents: AgentDefinitionSummary[];
  runs: AgentRunSummary[];
}

const statusTone = (status: string) => {
  if (status === "completed" || status === "active") return "success" as const;
  if (status === "failed") return "danger" as const;
  if (status === "inactive") return "neutral" as const;
  return "info" as const;
};

export default function AgentsPage() {
  const router = useRouter();
  const [data, setData] = useState<AgentOperationsState | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!api.isAuthenticated()) {
      router.push("/login");
      return;
    }
    let active = true;
    Promise.all([api.getAgents(), api.getAgentRuns()])
      .then(([agents, runs]) => {
        if (active) setData({ agents, runs });
      })
      .catch((loadError) => {
        if (active) setError(loadError instanceof Error ? loadError.message : "Agent 运行数据加载失败");
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [router]);

  if (loading) return <AppShell><LoadingState label="正在加载 Agent 运行数据" /></AppShell>;

  const completed = data?.runs.filter((run) => run.status === "completed").length || 0;
  const failed = data?.runs.filter((run) => run.status === "failed").length || 0;
  const terminal = completed + failed;
  const timedRuns = data?.runs.filter((run) => run.latency_ms !== null) || [];
  const averageLatencyMs = timedRuns.length
    ? Math.round(timedRuns.reduce((total, run) => total + (run.latency_ms || 0), 0) / timedRuns.length)
    : null;

  return (
    <AppShell>
      <PageHeader eyebrow="Agent Operations" title="Agent 运行" description="查看已注册 Agent、真实运行指标和每次工作流的完整执行轨迹。" />
      {error && <InlineAlert>{error}</InlineAlert>}

      <div className={flow.metricGrid}>
        <div className={flow.metric}><strong>{data?.runs.length || 0}</strong><span>当前列表运行数</span></div>
        <div className={flow.metric}><strong>{terminal ? `${Math.round((completed / terminal) * 100)}%` : "—"}</strong><span>终态运行成功率</span></div>
        <div className={flow.metric}><strong>{averageLatencyMs === null ? "—" : `${averageLatencyMs} ms`}</strong><span>平均执行延迟</span></div>
        <div className={flow.metric}><strong>{data?.agents.filter((agent) => agent.status === "active").length || 0}</strong><span>已启用 Agent</span></div>
      </div>

      <section className={content.section}>
        <div className={content.sectionHeading}><h2>Agent Registry</h2><p>未启用的专业 Agent 明确标记为 inactive，不计作已上线能力。</p></div>
        {!data?.agents.length ? (
          <EmptyState icon="◇" title="暂无 Agent 定义" description="运行数据库迁移后，版本化 Agent 定义会显示在这里。" />
        ) : (
          <div className={flow.gridTwo}>
            {data.agents.map((agent) => (
              <article key={agent.id} className={content.card}>
                <div className={content.cardHeader}><div><h2>{agent.name}</h2><p className={content.cardIntro}>{agent.description}</p></div><Badge tone={statusTone(agent.status)}>{agent.status}</Badge></div>
                <dl className={flow.definitionList}>
                  <div><dt>版本</dt><dd>{agent.version}</dd></div>
                  <div><dt>运行次数</dt><dd>{agent.run_count}</dd></div>
                  <div><dt>成功率</dt><dd>{agent.success_rate === null ? "暂无数据" : `${Math.round(agent.success_rate * 100)}%`}</dd></div>
                  <div><dt>平均延迟</dt><dd>{agent.average_latency_ms === null ? "暂无数据" : `${Math.round(agent.average_latency_ms)} ms`}</dd></div>
                  <div><dt>最近运行</dt><dd>{agent.last_run_at ? new Date(agent.last_run_at).toLocaleString("zh-CN") : "暂无数据"}</dd></div>
                </dl>
              </article>
            ))}
          </div>
        )}
      </section>

      <section className={content.section}>
        <div className={content.sectionHeading}><h2>最近运行</h2><p>Token 与成本只显示真实采集值；本地规则执行不会虚构模型费用。</p></div>
        {!data?.runs.length ? (
          <EmptyState icon="◎" title="No agent run data yet." description="创建政策扫描后，独立 Worker 会生成可复查轨迹。" />
        ) : (
          <div className={content.tableSurface}><div className={flow.tableScroll}>
            <table className={content.table}>
              <thead><tr><th>Agent</th><th>状态</th><th>当前步骤</th><th>Token</th><th>成本</th><th>延迟</th><th>创建时间</th></tr></thead>
              <tbody>{data.runs.map((run) => (
                <tr key={run.id}>
                  <td><Link className={flow.link} href={`/agents/${run.id}`}>{run.agent_name}</Link></td>
                  <td><Badge tone={statusTone(run.status)}>{run.status}</Badge></td>
                  <td>{run.current_step || "等待执行"}</td><td>{run.total_tokens}</td><td>${Number(run.cost_usd).toFixed(4)}</td>
                  <td>{run.latency_ms === null ? "—" : `${run.latency_ms} ms`}</td><td>{new Date(run.created_at).toLocaleString("zh-CN")}</td>
                </tr>
              ))}</tbody>
            </table>
          </div></div>
        )}
      </section>
    </AppShell>
  );
}
