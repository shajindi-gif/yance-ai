"use client";

import { useRouter } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { DataTable } from "@/components/ui/DataTable";
import { EmptyState } from "@/components/ui/EmptyState";
import { InlineAlert } from "@/components/ui/InlineAlert";
import { LoadingState } from "@/components/ui/LoadingState";
import { PageHeader } from "@/components/ui/PageHeader";
import AppShell from "@/components/workspace/AppShell";
import flow from "@/components/workspace/CoreWorkflow.module.css";
import content from "@/components/workspace/WorkspaceContent.module.css";
import api, { type Company, type DocumentDetail, type DocumentRecord } from "@/lib/api";
import styles from "./Documents.module.css";

const INGESTION_LABELS: Record<string, { label: string; tone: "neutral" | "info" | "success" | "warning" | "danger" }> = {
  not_requested: { label: "未请求摄取", tone: "neutral" },
  pending: { label: "待解析", tone: "info" },
  processing: { label: "解析中", tone: "info" },
  completed: { label: "已解析", tone: "success" },
  failed: { label: "解析失败", tone: "danger" },
  ocr_required: { label: "需要 OCR", tone: "warning" },
};

const FIELD_LABELS: Record<string, string> = {
  industry: "所属行业",
  registered_address: "注册地址",
  founded_date: "成立日期",
  employee_count: "员工人数",
  annual_revenue: "年度营业收入",
  rd_expense_ratio: "研发投入占比",
  funding_stage: "融资阶段",
  high_tech_status: "高新企业情况",
  tech_sme_status: "科技型中小企业情况",
  specialized_sme_status: "专精特新情况",
  intellectual_property: "知识产权",
  core_products: "核心产品",
  projects: "项目情况",
  current_needs: "当前需求",
};

const MIME_BY_EXTENSION: Record<string, string> = {
  pdf: "application/pdf",
  docx: "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
  xlsx: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
  csv: "text/csv",
  txt: "text/plain",
};

export default function DocumentsPage() {
  const router = useRouter();
  const [documents, setDocuments] = useState<DocumentRecord[]>([]);
  const [companies, setCompanies] = useState<Company[]>([]);
  const [companyId, setCompanyId] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [working, setWorking] = useState("");
  const [detail, setDetail] = useState<DocumentDetail | null>(null);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const companyNames = useMemo(
    () => new Map(companies.map((company) => [company.id, company.name])),
    [companies],
  );

  const load = async () => {
    const [documentResult, companyResult] = await Promise.all([
      api.getDocuments(),
      api.getCompanies(),
    ]);
    setDocuments(documentResult);
    setCompanies(companyResult);
    setCompanyId((current) => current || companyResult[0]?.id || "");
  };

  useEffect(() => {
    if (!api.isAuthenticated()) {
      router.push("/login");
      return;
    }
    let active = true;
    load()
      .catch((loadError) => {
        if (active) {
          setError(loadError instanceof Error ? loadError.message : "企业资料加载失败");
        }
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [router]);

  const upload = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!file || !companyId) return;
    const extension = file.name.split(".").pop()?.toLowerCase() || "";
    const contentType = MIME_BY_EXTENSION[extension];
    if (!contentType) {
      setError("仅支持 PDF、DOCX、XLSX、CSV 和 TXT 文件");
      return;
    }
    const normalizedFile =
      file.type === contentType ? file : new File([file], file.name, { type: contentType });
    setUploading(true);
    setError("");
    setMessage("");
    try {
      const document = await api.uploadDocument(companyId, normalizedFile);
      setDocuments((current) => [document, ...current]);
      setFile(null);
      const input = window.document.getElementById("company-document") as HTMLInputElement | null;
      if (input) input.value = "";
      setMessage(
        document.ingestion_status === "completed"
          ? "文件已通过安全门禁并完成解析。请检查提取出的企业信息。"
          : document.ingestion_error || "文件已上传，摄取任务正在等待处理。",
      );
      const parsed = await api.getDocument(document.id);
      setDetail(parsed);
    } catch (uploadError) {
      setError(uploadError instanceof Error ? uploadError.message : "文件上传失败");
    } finally {
      setUploading(false);
    }
  };

  const openDetail = async (documentId: string) => {
    setWorking(documentId);
    setError("");
    try {
      setDetail(await api.getDocument(documentId));
    } catch (detailError) {
      setError(detailError instanceof Error ? detailError.message : "解析详情加载失败");
    } finally {
      setWorking("");
    }
  };

  const retryIngestion = async () => {
    if (!detail) return;
    setWorking(detail.document.id);
    setError("");
    try {
      const refreshed = await api.ingestDocument(detail.document.id, true);
      setDetail(refreshed);
      setDocuments((current) => current.map((item) => item.id === refreshed.document.id ? refreshed.document : item));
      setMessage(refreshed.document.ingestion_status === "completed" ? "重新解析已完成。" : refreshed.document.ingestion_error || "重新解析未完成。");
    } catch (retryError) {
      setError(retryError instanceof Error ? retryError.message : "重新解析失败");
    } finally {
      setWorking("");
    }
  };

  const reviewCandidate = async (candidateId: string, decision: "accept" | "reject") => {
    if (!detail) return;
    setWorking(candidateId);
    setError("");
    try {
      await api.reviewDocumentFacts(detail.document.id, [{ candidate_id: candidateId, decision }]);
      setDetail(await api.getDocument(detail.document.id));
      setMessage(decision === "accept" ? "信息已写入企业画像草稿，发布前仍可编辑。" : "该候选信息已拒绝。");
    } catch (reviewError) {
      setError(reviewError instanceof Error ? reviewError.message : "信息审阅失败");
    } finally {
      setWorking("");
    }
  };

  if (loading) {
    return (
      <AppShell>
        <LoadingState label="正在加载企业资料" />
      </AppShell>
    );
  }

  return (
    <AppShell>
      <PageHeader
        eyebrow="Documents"
        title="企业资料"
        description="文件进入隔离区后经过服务端校验、安全扫描、格式解析和证据化信息提取；候选信息需人工确认。"
      />
      {error && <InlineAlert>{error}</InlineAlert>}
      {message && <InlineAlert tone="info">{message}</InlineAlert>}

      <form className={content.card} onSubmit={upload}>
        <div className={flow.formGrid}>
          <div className={flow.field}>
            <label htmlFor="document-company">所属企业</label>
            <select id="document-company" value={companyId} onChange={(event) => setCompanyId(event.target.value)} required>
              <option value="">请选择企业</option>
              {companies.map((company) => <option key={company.id} value={company.id}>{company.name}</option>)}
            </select>
          </div>
          <div className={flow.fieldWide}>
            <label htmlFor="company-document">选择文件</label>
            <div className={flow.fileInput}>
              <input id="company-document" type="file" accept=".pdf,.docx,.xlsx,.csv,.txt" onChange={(event) => setFile(event.target.files?.[0] || null)} required />
            </div>
            <span className={flow.helper}>支持 PDF、DOCX、XLSX、CSV、TXT，单文件上限由服务端配置（默认 25 MiB）。扫描版 PDF 会明确标记为需要 OCR；网页 URL 在 SSRF 门禁验收前不开放。</span>
          </div>
        </div>
        <div className={content.actionRow}>
          <Button type="submit" disabled={uploading || !file || !companyId}>
            {uploading ? "上传中…" : "上传资料"}
          </Button>
        </div>
      </form>

      <section className={content.section}>
        <div className={content.sectionHeading}>
          <h2>资料记录</h2>
          <p>所有状态均来自服务端，不以浏览器上传完成代替摄取成功。</p>
        </div>
        {documents.length === 0 ? (
          <EmptyState icon="▤" title="暂无资料" description="选择企业并上传第一份真实资料。" />
        ) : (
          <div className={content.tableSurface}>
            <DataTable>
              <table className={content.table}>
                <thead><tr><th>文件</th><th>企业</th><th>大小</th><th>摄取状态</th><th>上传时间</th><th>操作</th></tr></thead>
                <tbody>
                  {documents.map((document) => {
                    const status = INGESTION_LABELS[document.ingestion_status] || { label: document.ingestion_status, tone: "neutral" as const };
                    return (
                      <tr key={document.id}>
                        <td>{document.filename}</td>
                        <td>{document.company_id ? companyNames.get(document.company_id) || "未知企业" : "未关联"}</td>
                        <td>{document.size_bytes == null ? "—" : `${(document.size_bytes / 1024).toFixed(1)} KiB`}</td>
                        <td><Badge tone={status.tone}>{status.label}</Badge></td>
                        <td>{new Date(document.created_at).toLocaleString("zh-CN")}</td>
                        <td><Button className={styles.documentButton} type="button" variant="secondary" disabled={working === document.id} onClick={() => openDetail(document.id)}>{working === document.id ? "加载中…" : "查看解析"}</Button></td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </DataTable>
          </div>
        )}
      </section>

      {detail ? (
        <section className={content.section} aria-live="polite">
          <div className={content.sectionHeading}>
            <div><h2>解析与企业智能</h2><p>{detail.document.filename} · {detail.chunk_count} 个可检索片段 · {detail.candidates.length} 条候选信息</p></div>
            {detail.document.ingestion_status === "failed" ? <Button type="button" variant="secondary" onClick={retryIngestion} disabled={working === detail.document.id}>重新解析</Button> : null}
          </div>
          {detail.document.metadata_json.security_scan && (detail.document.metadata_json.security_scan as { status?: string }).status !== "clean" ? (
            <InlineAlert tone="info">当前记录的恶意文件扫描状态为 {(detail.document.metadata_json.security_scan as { status?: string }).status || "未知"}；生产环境必须配置为强制扫描。</InlineAlert>
          ) : null}
          <div className={styles.detailGrid}>
            <div className={content.card}>
              <h2>内容摘要</h2>
              {detail.content ? <><p className={content.cardIntro}>{detail.content.parser} · {detail.content.character_count.toLocaleString("zh-CN")} 字符{detail.content.page_count ? ` · ${detail.content.page_count} 页` : ""}</p><pre className={styles.preview}>{detail.content.preview}</pre></> : <p className={content.cardIntro}>{detail.document.ingestion_error || "尚无可读取内容。"}</p>}
            </div>
            <div className={content.card}>
              <h2>摄取轨迹</h2>
              <div className={styles.runList}>{detail.ingestion_runs.map((run) => <div className={styles.runRow} key={run.id}><span>第 {run.attempt} 次 · {run.parser_version}</span><span>{run.status}{run.error_code ? ` · ${run.error_code}` : ""}</span></div>)}</div>
            </div>
          </div>
          <div className={`${content.card} ${content.section}`}>
            <h2>待确认企业信息</h2>
            <p className={content.cardIntro}>每条信息都保留原文片段和置信度；接受后只写入画像草稿，不会自动发布。</p>
            {detail.candidates.length === 0 ? <EmptyState icon="⌁" title="暂无候选信息" description="文档可能未使用明确字段标签，或尚未完成解析。" /> : <div className={styles.candidateList}>{detail.candidates.map((candidate) => <article className={styles.candidate} key={candidate.id}><div className={styles.candidateHeader}><strong>{FIELD_LABELS[candidate.field_key] || candidate.field_key}</strong><div className={flow.inlineMeta}><Badge tone={candidate.status === "accepted" ? "success" : candidate.status === "rejected" ? "danger" : "info"}>{candidate.status === "accepted" ? "已接受" : candidate.status === "rejected" ? "已拒绝" : "待确认"}</Badge><Badge tone="neutral">置信度 {(candidate.confidence * 100).toFixed(0)}%</Badge></div></div><p className={styles.candidateValue}>{Array.isArray(candidate.value_json.value) ? candidate.value_json.value.join("、") : String(candidate.value_json.value ?? "—")}</p><blockquote className={styles.candidateEvidence}>{candidate.evidence_excerpt}</blockquote>{candidate.status === "pending_review" ? <div className={styles.candidateActions}><Button type="button" variant="secondary" disabled={working === candidate.id} onClick={() => reviewCandidate(candidate.id, "reject")}>拒绝</Button><Button type="button" disabled={working === candidate.id} onClick={() => reviewCandidate(candidate.id, "accept")}>接受并写入草稿</Button></div> : null}</article>)}</div>}
          </div>
        </section>
      ) : null}
    </AppShell>
  );
}
