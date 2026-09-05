'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import Link from 'next/link';
import api, { DemoScenarioDetail, DemoScenarioList } from '@/lib/api';
import styles from './Demo.module.css';

const steps = [
  { key: 'profile', label: 'Company Profile', short: '企业画像' },
  { key: 'document', label: 'Company Intelligence', short: '资料解析' },
  { key: 'scan', label: 'Policy Scan', short: '机会扫描' },
  { key: 'eligibility', label: 'Eligibility', short: '资格判断' },
  { key: 'evidence', label: 'Evidence', short: '证据核验' },
  { key: 'application', label: 'Application', short: '申报工作区' },
  { key: 'artifact', label: 'Deliverable', short: '生成文件' },
] as const;

type StepKey = (typeof steps)[number]['key'];
type ExportFormat = 'docx' | 'pdf' | 'xlsx' | 'json';

function valueText(value: unknown): string {
  if (Array.isArray(value)) return value.join('、');
  if (value === null || value === undefined || value === '') return '未提供';
  return String(value);
}

function statusLabel(status: string): string {
  return {
    ELIGIBLE: 'Eligible', POTENTIALLY_ELIGIBLE: 'Potentially Eligible',
    NOT_ELIGIBLE: 'Not Eligible', NEED_MORE_INFORMATION: 'Need More Information',
    met: '已满足', missing: '待补齐', ready: '已就绪', review: '待复核', completed: '已完成',
  }[status] || status;
}

export default function DemoExperience() {
  const [catalog, setCatalog] = useState<DemoScenarioList | null>(null);
  const [detail, setDetail] = useState<DemoScenarioDetail | null>(null);
  const [selectedKey, setSelectedKey] = useState('');
  const [activeStep, setActiveStep] = useState<StepKey>('profile');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [downloading, setDownloading] = useState<string | null>(null);
  const requestIdRef = useRef(0);

  const loadCatalog = useCallback(async () => {
    const requestId = ++requestIdRef.current;
    setLoading(true);
    setError('');
    try {
      const result = await api.getDemoScenarios();
      if (requestId !== requestIdRef.current) return;
      setCatalog(result);
      const firstKey = result.items[0]?.key || '';
      setSelectedKey(firstKey);
      const nextDetail = firstKey ? await api.getDemoScenario(firstKey) : null;
      if (requestId === requestIdRef.current) setDetail(nextDetail);
    } catch (reason) {
      if (requestId === requestIdRef.current) {
        setError(reason instanceof Error ? reason.message : '演示数据加载失败');
      }
    } finally {
      if (requestId === requestIdRef.current) setLoading(false);
    }
  }, []);

  useEffect(() => { void loadCatalog(); }, [loadCatalog]);

  const selectScenario = async (key: string) => {
    const requestId = ++requestIdRef.current;
    setSelectedKey(key);
    setActiveStep('profile');
    setLoading(true);
    setError('');
    try {
      const nextDetail = await api.getDemoScenario(key);
      if (requestId === requestIdRef.current) setDetail(nextDetail);
    } catch (reason) {
      if (requestId === requestIdRef.current) {
        setError(reason instanceof Error ? reason.message : '演示场景加载失败');
      }
    } finally {
      if (requestId === requestIdRef.current) setLoading(false);
    }
  };

  const activeIndex = steps.findIndex((step) => step.key === activeStep);
  const move = (delta: number) => {
    const next = Math.max(0, Math.min(steps.length - 1, activeIndex + delta));
    setActiveStep(steps[next].key);
  };

  const download = async (format: ExportFormat) => {
    if (!detail) return;
    setDownloading(format);
    setError('');
    try {
      const blob = await api.downloadDemoArtifact(detail.key, detail.artifact.id, format);
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement('a');
      anchor.href = url;
      anchor.download = `demo-${detail.key}.${format}`;
      anchor.click();
      URL.revokeObjectURL(url);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : '文件下载失败');
    } finally {
      setDownloading(null);
    }
  };

  return (
    <main id="main-content" className={styles.page}>
      <section className={styles.hero}>
        <div className={styles.eyebrow}><span>DEMO</span> Investor product walkthrough</div>
        <h1>在 3–5 分钟内，看 AI 完成一次企业政策与申报工作。</h1>
        <p>从企业资料到证据、缺口、任务和可下载文件。页面读取真实产品数据结构，不连接真实客户数据。</p>
        <div className={styles.notice} role="note">
          <strong>合成数据边界</strong>
          <span>所有公司、政策、机构、权益和结果均为 DEMO 示例，不代表客户、政府合作、收入、准确率或申报结果。</span>
        </div>
      </section>

      <section className={styles.shell} aria-busy={loading}>
        <aside className={styles.scenarios} aria-label="演示企业">
          <div className={styles.asideTitle}>
            <span>选择企业</span>
            {catalog?.dataset_version && <code>{catalog.dataset_version}</code>}
          </div>
          {catalog?.items.map((item) => (
            <button key={item.key} type="button"
              className={selectedKey === item.key ? styles.scenarioActive : styles.scenario}
              onClick={() => void selectScenario(item.key)}>
              <span>{item.industry}</span><strong>{item.title}</strong><small>{item.persona}</small>
            </button>
          ))}
          {!loading && catalog?.items.length === 0 && (
            <div className={styles.empty}>No demo data yet.<br />运行安全演示数据初始化后重试。</div>
          )}
        </aside>

        <div className={styles.workspace}>
          {loading && !detail && <div className={styles.loading} aria-live="polite"><div /><div /><div /><span>正在加载完整工作流…</span></div>}
          {error && <div className={styles.error} role="alert"><div><strong>暂时无法加载演示</strong><span>{error}</span></div><button type="button" onClick={() => void loadCatalog()}>重试</button></div>}
          {detail && <>
            <header className={styles.workspaceHeader}>
              <div><span className={styles.demoPill}>DEMO · SYNTHETIC</span><h2>{detail.company.name}</h2><p>{detail.summary}</p></div>
              <div className={styles.headerMetric}><span>Workflow</span><strong>7 / 7</strong><small>持久化步骤</small></div>
            </header>

            <nav className={styles.stepper} aria-label="演示流程">
              {steps.map((step, index) => <button key={step.key} type="button" onClick={() => setActiveStep(step.key)}
                className={activeStep === step.key ? styles.stepActive : styles.step}
                aria-current={activeStep === step.key ? 'step' : undefined}>
                <span>{index + 1}</span><b>{step.short}</b><small>{step.label}</small>
              </button>)}
            </nav>

            <div className={styles.stage}>
              {activeStep === 'profile' && <ProfileStage detail={detail} />}
              {activeStep === 'document' && <DocumentStage detail={detail} />}
              {activeStep === 'scan' && <ScanStage detail={detail} />}
              {activeStep === 'eligibility' && <EligibilityStage detail={detail} />}
              {activeStep === 'evidence' && <EvidenceStage detail={detail} />}
              {activeStep === 'application' && <ApplicationStage detail={detail} />}
              {activeStep === 'artifact' && <ArtifactStage detail={detail} downloading={downloading} onDownload={download} />}
            </div>

            <footer className={styles.stageFooter}>
              <button type="button" onClick={() => move(-1)} disabled={activeIndex === 0}>上一步</button>
              <span>{activeIndex + 1} / {steps.length} · {steps[activeIndex].label}</span>
              {activeIndex < steps.length - 1
                ? <button type="button" className={styles.primary} onClick={() => move(1)}>继续演示</button>
                : <Link className={styles.primary} href="/login?register=1">创建自己的 Workspace</Link>}
            </footer>
          </>}
        </div>
      </section>
    </main>
  );
}

function Panel({ title, kicker, children }: { title: string; kicker: string; children: React.ReactNode }) {
  return <section className={styles.panel}><span className={styles.kicker}>{kicker}</span><h3>{title}</h3>{children}</section>;
}

function ProfileStage({ detail }: { detail: DemoScenarioDetail }) {
  const fields = [
    ['行业', detail.company.profile.industry], ['地区', detail.company.profile.city],
    ['企业规模', detail.company.profile.company_scale], ['营收阶段', detail.company.profile.revenue_stage],
    ['融资阶段', detail.company.profile.funding_stage], ['核心产品', detail.company.profile.core_products],
    ['研发情况', detail.company.profile.rd_summary], ['当前需求', detail.company.profile.current_needs],
  ];
  return <Panel kicker="STEP 1" title="结构化企业画像">
    <div className={styles.scoreRow}><strong>{detail.company.completeness_score}%</strong><span>画像完整度 · Version {detail.company.profile_version}</span></div>
    <dl className={styles.fieldGrid}>{fields.map(([label, value]) => <div key={String(label)}><dt>{String(label)}</dt><dd>{valueText(value)}</dd></div>)}</dl>
  </Panel>;
}

function DocumentStage({ detail }: { detail: DemoScenarioDetail }) {
  return <Panel kicker="STEP 2" title="资料解析为 Company Intelligence">
    <div className={styles.documentCard}><div className={styles.fileIcon}>TXT</div><div><strong>{detail.document.filename}</strong><span>{detail.document.content_type} · 明确标注 synthetic metadata</span></div><em>解析完成</em></div>
    <div className={styles.callout}>系统保留原始资料引用边界，将抽取结果写入不可变企业画像版本；本案例不存储真实客户文件。</div>
  </Panel>;
}

function ScanStage({ detail }: { detail: DemoScenarioDetail }) {
  return <Panel kicker="STEP 3" title="Policy / Opportunity Scan">
    <div className={styles.metricGrid}>
      <div><span>Match Score</span><strong>{detail.opportunity.match_score}</strong></div>
      <div><span>Opportunities</span><strong>{detail.scan.total_opportunities}</strong></div>
      <div><span>Evidence</span><strong>{detail.opportunity.evidence_count}</strong></div>
      <div><span>Status</span><strong>{statusLabel(detail.scan.status)}</strong></div>
    </div>
    <article className={styles.opportunity}><div><small>{detail.opportunity.policy_type} · {detail.opportunity.region}</small><h4>{detail.opportunity.title}</h4><p>{detail.opportunity.authority}</p></div><span>{statusLabel(detail.opportunity.eligibility)}</span></article>
  </Panel>;
}

function EligibilityStage({ detail }: { detail: DemoScenarioDetail }) {
  return <Panel kicker="STEP 4" title="四态资格判断，不用模糊自然语言代替结论">
    <div className={styles.decision}><span>{statusLabel(detail.eligibility.status)}</span><strong>{Math.round(detail.eligibility.confidence * 100)}% confidence</strong><p>{detail.eligibility.summary}</p></div>
    <div className={styles.list}>{detail.eligibility.criteria.map((item, index) => <div key={index}><span className={item.status === 'met' ? styles.ok : styles.warn}>{statusLabel(String(item.status))}</span><strong>{String(item.name)}</strong><small>实际：{String(item.actual)} · 硬门槛：{item.hard_gate ? '是' : '否'}</small></div>)}</div>
  </Panel>;
}

function EvidenceStage({ detail }: { detail: DemoScenarioDetail }) {
  return <Panel kicker="STEP 5" title="Evidence Engine：结论可回到精确原文">
    {detail.evidence.map((item) => <blockquote key={item.id} className={styles.evidence}>
      <div><span>{item.verified ? 'Exact span verified' : 'Unverified'}</span><strong>{item.article}</strong></div>
      <p>“{item.quote}”</p>
      <footer><strong>{item.source_title}</strong><span>{item.issuer} · {item.region}</span><a href={item.source_url} target="_blank" rel="noreferrer">合成来源标识</a></footer>
    </blockquote>)}
  </Panel>;
}

function ApplicationStage({ detail }: { detail: DemoScenarioDetail }) {
  return <Panel kicker="STEP 6" title="Application Workspace：缺口变成可执行任务">
    <div className={styles.progress}><div><span>完成率</span><strong>{detail.application.progress}%</strong></div><div><i style={{ width: `${detail.application.progress}%` }} /></div></div>
    <div className={styles.splitLists}>
      <div><h4>Required Documents</h4>{detail.application.requirements.map((item) => <div className={styles.row} key={item.id}><span className={item.status === 'ready' ? styles.ok : styles.warn}>{statusLabel(item.status)}</span><div><strong>{item.title}</strong><small>{item.is_hard_gate ? '硬门槛' : '补充材料'}</small></div></div>)}</div>
      <div><h4>Tasks</h4>{detail.application.tasks.map((item) => <div className={styles.row} key={item.id}><span>{item.progress}%</span><div><strong>{item.title}</strong><small>{statusLabel(item.status)} · {item.priority}</small></div></div>)}</div>
    </div>
    <div className={styles.nextAction}><span>Next Best Action</span><strong>{detail.next_best_action}</strong></div>
  </Panel>;
}

function ArtifactStage({ detail, downloading, onDownload }: { detail: DemoScenarioDetail; downloading: string | null; onDownload: (format: ExportFormat) => Promise<void> }) {
  return <Panel kicker="STEP 7" title="版本化交付物：由生产渲染器实时生成">
    <article className={styles.artifact}><div className={styles.fileIcon}>DOC</div><div><strong>{detail.artifact.title}</strong><span>Version {detail.artifact.version} · {detail.artifact.generation_method}</span><code>{detail.artifact.checksum_sha256.slice(0, 16)}…</code></div><em>待人工复核</em></article>
    <div className={styles.downloads}>{detail.artifact.formats.map((format) => <button type="button" key={format} disabled={downloading !== null} onClick={() => void onDownload(format)}>{downloading === format ? '生成中…' : `下载 ${format.toUpperCase()}`}</button>)}</div>
    <div className={styles.agentTrace}><div><span>Agent Run</span><strong>{detail.agent_run.status}</strong><small>{detail.agent_run.model} · {detail.agent_run.latency_ms} ms · $0 deterministic demo</small></div><div className={styles.traceSteps}>{detail.agent_run.steps.map((step) => <span key={step.sequence}>{step.sequence}. {step.type}</span>)}</div></div>
  </Panel>;
}
