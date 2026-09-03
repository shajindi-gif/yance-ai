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
import api, { type Company, type DocumentRecord } from "@/lib/api";

const INGESTION_LABELS: Record<string, { label: string; tone: "neutral" | "info" | "success" | "danger" }> = {
  not_requested: { label: "未请求摄取", tone: "neutral" },
  pending: { label: "待解析", tone: "info" },
  processing: { label: "解析中", tone: "info" },
  completed: { label: "已解析", tone: "success" },
  failed: { label: "解析失败", tone: "danger" },
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
      setMessage("文件已上传并进入待解析队列。解析器将在 RAG 阶段接入。 ");
    } catch (uploadError) {
      setError(uploadError instanceof Error ? uploadError.message : "文件上传失败");
    } finally {
      setUploading(false);
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
        description="文件直接上传到租户隔离的对象路径；上传成功不等于解析完成。"
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
            <span className={flow.helper}>支持 PDF、DOCX、XLSX、CSV、TXT，单文件上限由服务端配置（默认 25 MiB）。网页 URL 摄取尚未开放。</span>
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
                <thead><tr><th>文件</th><th>企业</th><th>大小</th><th>摄取状态</th><th>上传时间</th></tr></thead>
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
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </DataTable>
          </div>
        )}
      </section>
    </AppShell>
  );
}
