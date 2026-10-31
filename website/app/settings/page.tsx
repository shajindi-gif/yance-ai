"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { InlineAlert } from "@/components/ui/InlineAlert";
import { LoadingState } from "@/components/ui/LoadingState";
import { PageHeader } from "@/components/ui/PageHeader";
import SmsAuth from "@/components/auth/SmsAuth";
import AppShell from "@/components/workspace/AppShell";
import styles from "@/components/workspace/Enterprise.module.css";
import api, { type EnterpriseSettings } from "@/lib/api";

export default function SettingsPage() {
  const [smsEnabled, setSmsEnabled] = useState(false);
  useEffect(() => { let active = true; api.getAuthConfig().then(cfg => { if (active) setSmsEnabled(cfg.sms_login_enabled === true); }).catch(() => { if (active) setSmsEnabled(false); }); return () => { active = false; }; }, []);
  const [data, setData] = useState<EnterpriseSettings | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [secret, setSecret] = useState("");
  const load = useCallback(async () => { setError(""); try { setData(await api.getEnterpriseSettings()); } catch (loadError) { setError(loadError instanceof Error ? loadError.message : "企业设置加载失败"); } finally { setLoading(false); } }, []);
  useEffect(() => { if (!api.isAuthenticated()) { setError("请先登录 企业所有者或管理员账号。"); setLoading(false); return; } void load(); }, [load]);
  const run = async (action: () => Promise<unknown>) => { setBusy(true); setError(""); try { await action(); await load(); } catch (actionError) { setError(actionError instanceof Error ? actionError.message : "操作失败"); } finally { setBusy(false); } };
  const issueKey = () => run(async () => { const result = await api.createApiKey("Workspace integration", ["read"]); setSecret(result.secret); });
  const exportWorkspace = () => run(() => api.createWorkspaceExport());
  const download = async (id: string) => { try { const blob = await api.downloadWorkspaceExport(id); const url = URL.createObjectURL(blob); const anchor = document.createElement("a"); anchor.href = url; anchor.download = `yance-workspace-${id}.json`; anchor.click(); URL.revokeObjectURL(url); } catch (downloadError) { setError(downloadError instanceof Error ? downloadError.message : "下载失败"); } };
  if (loading) return <AppShell><LoadingState label="正在读取企业控制项" /></AppShell>;
  return <AppShell>
    <PageHeader eyebrow="企业管理" title="企业设置" description="API 密钥、数据导出、保留策略与删除请求均由后端权限和审计记录约束。" />
    {smsEnabled && api.isAuthenticated() && <section className={styles.panel}><h2>绑定手机号</h2><SmsAuth binding /></section>}
    {error ? <InlineAlert tone="error">{error}</InlineAlert> : null}
    {error && !data ? <Button type="button" variant="secondary" onClick={() => { setLoading(true); void load(); }}>重新加载企业设置</Button> : null}
    {secret ? <div className={styles.secret}><strong>仅显示一次：</strong> {secret}</div> : null}
    {data ? <div className={styles.stack}>
      <section className={styles.panel}><div className={styles.panelHeader}><div><h2>API 密钥</h2><p>原始密钥只返回一次；数据库只保存带 pepper 的哈希。API Key 无法访问账单、成员、Admin 或企业控制面。</p></div><Button type="button" disabled={busy} onClick={issueKey}>创建只读密钥</Button></div><div className={styles.rows}>{data.apiKeys.length ? data.apiKeys.map((key) => <div className={styles.row} key={key.id}><div><strong>{key.name}</strong><p>yance_live_{key.prefix}_… · {key.scopes.join(", ")}</p></div><span>{key.last_used_at ? `最近使用 ${new Date(key.last_used_at).toLocaleString("zh-CN")}` : "从未使用"}</span>{key.revoked_at ? <Badge tone="neutral">已撤销</Badge> : <Button type="button" variant="secondary" disabled={busy} onClick={() => run(() => api.revokeApiKey(key.id))}>撤销</Button>}</div>) : <p className={styles.muted}>尚未创建 API 密钥。</p>}</div></section>
      <section className={styles.panel}><div className={styles.panelHeader}><div><h2>数据保留策略</h2><p>这里只展示真实策略。自动清理 worker 尚未启用，因此不会声称已执行删除。</p></div><Badge tone={data.retention.legal_hold ? "warning" : "neutral"}>{data.retention.legal_hold ? "保留锁定" : "未锁定保留"}</Badge></div><dl className={styles.definition}><div><dt>文档</dt><dd>{data.retention.document_days} 天</dd></div><div><dt>任务记录</dt><dd>{data.retention.agent_trace_days} 天</dd></div><div><dt>使用分析</dt><dd>{data.retention.analytics_days} 天</dd></div><div><dt>审计记录</dt><dd>{data.retention.audit_days} 天</dd></div></dl></section>
      <section className={styles.panel}><div className={styles.panelHeader}><div><h2>工作区数据导出</h2><p>导出不包含密码哈希、API Key 哈希、支付原始响应或文档对象存储 Key。</p></div><Button type="button" disabled={busy} onClick={exportWorkspace}>生成 JSON 导出</Button></div><div className={styles.rows}>{data.exports.map((job) => <div className={styles.row} key={job.id}><strong>{job.scope} · {job.status}</strong><span>{job.checksum_sha256?.slice(0, 16) || "无校验值"}</span><Button type="button" variant="secondary" onClick={() => void download(job.id)}>下载</Button></div>)}</div></section>
      <section className={styles.panel}><div className={styles.panelHeader}><div><h2>Delete Workspace</h2><p>请求有 7 天冷静期；当前部署尚未配置跨存储、日志、备份与模型供应商的传播 worker。</p></div></div>{data.deletion.request ? <div className={styles.row}><div><strong>已安排</strong><p>{new Date(data.deletion.request.scheduled_for).toLocaleString("zh-CN")}</p></div><Badge tone="warning">{data.deletion.request.status}</Badge><Button type="button" variant="secondary" disabled={busy} onClick={() => run(() => api.cancelWorkspaceDeletion(data.deletion.request!.id))}>取消请求</Button></div> : <Button type="button" variant="secondary" disabled={busy} onClick={() => { if (window.confirm("确认安排工作区删除请求？这不会立即删除数据。")) void run(() => api.scheduleWorkspaceDeletion("owner_requested")); }}>安排删除请求</Button>}</section>
      <section className={styles.panel}><div className={styles.panelHeader}><div><h2>意见反馈</h2><p>在反馈中心提交问题、建议或数据纠错，并查看本账号的处理进度。</p></div><Link href="/feedback">前往反馈中心 →</Link></div></section>
    </div> : null}
  </AppShell>;
}
