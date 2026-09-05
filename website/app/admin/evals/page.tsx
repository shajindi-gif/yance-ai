"use client";

import Link from "next/link";
import { useCallback, useEffect, useRef, useState } from "react";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { ButtonLink } from "@/components/ui/ButtonLink";
import { EmptyState } from "@/components/ui/EmptyState";
import { InlineAlert } from "@/components/ui/InlineAlert";
import { LoadingState } from "@/components/ui/LoadingState";
import { PageHeader } from "@/components/ui/PageHeader";
import AppShell from "@/components/workspace/AppShell";
import styles from "@/components/workspace/AdminDashboard.module.css";
import api, { type EvalType, type EvaluationOverview } from "@/lib/api";

const FILTERS: Array<[EvalType | "", string]> = [
  ["", "全部评测"],
  ["policy_retrieval_eval", "Policy Retrieval"],
  ["eligibility_eval", "Eligibility"],
  ["citation_eval", "Citation"],
  ["hallucination_eval", "Hallucination"],
  ["document_generation_eval", "Document Generation"],
];

const CARD_LABELS: Array<[keyof EvaluationOverview["cards"], string, string]> = [
  ["accuracy", "Accuracy", "mean applicable correctness"],
  ["citation_accuracy", "Citation Accuracy", "exact-span decisions"],
  ["hallucination_rate", "Hallucination Rate", "1 − safety score"],
  ["pass_rate", "Pass Rate", "errors stay in denominator"],
  ["average_latency_ms", "Average Latency", "per requested case"],
  ["average_cost_usd", "Average Cost", "per requested case"],
];

function cardValue(key: keyof EvaluationOverview["cards"], value: number | null): string {
  if (value == null) return "—";
  if (key === "average_latency_ms") return `${value.toFixed(1)} ms`;
  if (key === "average_cost_usd") return `$${value.toFixed(6)}`;
  return `${(value * 100).toFixed(1)}%`;
}

export default function EvaluationDashboardPage() {
  const [overview, setOverview] = useState<EvaluationOverview | null>(null);
  const [filter, setFilter] = useState<EvalType | "">("");
  const [loading, setLoading] = useState(true);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState("");
  const requestSequence = useRef(0);

  const load = useCallback(async (nextFilter: EvalType | "" = "") => {
    const requestId = ++requestSequence.current;
    setError("");
    try {
      const nextOverview = await api.getEvaluationOverview(nextFilter || undefined);
      if (requestId === requestSequence.current) setOverview(nextOverview);
    } catch (loadError) {
      if (requestId === requestSequence.current) {
        setError(loadError instanceof Error ? loadError.message : "评测数据加载失败");
      }
    } finally {
      if (requestId === requestSequence.current) setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (!api.isAuthenticated()) {
      setError("请先登录平台管理员账号。");
      setLoading(false);
      return;
    }
    void load();
  }, [load]);

  const changeFilter = (next: EvalType | "") => {
    setFilter(next);
    setLoading(true);
    void load(next);
  };

  const runEvaluations = async () => {
    setRunning(true);
    setError("");
    try {
      await api.runEvaluations(filter || "all");
      await load(filter);
    } catch (runError) {
      setError(runError instanceof Error ? runError.message : "评测执行失败");
    } finally {
      setRunning(false);
    }
  };

  if (loading) return <AppShell><LoadingState label="正在读取评测结果" /></AppShell>;

  return <AppShell>
    <PageHeader eyebrow="Evaluation · Platform Admin" title="Agent 质量评测" description="最新完成的非 Demo Eval Run；每项结果保留数据集、目标、评分器、分母和错误。" actions={<><ButtonLink href="/admin" variant="secondary">返回 Admin</ButtonLink><Button type="button" disabled={running} onClick={runEvaluations}>{running ? "正在执行…" : filter ? "运行当前评测" : "运行 5 类评测"}</Button></>} />
    {error ? <InlineAlert tone="error">{error}</InlineAlert> : null}
    <div className={styles.evalToolbar}>
      <label htmlFor="eval-type">评测类型</label>
      <select id="eval-type" value={filter} onChange={(event) => changeFilter(event.target.value as EvalType | "")}>
        {FILTERS.map(([value, label]) => <option key={value || "all"} value={value}>{label}</option>)}
      </select>
      <span>范围：latest completed run per eval type</span>
    </div>

    <div className={styles.metricGrid}>
      {CARD_LABELS.map(([key, label, note]) => <div className={styles.metricCard} key={key}><strong>{cardValue(key, overview?.cards[key] ?? null)}</strong><span>{label}</span><small>{note}</small></div>)}
    </div>

    {!overview?.available ? <section className={styles.panel}><EmptyState icon="—" title="No evaluation data yet." description="数据库中还没有真实执行结果。点击运行后才会创建 Eval Run；页面不会使用示例指标填充卡片。" /></section> : <>
      {!overview.investor_quality_eligible ? <InlineAlert tone="info">当前结果来自合成、尚未人工复核的数据集，只能作为工程回归信号，不能作为生产准确率或投资人质量指标。</InlineAlert> : null}
      <div className={styles.twoColumn}>
        <section className={styles.panel}>
          <div className={styles.panelHeader}><div><h2>Quality Dimensions</h2><p>维度均值和实际样本数；不适用维度不进入均值。</p></div><Badge tone="neutral">{overview.counts.requested} requested</Badge></div>
          <div className={styles.dimensionList}>{overview.dimensions.map((item) => <div key={item.dimension}><div><strong>{item.dimension}</strong><span>{item.score == null ? "—" : `${(item.score * 100).toFixed(1)}%`} · n={item.sample_size}</span></div><div className={styles.scoreTrack}><span style={{ width: `${(item.score || 0) * 100}%` }} /></div></div>)}</div>
        </section>
        <section className={styles.panel}>
          <div className={styles.panelHeader}><div><h2>Denominator</h2><p>失败和执行错误不会从分母移除。</p></div><Badge tone={overview.counts.errors ? "danger" : "success"}>{overview.counts.errors} errors</Badge></div>
          <dl className={styles.healthList}><div><dt>Requested</dt><dd>{overview.counts.requested}</dd></div><div><dt>Completed</dt><dd>{overview.counts.completed}</dd></div><div><dt>Passed</dt><dd>{overview.counts.passed}</dd></div><div><dt>Errors</dt><dd>{overview.counts.errors}</dd></div></dl>
        </section>
      </div>
      <section className={styles.panel}>
        <div className={styles.panelHeader}><div><h2>Latest Comparable Runs</h2><p>每类仅采用最新完成的非 Demo 运行，避免重复执行扩大样本数。</p></div><Badge tone="info">{new Date(overview.generated_at).toLocaleString("zh-CN")}</Badge></div>
        <div className={styles.evalRunList}>{overview.runs.map((run) => <Link className={styles.evalRun} href={`/admin/evals/${run.id}`} key={run.id}><div><strong>{run.eval_type}</strong><span>{run.dataset} · {run.dataset_version}</span></div><div><Badge tone={run.release_gate_passed ? "success" : "danger"}>{run.release_gate_passed ? "gate passed" : "gate failed"}</Badge><span>{run.passed_cases}/{run.requested_cases} passed · {run.error_cases} errors</span></div><div><span>{run.data_classification} · {run.review_status}</span><span>{run.target_key}@{run.target_version} · {run.scorer_version}</span></div></Link>)}</div>
      </section>
    </>}
  </AppShell>;
}
