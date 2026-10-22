import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { DataTable } from "@/components/ui/DataTable";
import { InlineAlert } from "@/components/ui/InlineAlert";
import type { EvidenceMatrix as Matrix } from "@/lib/api";
import styles from "./EvidenceMatrix.module.css";

const LABELS: Record<string, string> = { PASS: "条件满足", FAIL: "条件不满足", MISSING: "证据不足", UNVERIFIED_SOURCE: "原文待核验", UNSUPPORTED: "需人工复核" };
const value = (input: unknown) => input == null || input === "" ? "尚未提供" : typeof input === "object" ? JSON.stringify(input) : String(input);
const safeUrl = (url: string | null) => {
  try { const parsed = new URL(url || ""); return ["https:", "http:"].includes(parsed.protocol) ? parsed.href : null; }
  catch { return null; }
};

export function EvidenceMatrix({ matrix, busy, canWrite, onCollect }: { matrix?: Matrix; busy: boolean; canWrite: boolean; onCollect: () => void }) {
  if (!matrix) return <InlineAlert tone="info">当前接口尚未提供资格矩阵，请刷新或联系管理员核对版本。</InlineAlert>;
  return <section className={styles.panel} aria-label="资格审查矩阵">
    <div className={styles.heading}><div><h2>资格审查矩阵</h2><p>逐条核对政策条件与企业事实；条件满足仍须人工复核，不代表获批。</p></div><Button type="button" onClick={onCollect} disabled={busy || !canWrite || !matrix.rows.some(row => row.status !== "PASS")}>创建补证待办</Button></div>
    {matrix.context_issues.length > 0 ? <InlineAlert tone="info">{matrix.context_issues.join("；")}</InlineAlert> : null}
    {matrix.rows.length === 0 ? <p>尚无可核验条件。请先确认企业资料并重新扫描政策资格。</p> : <DataTable><table className={styles.matrix}>
      <caption>政策条件、企业事实和原文引用对照</caption>
      <thead><tr><th scope="col">政策条件</th><th scope="col">企业事实</th><th scope="col">判断</th><th scope="col">原文证据</th></tr></thead>
      <tbody>{matrix.rows.map((row, index) => <tr key={row.rule_id || index}>
        <th scope="row">{row.name}<small>{row.is_hard_gate ? "硬条件" : "参考条件"} · 要求：{value(row.expected)}</small></th>
        <td>{value(row.actual)}<small>{row.fact_source}</small><small>画像版本：{row.profile_version_id || "未固定"}</small></td>
        <td><Badge tone={row.status === "PASS" ? "success" : row.status === "FAIL" ? "danger" : "warning"}>{LABELS[row.status] || "需人工复核"}</Badge></td>
        <td>{row.policy_evidence.length === 0 ? "缺少逐条原文引用" : row.policy_evidence.map(item => {
          const url = safeUrl(item.source_url);
          return <details key={item.id}><summary>{item.article || "查看政策原文"} · {item.verified ? "逐字核验" : "待核验"}</summary><blockquote>{item.quote}</blockquote>{url ? <a href={url} target="_blank" rel="noopener noreferrer">打开来源网页</a> : <span>来源链接未核实</span>}</details>;
        })}</td>
      </tr>)}</tbody>
    </table></DataTable>}
    {matrix.missing_information.length > 0 ? <div><h3>待补充与复核</h3><ul>{matrix.missing_information.map((item, index) => <li key={index}>{item}</li>)}</ul></div> : null}
  </section>;
}
