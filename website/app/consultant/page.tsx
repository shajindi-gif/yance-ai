"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { InlineAlert } from "@/components/ui/InlineAlert";
import { LoadingState } from "@/components/ui/LoadingState";
import { PageHeader } from "@/components/ui/PageHeader";
import AppShell from "@/components/workspace/AppShell";
import content from "@/components/workspace/WorkspaceContent.module.css";
import flow from "@/components/workspace/CoreWorkflow.module.css";
import api, { type Company, type ConsultantAnswer } from "@/lib/api";

const PRESETS = [
  "我们最近有哪些能申请的资金？",
  "还缺什么证明材料？",
  "距离截止还有什么没完成？",
  "企业画像哪些关键信息不足？",
];

interface Turn {
  question: string;
  answer?: ConsultantAnswer;
  pending?: boolean;
  error?: string;
}

function Citation({ citation }: { citation?: Record<string, unknown> | null }) {
  if (!citation) return null;
  const quote = typeof citation.quote === "string" ? citation.quote : null;
  const article = typeof citation.article === "string" ? citation.article : null;
  const url = typeof citation.source_url === "string" ? citation.source_url : null;
  const title = typeof citation.title === "string" ? citation.title : null;
  if (!quote && !url && !title) return null;
  return (
    <div className={flow.evidenceQuote} style={{ marginTop: 8 }}>
      {article ? <strong>{article}：</strong> : null}
      {quote || title}
      {url ? (
        <>
          {" "}
          <a href={url} target="_blank" rel="noopener noreferrer" className={flow.link}>
            官方原文
          </a>
        </>
      ) : null}
    </div>
  );
}

export default function ConsultantPage() {
  const [companies, setCompanies] = useState<Company[]>([]);
  const [companyId, setCompanyId] = useState("");
  const [loading, setLoading] = useState(true);
  const [turns, setTurns] = useState<Turn[]>([]);
  const [question, setQuestion] = useState("");
  const [asking, setAsking] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  const load = useCallback(async () => {
    try {
      const comps = await api.getCompanies();
      setCompanies(comps);
      if (comps.length) setCompanyId((current) => current || comps[0].id);
    } catch {
      setCompanies([]);
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

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [turns]);

  const ask = async (text: string) => {
    const trimmed = text.trim();
    if (!trimmed || !companyId || asking) return;
    setAsking(true);
    setQuestion("");
    setTurns((previous) => [...previous, { question: trimmed, pending: true }]);
    try {
      const answer = await api.askConsultant(companyId, trimmed);
      setTurns((previous) =>
        previous.map((turn, index) =>
          index === previous.length - 1 ? { question: trimmed, answer } : turn,
        ),
      );
    } catch (error) {
      setTurns((previous) =>
        previous.map((turn, index) =>
          index === previous.length - 1
            ? { question: trimmed, error: error instanceof Error ? error.message : "咨询失败" }
            : turn,
        ),
      );
    } finally {
      setAsking(false);
    }
  };

  if (loading) return <AppShell><LoadingState label="正在准备 AI 顾问" /></AppShell>;

  return (
    <AppShell>
      <PageHeader
        eyebrow="AI Consultant"
        title="资金顾问"
        description="回答只基于你工作区的真实画像、资格判定与官方条款证据。找不到依据时明确返回「证据不足」，不做猜测。"
      />

      {companies.length === 0 ? (
        <InlineAlert tone="info">请先创建企业档案并运行政策扫描，顾问需要真实数据才能给出可追溯的回答。</InlineAlert>
      ) : null}

      <div className={flow.toolbar}>
        {companies.length > 1 ? (
          <select
            aria-label="选择企业"
            value={companyId}
            onChange={(event) => setCompanyId(event.target.value)}
            style={{ padding: "9px 12px", border: "1px solid #dde3eb", borderRadius: 8, fontSize: 13 }}
          >
            {companies.map((company) => (
              <option key={company.id} value={company.id}>{company.name}</option>
            ))}
          </select>
        ) : null}
      </div>

      <div className={content.stack} style={{ minHeight: 220 }}>
        {turns.length === 0 ? (
          <div className={content.card}>
            <div className={content.cardIntro} style={{ marginBottom: 12 }}>试试这些问题：</div>
            <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
              {PRESETS.map((preset) => (
                <Button key={preset} variant="secondary" disabled={!companyId || asking} onClick={() => ask(preset)}>
                  {preset}
                </Button>
              ))}
            </div>
          </div>
        ) : null}

        {turns.map((turn, index) => (
          <div key={index} className={content.card}>
            <div className={flow.itemTitle} style={{ marginBottom: 10 }}>
              <strong>{turn.question}</strong>
            </div>
            {turn.pending ? <div className={content.subtle}>正在检索证据…</div> : null}
            {turn.error ? <InlineAlert tone="error">{turn.error}</InlineAlert> : null}
            {turn.answer ? (
              <>
                <div style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap", marginBottom: 8 }}>
                  <Badge tone={turn.answer.insufficient ? "warning" : "success"}>
                    {turn.answer.insufficient ? "证据不足" : "有据可查"}
                  </Badge>
                  <span className={content.subtle} style={{ fontSize: 12 }}>
                    意图识别：{turn.answer.intent}
                  </span>
                </div>
                <p style={{ margin: "0 0 10px", fontSize: 14 }}>{turn.answer.summary}</p>
                {turn.answer.blocks.length ? (
                  <div className={flow.criteriaList}>
                    {turn.answer.blocks.map((block, blockIndex) => (
                      <div key={blockIndex} className={flow.criterion}>
                        <strong>{block.title}</strong>
                        {block.detail ? (
                          <div className={content.subtle} style={{ fontSize: 12, marginTop: 4 }}>
                            {Object.entries(block.detail)
                              .filter(([, value]) => value !== null && value !== undefined && value !== "")
                              .map(([key, value]) => `${key}: ${String(value)}`)
                              .join(" · ")}
                          </div>
                        ) : null}
                        <Citation citation={block.citation} />
                      </div>
                    ))}
                  </div>
                ) : null}
                {turn.answer.missing_evidence?.length ? (
                  <div className={flow.gapList} style={{ marginTop: 10 }}>
                    {turn.answer.missing_evidence.map((item, itemIndex) => (
                      <div key={itemIndex} className={content.subtle} style={{ fontSize: 13 }}>缺证据：{item}</div>
                    ))}
                  </div>
                ) : null}
                {turn.answer.next_actions.length ? (
                  <div className={content.actionRow} style={{ marginTop: 10 }}>
                    <span className={content.subtle} style={{ fontSize: 12 }}>建议：</span>
                    {turn.answer.next_actions.map((action) => (
                      <Badge key={action} tone="neutral">{action}</Badge>
                    ))}
                  </div>
                ) : null}
              </>
            ) : null}
          </div>
        ))}
        <div ref={bottomRef} />
      </div>

      <form
        onSubmit={(event) => {
          event.preventDefault();
          void ask(question);
        }}
        style={{ display: "flex", gap: 10, marginTop: 16 }}
      >
        <input
          value={question}
          onChange={(event) => setQuestion(event.target.value)}
          placeholder="例如：高企认定我们还差什么条件？"
          disabled={!companyId || asking}
          style={{ flex: 1, padding: "11px 14px", border: "1px solid #dde3eb", borderRadius: 10, fontSize: 14 }}
        />
        <Button type="submit" disabled={!companyId || asking || question.trim().length < 2}>
          {asking ? "检索中…" : "提问"}
        </Button>
      </form>
    </AppShell>
  );
}
