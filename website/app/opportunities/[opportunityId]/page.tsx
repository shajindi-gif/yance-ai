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
import flow from "@/components/workspace/CoreWorkflow.module.css";
import content from "@/components/workspace/WorkspaceContent.module.css";
import api, { type Opportunity } from "@/lib/api";

const ELIGIBILITY = {
  ELIGIBLE: { label: "Eligible", tone: "success" as const },
  POTENTIALLY_ELIGIBLE: { label: "Potentially Eligible", tone: "warning" as const },
  NOT_ELIGIBLE: { label: "Not Eligible", tone: "danger" as const },
  NEED_MORE_INFORMATION: { label: "Need More Information", tone: "neutral" as const },
};

function safeSourceUrl(value?: string | null): string | null {
  if (!value) return null;
  try {
    const url = new URL(value);
    return url.protocol === "https:" || url.protocol === "http:" ? url.toString() : null;
  } catch {
    return null;
  }
}

export default function OpportunityDetailPage() {
  const params = useParams<{ opportunityId: string }>();
  const router = useRouter();
  const opportunityId = params.opportunityId;
  const [opportunity, setOpportunity] = useState<Opportunity | null>(null);
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!api.isAuthenticated()) {
      router.push("/login");
      return;
    }
    let active = true;
    api
      .getOpportunity(opportunityId)
      .then((result) => {
        if (active) {
          setOpportunity(result);
          api.recordOpportunityOpened(opportunityId).catch(() => undefined);
        }
      })
      .catch((loadError) => {
        if (active) {
          setError(loadError instanceof Error ? loadError.message : "政策机会加载失败");
        }
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [opportunityId, router]);

  const createApplication = async () => {
    if (!opportunity) return;
    setCreating(true);
    setError("");
    try {
      const application = await api.createApplication({
        company_id: opportunity.company_id,
        opportunity_id: opportunity.id,
        title: `${opportunity.policy_snapshot_json.title || opportunity.title}申报`,
      });
      router.push(`/applications/${application.id}`);
    } catch (createError) {
      setError(createError instanceof Error ? createError.message : "申报工作区创建失败");
      setCreating(false);
    }
  };

  if (loading) {
    return (
      <AppShell>
        <LoadingState label="正在加载政策机会" />
      </AppShell>
    );
  }

  if (!opportunity) {
    return (
      <AppShell>
        <PageHeader title="政策机会不可用" description="记录不存在、无权访问或暂时无法加载。" />
        {error && <InlineAlert>{error}</InlineAlert>}
        <ButtonLink href="/opportunities" variant="secondary">返回机会列表</ButtonLink>
      </AppShell>
    );
  }

  const snapshot = opportunity.policy_snapshot_json;
  const eligibility = ELIGIBILITY[opportunity.eligibility_status];
  const sourceUrl = safeSourceUrl(snapshot.source_url);
  const missingMaterials = opportunity.evidence_json.missing_materials || [];
  const scoreBreakdown = opportunity.evidence_json.score_breakdown || {};
  const result = opportunity.eligibility_result;
  const evidence = opportunity.evidence || [];
  const requirements = opportunity.required_materials || [];
  const benefits = opportunity.benefits || [];

  return (
    <AppShell>
      <PageHeader
        eyebrow="Opportunity"
        title={snapshot.title || opportunity.title}
        description="政策元数据、企业画像版本、逐条资格判断与原文证据均已固化，可回溯本次判断。"
        actions={
          <div className={flow.toolbarActions}>
            <ButtonLink href="/opportunities" variant="secondary">返回列表</ButtonLink>
            <Button type="button" onClick={createApplication} disabled={creating}>
              {creating ? "创建中…" : "开始申报"}
            </Button>
          </div>
        }
      />
      {error && <InlineAlert>{error}</InlineAlert>}

      <div className={flow.metricGrid}>
        <div className={flow.metric}><strong>{Math.round((opportunity.score || 0) * 100)}%</strong><span>相关性匹配分</span></div>
        <div className={flow.metric}><strong>{missingMaterials.length}</strong><span>候选材料缺口</span></div>
        <div className={flow.metric}><strong>{opportunity.eligibility_confidence == null ? "—" : `${Math.round(opportunity.eligibility_confidence * 100)}%`}</strong><span>资格置信度</span></div>
        <div className={flow.metric}><Badge tone={eligibility.tone}>{eligibility.label}</Badge><span>资格状态</span></div>
      </div>

      {opportunity.eligibility_status === "NEED_MORE_INFORMATION" && (
        <InlineAlert tone="info">相关性命中不代表符合资格。{result?.summary || "当前缺少结构化规则或可核验证据。"}</InlineAlert>
      )}
      {result?.status === "POTENTIALLY_ELIGIBLE" && (
        <InlineAlert tone="info">结构化硬门槛已通过并有原文证据；正式申报前仍需人工复核。</InlineAlert>
      )}
      {result?.status === "NOT_ELIGIBLE" && (
        <InlineAlert tone="error">至少一项已核验硬门槛不满足。请查看逐条判断后再决定是否继续。</InlineAlert>
      )}

      <div className={flow.detailGrid}>
        <section className={content.card}>
          <h2>政策概览</h2>
          <dl className={flow.definitionList}>
            <div><dt>发布机关</dt><dd>{snapshot.issuing_authority || "未记录"}</dd></div>
            <div><dt>适用地区</dt><dd>{snapshot.jurisdiction || [snapshot.province, snapshot.city, snapshot.district].filter(Boolean).join(" · ") || "未记录"}</dd></div>
            <div><dt>政策类型</dt><dd>{snapshot.policy_type || snapshot.support_type || "未记录"}</dd></div>
            <div><dt>潜在支持</dt><dd>{snapshot.support_amount || "未公开"}</dd></div>
            <div><dt>发布日期</dt><dd>{snapshot.published_at ? new Date(snapshot.published_at).toLocaleDateString("zh-CN") : "未记录"}</dd></div>
            <div><dt>有效日期</dt><dd>{snapshot.effective_at ? new Date(snapshot.effective_at).toLocaleDateString("zh-CN") : "未记录"}</dd></div>
            <div><dt>截止日期</dt><dd>{snapshot.deadline ? new Date(snapshot.deadline).toLocaleDateString("zh-CN") : "未记录"}</dd></div>
            <div><dt>原文来源</dt><dd>{sourceUrl ? <a className={flow.link} href={sourceUrl} target="_blank" rel="noreferrer">打开政策来源</a> : "未提供可验证链接"}</dd></div>
          </dl>
        </section>

        <section className={content.card}>
          <h2>匹配依据</h2>
          {Object.keys(scoreBreakdown).length === 0 ? (
            <p className={content.cardIntro}>暂无结构化匹配分解。</p>
          ) : (
            <dl className={flow.definitionList}>
              {Object.entries(scoreBreakdown).map(([key, value]) => (
                <div key={key}><dt>{key}</dt><dd>{value} 分</dd></div>
              ))}
            </dl>
          )}
        </section>
      </div>

      <section className={content.section}>
        <div className={content.card}>
          <div className={flow.sectionHeading}>
            <div><h2>资格判断</h2><p className={content.cardIntro}>{result?.summary || "尚无资格判断记录。"}</p></div>
            {result && <Badge tone="neutral">{result.engine_version}</Badge>}
          </div>
          {!result || result.criteria.length === 0 ? (
            <p className={content.cardIntro}>暂无已审核的结构化资格规则，系统不会从相关性分数推断资格。</p>
          ) : (
            <div className={flow.criteriaList}>
              {result.criteria.map((criterion) => (
                <div className={flow.criterion} key={criterion.rule_id}>
                  <div>
                    <strong>{criterion.name}</strong>
                    <p>企业事实：{criterion.actual == null || criterion.actual === "" ? "未提供" : String(criterion.actual)}</p>
                    <p>政策要求：{String(criterion.expected ?? "存在该信息")}{criterion.article ? ` · ${criterion.article}` : ""}</p>
                  </div>
                  <div className={flow.inlineMeta}>
                    {criterion.is_hard_gate && <Badge tone="warning">硬门槛</Badge>}
                    <Badge tone={criterion.status === "PASS" ? "success" : criterion.status === "FAIL" ? "danger" : "neutral"}>{criterion.status}</Badge>
                  </div>
                </div>
              ))}
            </div>
          )}
          {result && result.missing_information.length > 0 && (
            <div className={flow.gapList}>
              <strong>仍需补充</strong>
              {result.missing_information.map((item) => <span key={item}>• {item}</span>)}
            </div>
          )}
        </div>
      </section>

      <section className={content.section}>
        <div className={content.card}>
          <div className={flow.sectionHeading}><div><h2>政策证据</h2><p className={content.cardIntro}>引用必须逐字存在于本次固定的政策版本中。</p></div><Badge tone={evidence.length ? "success" : "neutral"}>{evidence.length} 条</Badge></div>
          {evidence.length === 0 ? (
            <p className={content.cardIntro}>暂无可验证证据。系统不会展示无来源政策结论。</p>
          ) : evidence.map((item) => (
            <blockquote className={flow.evidenceQuote} key={item.id}>
              <p>“{item.quote}”</p>
              <footer>{[item.issuer, item.article].filter(Boolean).join(" · ") || item.source_title} · {Math.round(item.confidence * 100)}% 置信度 {item.verified && <Badge tone="success">原文已核验</Badge>}</footer>
              {safeSourceUrl(item.source_url) && <a className={flow.link} href={safeSourceUrl(item.source_url) || undefined} target="_blank" rel="noreferrer">查看来源</a>}
            </blockquote>
          ))}
        </div>
      </section>

      {(requirements.length > 0 || benefits.length > 0) && (
        <div className={flow.gridTwo}>
          <section className={content.card}>
            <h2>申报材料</h2>
            {requirements.length === 0 ? <p className={content.cardIntro}>暂无已审核材料清单。</p> : requirements.map((item) => <div className={content.activityRow} key={item.id}><span className={content.activityStatus}>○</span><span>{item.name}</span>{item.is_hard_gate && <Badge tone="warning">必需</Badge>}</div>)}
          </section>
          <section className={content.card}>
            <h2>政策支持</h2>
            {benefits.length === 0 ? <p className={content.cardIntro}>暂无已审核支持内容。</p> : benefits.map((item) => <div className={content.activityRow} key={item.id}><span className={content.activityStatus}>＋</span><span>{item.description}</span>{item.amount_text && <Badge tone="info">{item.amount_text}</Badge>}</div>)}
          </section>
        </div>
      )}

      <section className={content.section}>
        <div className={content.card}>
          <h2>候选材料缺口</h2>
          <p className={content.cardIntro}>以下内容来自政策关键词，不代表已经核验企业现有资料，也不标记为硬门槛。</p>
          {missingMaterials.length === 0 ? (
            <p className={content.cardIntro}>扫描未生成候选材料。只有经过来源核验的材料要求才会进入正式清单。</p>
          ) : (
            missingMaterials.map((material) => (
              <div className={content.activityRow} key={material}><span className={content.activityStatus}>○</span><span>{material}</span><Badge tone="neutral">待核验</Badge></div>
            ))
          )}
        </div>
      </section>
    </AppShell>
  );
}
