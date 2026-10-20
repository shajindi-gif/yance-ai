"use client";

import { useParams, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { Button } from "@/components/ui/Button";
import { Badge } from "@/components/ui/Badge";
import { ButtonLink } from "@/components/ui/ButtonLink";
import { EmptyState } from "@/components/ui/EmptyState";
import { InlineAlert } from "@/components/ui/InlineAlert";
import { LoadingState } from "@/components/ui/LoadingState";
import { PageHeader } from "@/components/ui/PageHeader";
import AppShell from "@/components/workspace/AppShell";
import flow from "@/components/workspace/CoreWorkflow.module.css";
import content from "@/components/workspace/WorkspaceContent.module.css";
import api, { type AgentRunDetail } from "@/lib/api";

const statusTone = (status: string) => {
  if (status === "completed") return "success" as const;
  if (status === "failed") return "danger" as const;
  if (status === "queued") return "warning" as const;
  return "info" as const;
};

const prettyJson = (value: Record<string, unknown>) => JSON.stringify(value, null, 2);

export default function AgentRunPage() {
  const params = useParams<{ runId: string }>();
  const router = useRouter();
  const [run, setRun] = useState<AgentRunDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [cancelling, setCancelling] = useState(false);
  const [canCancel, setCanCancel] = useState(false);

  const cancel = async () => {
    setCancelling(true);
    try {
      await api.cancelAgentRun(params.runId);
      setRun(await api.getAgentRun(params.runId));
      setError("");
    } catch (failure) {
      setError(failure instanceof Error ? failure.message : "取消失败，请重试");
    } finally {
      setCancelling(false);
    }
  };

  useEffect(() => {
    if (!api.isAuthenticated()) {
      router.push("/login");
      return;
    }
    let active = true;
    api.getAuthConfig().then((config) => {
      if (active) setCanCancel(config.agent_cancellation_enabled === true);
    });
    let timer: number | undefined;
    const load = async () => {
      try {
        const result = await api.getAgentRun(params.runId);
        if (!active) return;
        setRun(result);
        setError("");
        if (["queued", "planning", "running", "waiting"].includes(result.status)) timer = window.setTimeout(load, 3000);
      } catch (loadError) {
        if (active) setError(loadError instanceof Error ? loadError.message : "Agent Run 加载失败");
      } finally {
        if (active) setLoading(false);
      }
    };
    void load();
    return () => {
      active = false;
      if (timer) window.clearTimeout(timer);
    };
  }, [params.runId, router]);

  if (loading) return <AppShell><LoadingState label="正在加载执行轨迹" /></AppShell>;
  if (!run) return <AppShell><PageHeader title="Agent Run 不可用" description="该运行不存在、无权访问或暂时无法加载。" />{error && <InlineAlert>{error}</InlineAlert>}<ButtonLink href="/agents" variant="secondary">返回 Agent 运行</ButtonLink></AppShell>;

  return (
    <AppShell>
      <PageHeader eyebrow="Execution Trace" title={`${run.agent_name} · ${run.workflow_key || "未命名工作流"}`} description={`Run ID: ${run.id}`} actions={<ButtonLink href="/agents" variant="secondary">返回列表</ButtonLink>} />
      {error && <InlineAlert>{error}</InlineAlert>}
      {canCancel && ["queued", "planning", "running", "waiting"].includes(run.status) ? <Button variant="secondary" onClick={cancel} disabled={cancelling}>{cancelling ? "正在取消…" : "取消任务"}</Button> : null}
      {run.status === "cancelled" ? <InlineAlert>任务已取消。正在进行的供应商请求可能仍产生费用；后续步骤与最终交付已停止。</InlineAlert> : null}
      <div className={flow.metricGrid}>
        <div className={flow.metric}><strong><Badge tone={statusTone(run.status)}>{run.status}</Badge></strong><span>运行状态</span></div>
        <div className={flow.metric}><strong>{run.current_step || "—"}</strong><span>当前步骤</span></div>
        <div className={flow.metric}><strong>{run.total_tokens}</strong><span>模型 Token</span></div>
        <div className={flow.metric}><strong>{run.latency_ms === null ? "—" : `${run.latency_ms} ms`}</strong><span>端到端延迟</span></div>
      </div>

      <section className={content.section}>
        <div className={content.sectionHeading}><h2>Plan → Retrieve → Reason → Act → Verify → Finish</h2><p>每个步骤均为持久化记录；失败与重试不会覆盖历史。</p></div>
        <div className={content.stack}>
          {run.steps.map((step) => (
            <article key={step.id} className={content.card}>
              <div className={content.cardHeader}><div><h2>{step.sequence}. {step.step_type}</h2><p className={content.cardIntro}>{step.latency_ms === null ? "尚未完成" : `${step.latency_ms} ms`} · ${Number(step.cost_usd).toFixed(4)}</p></div><Badge tone={statusTone(step.status)}>{step.status}</Badge></div>
              {Object.keys(step.verification).length > 0 && <div className={flow.traceBlock}><strong>Verification</strong><pre>{prettyJson(step.verification)}</pre></div>}
            </article>
          ))}
          {run.steps.length === 0 && <EmptyState icon="…" title="运行尚未开始" description="Worker 领取任务后，执行步骤会出现在这里。" />}
        </div>
      </section>

      <div className={flow.gridTwo}>
        <section className={content.section}>
          <div className={content.sectionHeading}><h2>Tool Calls</h2><p>工具参数与结果仅保存结构化业务标识和计数。</p></div>
          <div className={content.stack}>
            {run.tool_calls.map((tool) => <article key={tool.id} className={content.card}><div className={content.cardHeader}><div><h2>{tool.tool_name}</h2><p className={content.cardIntro}>{tool.latency_ms === null ? "执行中" : `${tool.latency_ms} ms`}</p></div><Badge tone={statusTone(tool.status)}>{tool.status}</Badge></div><div className={flow.traceBlock}><strong>Result</strong><pre>{prettyJson(tool.result)}</pre></div></article>)}
            {!run.tool_calls.length && <p className={content.cardIntro}>暂无工具调用。</p>}
          </div>
        </section>
        <section className={content.section}>
          <div className={content.sectionHeading}><h2>Artifacts & Errors</h2><p>交付物、错误和重试均保留关联关系。</p></div>
          <div className={content.stack}>
            {run.artifacts.map((artifact) => <article key={artifact.id} className={content.card}><div className={content.cardHeader}><div><h2>{artifact.title}</h2><p className={content.cardIntro}>{artifact.artifact_type} · v{artifact.version}</p></div><Badge tone="success">{artifact.status}</Badge></div></article>)}
            {run.errors.map((item) => <article key={item.id} className={content.card}><div className={content.cardHeader}><div><h2>{item.code}</h2><p className={content.cardIntro}>{item.safe_message}</p></div><Badge tone="danger">error</Badge></div></article>)}
            {!run.artifacts.length && !run.errors.length && <p className={content.cardIntro}>暂无交付物或错误记录。</p>}
          </div>
        </section>
      </div>
    </AppShell>
  );
}
