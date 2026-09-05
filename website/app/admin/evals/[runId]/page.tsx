"use client";

import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { Badge } from "@/components/ui/Badge";
import { ButtonLink } from "@/components/ui/ButtonLink";
import { InlineAlert } from "@/components/ui/InlineAlert";
import { LoadingState } from "@/components/ui/LoadingState";
import { PageHeader } from "@/components/ui/PageHeader";
import AppShell from "@/components/workspace/AppShell";
import styles from "@/components/workspace/AdminDashboard.module.css";
import api, { type EvalRunDetail } from "@/lib/api";

function pretty(value: Record<string, unknown>): string {
  return JSON.stringify(value, null, 2);
}

export default function EvaluationRunPage() {
  const params = useParams<{ runId: string }>();
  const [detail, setDetail] = useState<EvalRunDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!api.isAuthenticated()) {
      setError("请先登录平台管理员账号。");
      setLoading(false);
      return;
    }
    let active = true;
    api.getEvaluationRun(params.runId)
      .then((nextDetail) => {
        if (active) setDetail(nextDetail);
      })
      .catch((loadError) => {
        if (active) setError(loadError instanceof Error ? loadError.message : "Eval Run 加载失败");
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [params.runId]);

  if (loading) return <AppShell><LoadingState label="正在加载 Eval Run" /></AppShell>;
  if (!detail) return <AppShell><PageHeader title="Eval Run 不可用" description="该运行不存在或当前账号无权查看。" />{error ? <InlineAlert tone="error">{error}</InlineAlert> : null}<ButtonLink href="/admin/evals" variant="secondary">返回评测</ButtonLink></AppShell>;

  const { run, dataset } = detail;
  return <AppShell>
    <PageHeader eyebrow="Evaluation Trace" title={dataset.name} description={`Run ${run.id} · ${dataset.key}@${dataset.version}`} actions={<ButtonLink href="/admin/evals" variant="secondary">返回评测</ButtonLink>} />
    {error ? <InlineAlert tone="error">{error}</InlineAlert> : null}
    {dataset.review_status !== "reviewed" ? <InlineAlert tone="info">{dataset.data_classification} · {dataset.review_status}：该运行不具备投资人质量指标资格。</InlineAlert> : null}
    <div className={styles.metricGrid}>
      <div className={styles.metricCard}><strong>{run.passed_cases}/{run.requested_cases}</strong><span>Passed Cases</span><small>errors remain in denominator</small></div>
      <div className={styles.metricCard}><strong>{run.error_cases}</strong><span>Error Cases</span><small>not silently excluded</small></div>
      <div className={styles.metricCard}><strong>{run.total_latency_ms} ms</strong><span>Total Latency</span><small>persisted execution time</small></div>
      <div className={styles.metricCard}><strong>${run.total_cost_usd.toFixed(6)}</strong><span>Total Cost</span><small>deterministic target</small></div>
      <div className={styles.metricCard}><strong><Badge tone={run.release_gate_passed ? "success" : "danger"}>{run.release_gate_passed ? "passed" : "failed"}</Badge></strong><span>Release Gate</span><small>{run.scorer_version}</small></div>
      <div className={styles.metricCard}><strong>{dataset.content_sha256.slice(0, 12)}</strong><span>Dataset Hash</span><small>immutable version</small></div>
    </div>
    <section className={styles.panel}>
      <div className={styles.panelHeader}><div><h2>Case Results</h2><p>Question → Ground Truth → Model Answer → Score → Evidence → Error Type</p></div><Badge tone="neutral">{dataset.case_count} cases</Badge></div>
      <div className={styles.caseList}>{detail.cases.map((item) => <article className={styles.caseCard} key={item.case_id}>
        <div className={styles.caseHeader}><div><strong>{item.case_id}</strong><h3>{item.question}</h3><span>{item.risk_tier} risk · {item.tags.join(" · ")}</span></div><Badge tone={item.passed ? "success" : "danger"}>{item.passed ? "pass" : item.status}</Badge></div>
        <div className={styles.jsonGrid}><div><strong>Ground Truth</strong><pre>{pretty(item.ground_truth)}</pre></div><div><strong>Model Answer</strong><pre>{pretty(item.model_answer)}</pre></div></div>
        <div className={styles.dimensionChips}>{item.dimensions.map((dimension) => <span key={dimension.dimension}>{dimension.dimension}: {dimension.is_applicable && dimension.score != null ? `${(dimension.score * 100).toFixed(0)}%` : "N/A"}</span>)}</div>
        {item.evidence.length ? <div className={styles.evidenceList}>{item.evidence.map((evidence, index) => <div key={`${evidence.expectation}-${index}`}><Badge tone={evidence.passed ? "success" : "danger"}>{evidence.passed ? "verified" : "failed"}</Badge><span>{evidence.expectation} → {evidence.observed}</span><small>{evidence.source_reference || "no source reference"}</small></div>)}</div> : <p className={styles.muted}>该 case 没有适用的 Evidence observation。</p>}
        {item.errors.map((itemError) => <InlineAlert tone="error" key={`${itemError.code}-${itemError.error_type}`}>{itemError.error_type}: {itemError.safe_message}</InlineAlert>)}
      </article>)}</div>
    </section>
  </AppShell>;
}
