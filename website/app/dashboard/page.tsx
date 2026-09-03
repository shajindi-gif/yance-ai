'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import api from '@/lib/api';
import AppShell from '@/components/workspace/AppShell';
import { InlineAlert } from '@/components/ui/InlineAlert';
import { LoadingState } from '@/components/ui/LoadingState';
import { PageHeader } from '@/components/ui/PageHeader';

/* --- Types --- */
interface TenantInfo {
  name: string;
  slug: string;
}

interface CompanyInfo {
  id: string;
  name: string;
  industry?: string;
  city?: string;
  province?: string;
}

interface OrderInfo {
  id: string;
  product_code: string;
  amount: number;
  status: string;
  created_at: string;
}

interface MatchResult {
  company_name: string;
  total_matches: number;
  preview: any[];
  full: any[];
  ai_summary: string;
  provider_used: string;
}

/* --- Status Badge --- */
function StatusBadge({ status }: { status: string }) {
  const styles: Record<string, { bg: string; color: string; label: string }> = {
    pending: { bg: '#fef3c7', color: '#92400e', label: '待支付' },
    paid: { bg: '#d1fae5', color: '#065f46', label: '已支付' },
    draft: { bg: '#f3f4f6', color: '#6b7280', label: '草稿' },
    published: { bg: '#d1fae5', color: '#065f46', label: '已发布' },
  };
  const style = styles[status] || { bg: '#f3f4f6', color: '#6b7280', label: status };
  return (
    <span style={{
      display: 'inline-block', padding: '3px 10px', borderRadius: '12px',
      fontSize: '12px', fontWeight: 500, background: style.bg, color: style.color,
    }}>
      {style.label}
    </span>
  );
}

/* --- Score Badge --- */
function ScoreBadge({ score }: { score: number }) {
  const color = score >= 80 ? '#16a34a' : score >= 60 ? '#ea580c' : '#dc2626';
  return (
    <span style={{ fontWeight: 700, color, fontSize: '15px' }}>{score}%</span>
  );
}

export default function DashboardPage() {
  const router = useRouter();
  const [loading, setLoading] = useState(true);
  const [authenticated, setAuthenticated] = useState(false);
  const [tenant, setTenant] = useState<TenantInfo | null>(null);
  const [companies, setCompanies] = useState<CompanyInfo[]>([]);
  const [orders, setOrders] = useState<any[]>([]);
  const [error, setError] = useState('');

  // Company form
  const [showCompanyForm, setShowCompanyForm] = useState(false);
  const [companyName, setCompanyName] = useState('');
  const [companyIndustry, setCompanyIndustry] = useState('');
  const [companyProvince, setCompanyProvince] = useState('');
  const [companyCity, setCompanyCity] = useState('');
  const [creatingCompany, setCreatingCompany] = useState(false);

  // Report
  const [matchResult, setMatchResult] = useState<MatchResult | null>(null);
  const [generating, setGenerating] = useState(false);
  const [selectedProvider, setSelectedProvider] = useState('qwen');
  const [stats, setStats] = useState<any>(null);

  useEffect(() => {
    const init = async () => {
      if (!api.isAuthenticated()) { router.push('/login'); return; }
      try {
        const [t, c, o] = await Promise.all([api.getTenant(), api.getCompanies(), api.getOrders()]);
        setTenant({ name: t.name, slug: t.slug });
        setCompanies(c);
        setOrders(o);
        setAuthenticated(true);
        // Load analytics stats (data flywheel)
        api.getStats().then(setStats).catch(() => {});
      } catch (err) {
        setError(err instanceof Error ? err.message : '加载失败');
        api.clearToken();
        router.push('/login');
      } finally { setLoading(false); }
    };
    init();
  }, [router]);

  const handleCreateCompany = async (e: React.FormEvent) => {
    e.preventDefault();
    setCreatingCompany(true);
    try {
      const newCompany = await api.createCompany({
        name: companyName, industry: companyIndustry,
        province: companyProvince, city: companyCity,
      });
      setCompanies(prev => [...prev, newCompany]);
      setShowCompanyForm(false);
      setCompanyName(''); setCompanyIndustry(''); setCompanyProvince(''); setCompanyCity('');
    } catch (err) {
      setError(err instanceof Error ? err.message : '创建失败');
    } finally { setCreatingCompany(false); }
  };

  const handleGenerateReport = async () => {
    if (companies.length === 0) return;
    setGenerating(true); setError('');
    try {
      const result = await api.matchReport(companies[0].id, selectedProvider);
      setMatchResult(result);
      // Refresh stats after report generation
      api.getStats().then(setStats).catch(() => {});
    } catch (err) {
      setError(err instanceof Error ? err.message : '生成失败');
    } finally { setGenerating(false); }
  };

  if (loading) {
    return (
      <AppShell>
        <LoadingState label="正在加载企业工作台" />
      </AppShell>
    );
  }

  if (!authenticated) return null;

  return (
    <AppShell workspaceName={tenant?.name}>
      <div className="yc-dashboard">
        <PageHeader
          eyebrow="Home"
          title="工作台"
          description={`${tenant?.name || '企业工作区'}${tenant?.slug ? ` · ${tenant.slug}` : ''}。这里仅展示数据库返回的企业、机会与交易数据。`}
        />

        {error && <InlineAlert>{error}</InlineAlert>}

      {/* Metrics */}
      <div className="yc-dash-metrics">
        <div className="yc-dash-metric-card">
          <div className="yc-dash-metric-value">{companies.length}</div>
          <div className="yc-dash-metric-label">企业档案</div>
        </div>
        <div className="yc-dash-metric-card">
          <div className="yc-dash-metric-value">{matchResult?.total_matches ?? '—'}</div>
          <div className="yc-dash-metric-label">匹配政策</div>
        </div>
        <div className="yc-dash-metric-card">
          <div className="yc-dash-metric-value">{orders.length}</div>
          <div className="yc-dash-metric-label">订单</div>
        </div>
        <div className="yc-dash-metric-card">
          <div className="yc-dash-metric-value">
            ¥{orders.filter(o => o.status === 'paid').reduce((s, o) => s + o.amount, 0).toLocaleString()}
          </div>
          <div className="yc-dash-metric-label">已支付</div>
        </div>
      </div>

      {/* Company Profile */}
      <div className="yc-dash-section">
        <h2>企业档案</h2>
        {companies.length === 0 ? (
          showCompanyForm ? (
            <form onSubmit={handleCreateCompany} className="yc-dash-company-form">
              <div className="yc-dash-form-row">
                <label>企业名称</label>
                <input value={companyName} onChange={e => setCompanyName(e.target.value)} placeholder="如：上海某某科技有限公司" required />
              </div>
              <div className="yc-dash-form-row">
                <label>行业</label>
                <select value={companyIndustry} onChange={e => setCompanyIndustry(e.target.value)}>
                  <option value="">请选择</option>
                  <option value="人工智能">人工智能</option>
                  <option value="软件与信息技术">软件与信息技术</option>
                  <option value="生物医药">生物医药</option>
                  <option value="高端制造">高端制造</option>
                  <option value="新材料">新材料</option>
                  <option value="其他">其他</option>
                </select>
              </div>
              <div className="yc-dash-form-row">
                <label>省份</label>
                <input value={companyProvince} onChange={e => setCompanyProvince(e.target.value)} placeholder="如：上海市" />
              </div>
              <div className="yc-dash-form-row">
                <label>城市</label>
                <input value={companyCity} onChange={e => setCompanyCity(e.target.value)} placeholder="如：徐汇区" />
              </div>
              <div className="yc-dash-form-actions">
                <button type="submit" disabled={creatingCompany}>{creatingCompany ? '创建中...' : '创建企业'}</button>
                <button type="button" onClick={() => setShowCompanyForm(false)}>取消</button>
              </div>
            </form>
          ) : (
            <button className="yc-dash-btn-primary" onClick={() => setShowCompanyForm(true)}>+ 创建企业档案</button>
          )
        ) : (
          <div className="yc-dash-company-info">
            <div className="yc-dash-company-card">
              <div className="yc-dash-company-name">{companies[0].name}</div>
              <div className="yc-dash-company-meta">
                {companies[0].industry && <span>{companies[0].industry}</span>}
                {companies[0].province && <span>{companies[0].province}{companies[0].city ? ` · ${companies[0].city}` : ''}</span>}
              </div>
            </div>
            <div className="yc-dash-company-actions">
              <select
                className="yc-dash-model-select"
                aria-label="选择政策匹配模型提供方"
                value={selectedProvider}
                onChange={e => setSelectedProvider(e.target.value)}
              >
                <option value="qwen">通义千问 Qwen</option>
                <option value="deepseek">DeepSeek V3</option>
                <option value="openai">OpenAI GPT-4o</option>
              </select>
              <button className="yc-dash-btn-primary" onClick={handleGenerateReport} disabled={generating}>
                {generating ? '生成中...' : '生成政策匹配报告'}
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Match Report */}
      {matchResult && (
        <div className="yc-dash-section">
          <h2>政策匹配报告 — {matchResult.company_name}</h2>
          <p className="yc-dash-match-summary">
            {matchResult.full.length > 0 ? (
              <>
                匹配到 <strong>{matchResult.total_matches}</strong> 项政策，平均匹配度{' '}
                <strong>{Math.round(matchResult.full.reduce((s, m) => s + m.score_pct, 0) / matchResult.full.length)}%</strong>，
                最高 <strong>{Math.max(...matchResult.full.map(m => m.score_pct))}%</strong>
              </>
            ) : '未发现带来源的匹配机会。'}
            {matchResult.provider_used && <span className="yc-dash-provider-tag">AI: {matchResult.provider_used}</span>}
          </p>

          {matchResult.ai_summary && (
            <div className="yc-dash-ai-summary">
              <div className="yc-dash-ai-summary-title">🤖 AI 智能建议</div>
              <p>{matchResult.ai_summary}</p>
            </div>
          )}

          {/* Scan results */}
          <div className="yc-dash-table">
            <table>
              <thead>
                <tr>
                  <th>#</th>
                  <th>政策名称</th>
                  <th>匹配度</th>
                  <th>管辖范围</th>
                  <th>缺失材料</th>
                </tr>
              </thead>
              <tbody>
                {matchResult.full.map((m, i) => (
                  <tr key={m.opportunity_id}>
                    <td>{i + 1}</td>
                    <td>{m.policy_title}</td>
                    <td><ScoreBadge score={m.score_pct} /></td>
                    <td>{m.jurisdiction || '全国'}</td>
                    <td className="yc-dash-missing">{(m.missing_materials || []).join('、')}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="yc-dash-unlocked">
            <p>扫描结果可直接查看；PDF 导出需通过服务端产品目录创建订单并完成支付。</p>
            <Link
              className="yc-dash-btn-primary"
              href={`/checkout?product=POLICY_REPORT&company=${companies[0].id}`}
            >
              查看 PDF 导出价格
            </Link>
          </div>
        </div>
      )}

      {/* Data Flywheel */}
      {stats && (
        <div className="yc-dash-section">
          <h2>数据飞轮 — 使用统计（近7天）</h2>
          <div className="yc-dash-flywheel">
            <div className="yc-dash-flywheel-item">
              <div className="yc-dash-flywheel-value">{stats.reports_generated}</div>
              <div className="yc-dash-flywheel-label">报告生成</div>
            </div>
            <div className="yc-dash-flywheel-arrow">→</div>
            <div className="yc-dash-flywheel-item">
              <div className="yc-dash-flywheel-value">{stats.payments}</div>
              <div className="yc-dash-flywheel-label">付费转化</div>
            </div>
            <div className="yc-dash-flywheel-arrow">→</div>
            <div className="yc-dash-flywheel-item">
              <div className="yc-dash-flywheel-value">{stats.downloads}</div>
              <div className="yc-dash-flywheel-label">报告下载</div>
            </div>
            <div className="yc-dash-flywheel-arrow">→</div>
            <div className="yc-dash-flywheel-item">
              <div className="yc-dash-flywheel-value">{Object.values(stats.provider_usage || {}).reduce((a: number, b: any) => a + b, 0)}</div>
              <div className="yc-dash-flywheel-label">模型调用</div>
            </div>
          </div>
          {stats.provider_usage && Object.keys(stats.provider_usage).length > 0 && (
            <div className="yc-dash-provider-usage">
              模型使用分布：{Object.entries(stats.provider_usage).map(([k, v]) => `${k}: ${v}`).join(' | ')}
            </div>
          )}
        </div>
      )}

      {/* Orders */}
      <div className="yc-dash-section">
        <h2>订单记录</h2>
        {orders.length === 0 ? (
          <p className="yc-dash-empty">暂无订单</p>
        ) : (
          <div className="yc-dash-table">
            <table>
              <thead>
                <tr><th>产品</th><th>金额</th><th>状态</th><th>时间</th></tr>
              </thead>
              <tbody>
                {orders.map(o => (
                  <tr key={o.id}>
                    <td>{o.product_code === 'policy_match_report' ? '政策匹配报告' : o.product_code}</td>
                    <td>¥{o.amount.toLocaleString()}</td>
                    <td><StatusBadge status={o.status} /></td>
                    <td>{new Date(o.created_at).toLocaleDateString('zh-CN')}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      <style jsx>{`
        .yc-dashboard { max-width:1200px; margin:0 auto; }
        .yc-dash-metrics { display:grid; grid-template-columns:repeat(4,1fr); gap:16px; margin-bottom:32px; }
        .yc-dash-metric-card { background:#fff; border:1px solid #e2e8f0; border-radius:16px; padding:24px; text-align:center; }
        .yc-dash-metric-value { font-size:32px; font-weight:700; color:#0d1b2a; margin-bottom:4px; }
        .yc-dash-metric-label { font-size:13px; color:#64748b; }
        .yc-dash-section { background:#fff; border:1px solid #e2e8f0; border-radius:16px; padding:28px; margin-bottom:24px; }
        .yc-dash-section h2 { font-size:18px; font-weight:600; color:#0d1b2a; margin:0 0 20px; }
        .yc-dash-btn-primary { padding:12px 24px; background:#126a9a; color:#fff; border:none; border-radius:10px; font-size:14px; font-weight:600; cursor:pointer; }
        .yc-dash-btn-primary:hover { background:#0d567e; }
        .yc-dash-btn-primary:disabled { opacity:.6; cursor:not-allowed; }
        .yc-dash-company-form { display:flex; flex-direction:column; gap:16px; }
        .yc-dash-form-row { display:flex; flex-direction:column; gap:6px; }
        .yc-dash-form-row label { font-size:13px; font-weight:500; color:#374151; }
        .yc-dash-form-row input, .yc-dash-form-row select { padding:10px 14px; border:1px solid #e2e8f0; border-radius:8px; font-size:14px; outline:none; }
        .yc-dash-form-row input:focus, .yc-dash-form-row select:focus { border-color:#0ea5e9; }
        .yc-dash-form-actions { display:flex; gap:12px; }
        .yc-dash-form-actions button { padding:10px 20px; border-radius:8px; font-size:14px; cursor:pointer; }
        .yc-dash-form-actions button[type="submit"] { background:#0ea5e9; color:#fff; border:none; }
        .yc-dash-form-actions button[type="button"] { background:#fff; color:#64748b; border:1px solid #e2e8f0; }
        .yc-dash-company-info { display:flex; justify-content:space-between; align-items:center; }
        .yc-dash-company-card { }
        .yc-dash-company-name { font-size:18px; font-weight:600; color:#0d1b2a; margin-bottom:4px; }
        .yc-dash-company-meta { display:flex; gap:12px; font-size:13px; color:#64748b; }
        .yc-dash-match-summary { font-size:14px; color:#374151; margin-bottom:20px; }
        .yc-dash-match-summary strong { color:#0d1b2a; }
        .yc-dash-table table { width:100%; border-collapse:collapse; }
        .yc-dash-table th { text-align:left; padding:10px 12px; font-size:12px; font-weight:500; color:#64748b; border-bottom:1px solid #e2e8f0; }
        .yc-dash-table td { padding:12px; font-size:14px; color:#0d1b2a; border-bottom:1px solid #f1f5f9; }
        .yc-dash-missing { font-size:12px; color:#64748b; }
        .yc-dash-paywall { margin-top:24px; }
        .yc-dash-paywall-blur { filter:blur(4px); opacity:.5; pointer-events:none; padding:16px; border:1px solid #e2e8f0; border-radius:10px; margin-bottom:20px; }
        .yc-dash-blur-row { padding:10px 0; border-bottom:1px solid #f1f5f9; font-size:13px; color:#374151; }
        .yc-dash-paywall-cta { text-align:center; padding:20px; background:#f0f9ff; border-radius:12px; }
        .yc-dash-paywall-cta p { font-size:14px; color:#374151; margin-bottom:16px; }
        .yc-dash-unlocked { margin-top:20px; }
        .yc-dash-empty { color:#94a3b8; font-size:14px; text-align:center; padding:24px; }
        .yc-dash-company-actions { display:flex; gap:12px; align-items:center; }
        .yc-dash-model-select { padding:10px 14px; border:1px solid #e2e8f0; border-radius:8px; font-size:13px; outline:none; background:#fff; color:#374151; }
        .yc-dash-model-select:focus { border-color:#0ea5e9; }
        .yc-dash-provider-tag { display:inline-block; margin-left:12px; padding:2px 8px; background:#eff6ff; color:#1d4ed8; border-radius:6px; font-size:11px; font-weight:500; }
        .yc-dash-ai-summary { background:linear-gradient(135deg, #f0f9ff, #eff6ff); border:1px solid #bae6fd; border-radius:12px; padding:16px 20px; margin-bottom:20px; }
        .yc-dash-ai-summary-title { font-size:13px; font-weight:600; color:#0369a1; margin-bottom:8px; }
        .yc-dash-ai-summary p { font-size:14px; color:#1e293b; line-height:1.6; margin:0; }
        .yc-dash-flywheel { display:flex; align-items:center; justify-content:center; gap:8px; padding:16px 0; }
        .yc-dash-flywheel-item { text-align:center; padding:16px 24px; background:#f8fafc; border-radius:12px; min-width:100px; }
        .yc-dash-flywheel-value { font-size:28px; font-weight:700; color:#0ea5e9; }
        .yc-dash-flywheel-label { font-size:12px; color:#64748b; margin-top:4px; }
        .yc-dash-flywheel-arrow { font-size:20px; color:#94a3b8; }
        .yc-dash-provider-usage { text-align:center; font-size:12px; color:#64748b; margin-top:8px; }
        @media (max-width:768px) {
          .yc-dash-metrics { grid-template-columns:repeat(2,1fr); }
          .yc-dash-company-info { flex-direction:column; align-items:flex-start; gap:16px; }
          .yc-dash-company-actions { width:100%; flex-direction:column; align-items:stretch; }
          .yc-dash-flywheel { display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); }
          .yc-dash-flywheel-item { min-width:0; padding:14px 8px; }
          .yc-dash-flywheel-arrow { display:none; }
        }
      `}</style>
      </div>
    </AppShell>
  );
}
