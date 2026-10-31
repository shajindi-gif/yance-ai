'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import api from '@/lib/api';
import { safeReturnPath } from '@/lib/return-path';

const STEPS = [
  { id: 1, title: '企业名称', desc: '您的企业全称' },
  { id: 2, title: '所在地', desc: '企业注册地' },
  { id: 3, title: '行业', desc: '企业所属行业' },
  { id: 4, title: '企业规模', desc: '员工人数规模' },
  { id: 5, title: '成立时间', desc: '企业成立年限' },
  { id: 6, title: '已有资质', desc: '已获得的认定资质' },
  { id: 7, title: '研发情况', desc: '知识产权与研发投入' },
  { id: 8, title: '政策需求', desc: '重点关注的政策方向' },
];

const INDUSTRIES = ['人工智能', '软件与信息技术', '集成电路/半导体', '生物医药', '新材料', '高端装备制造', '新能源/储能', '航空航天/低空经济', '数字经济', '其他'];
const SCALES = ['微型（<20人）', '小型（20-100人）', '中型（100-500人）', '大型（500+人）'];
const AGES = ['<1年', '1-3年', '3-5年', '5-10年', '10年以上'];
const QUALIFICATIONS = ['高新技术企业', '专精特新', '科技型中小企业', '创新型中小企业', '独角兽', '瞪羚企业'];
const POLICY_NEEDS = ['高新技术企业认定', '专精特新认定', '科技型中小企业评价', '研发费用加计扣除', '人才政策', '房租补贴', '算力券/模型券', '融资贷款贴息', '科技项目', '产业园区入驻'];

export default function OnboardingPage() {
  const router = useRouter();
  const [returnPath, setReturnPath] = useState('/dashboard');
  useEffect(() => { setReturnPath(safeReturnPath(new URLSearchParams(window.location.search).get('next'))); }, []);
  const [step, setStep] = useState(1);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [companyId, setCompanyId] = useState<string | null>(null);
  const [data, setData] = useState({
    name: '',
    province: '',
    city: '',
    district: '',
    industry: '',
    scale: '',
    founded_year: '',
    qualifications: [] as string[],
    ip_count: '',
    rd_expense_ratio: '',
    rd_ratio: '',
    policy_needs: [] as string[],
  });

  useEffect(() => {
    if (!api.isAuthenticated()) { router.push('/login?register=1'); return; }
    // Load existing company if any
    api.getCompanies().then(companies => {
      if (companies.length > 0) {
        setCompanyId(companies[0].id);
        const meta = companies[0].metadata_json || {};
        setData(prev => ({
          ...prev,
          name: companies[0].name || '',
          province: companies[0].province || '',
          city: companies[0].city || '',
          district: String(meta.district || ''),
          industry: companies[0].industry || '',
          scale: String(meta.scale || ''),
          founded_year: String(meta.founded_year || ''),
          qualifications: Array.isArray(meta.qualifications) ? meta.qualifications as string[] : [],
          ip_count: String(meta.ip_count || ''),
          rd_expense_ratio: String(meta.rd_expense_ratio || ''),
          rd_ratio: String(meta.rd_ratio || ''),
          policy_needs: Array.isArray(meta.policy_needs) ? meta.policy_needs as string[] : [],
        }));
      }
    }).catch(() => {});
  }, [router]);

  const updateField = (field: string, value: string) => {
    setData(prev => ({ ...prev, [field]: value }));
  };

  const toggleArray = (field: 'qualifications' | 'policy_needs', item: string) => {
    setData(prev => {
      const arr = prev[field];
      return { ...prev, [field]: arr.includes(item) ? arr.filter(x => x !== item) : [...arr, item] };
    });
  };

  const handleNext = () => {
    if (step < 8) setStep(step + 1);
  };

  const handleBack = () => {
    if (step > 1) setStep(step - 1);
  };

  const handleSubmit = async () => {
    setLoading(true);
    try {
      const payload = {
        name: data.name || '未命名企业',
        industry: data.industry || undefined,
        province: data.province || undefined,
        city: data.city || undefined,
        metadata_json: {
          district: data.district,
          scale: data.scale,
          founded_year: data.founded_year,
          qualifications: data.qualifications,
          ip_count: data.ip_count,
          rd_expense_ratio: data.rd_expense_ratio,
          rd_ratio: data.rd_ratio,
          policy_needs: data.policy_needs,
        },
      };

      if (companyId) {
        await api.updateCompany(companyId, payload);
      } else {
        const company = await api.createCompany(payload);
        setCompanyId(company.id);
      }

      router.push(returnPath === '/dashboard' ? '/dashboard?onboarded=1' : returnPath);
    } catch (err) {
      console.error('Onboarding failed:', err);
      setError(err instanceof Error ? err.message : '保存失败，请重试或跳过稍后完善');
    } finally {
      setLoading(false);
    }
  };

  const canNext = () => {
    if (step === 1) return data.name.trim().length >= 2;
    return true; // Other steps are optional
  };

  return (
    <div style={{ minHeight: '100vh', background: 'linear-gradient(135deg, #0d1b2a 0%, #1b2d45 50%, #142842 100%)', padding: '40px 20px' }}>
      <div style={{ maxWidth: '640px', margin: '0 auto' }}>
        {/* Header */}
        <div style={{ textAlign: 'center', marginBottom: '32px' }}>
          <img src="/logo.png" alt="衍策引擎AI" style={{ width: '48px', height: '48px', marginBottom: '12px' }} />
          <h1 style={{ fontSize: '22px', color: '#fff', fontWeight: 700, margin: '0 0 8px' }}>完善企业画像</h1>
          <p style={{ fontSize: '13px', color: '#94a3b8', margin: 0 }}>填写更多信息，获取更精准的政策匹配</p>
        </div>

        {/* Progress */}
        <div style={{ display: 'flex', gap: '4px', marginBottom: '32px' }}>
          {STEPS.map(s => (
            <div key={s.id} style={{ flex: 1, height: '4px', borderRadius: '2px', background: s.id <= step ? '#126a9a' : 'rgba(255,255,255,0.15)', transition: 'all 0.3s' }} />
          ))}
        </div>

        {/* Step info */}
        <div style={{ marginBottom: '24px' }}>
          <span style={{ fontSize: '12px', color: 'var(--teal)', fontWeight: 600 }}>步骤 {step}/8</span>
          <h2 style={{ fontSize: '20px', color: '#fff', fontWeight: 700, margin: '8px 0 4px' }}>{STEPS[step - 1].title}</h2>
          <p style={{ fontSize: '13px', color: '#94a3b8', margin: 0 }}>{STEPS[step - 1].desc}</p>
        </div>

        {/* Form card */}
        <div style={{ background: 'rgba(255,255,255,0.98)', borderRadius: '16px', padding: '32px', boxShadow: '0 20px 60px rgba(0,0,0,0.3)' }}>
          {/* Step 1: Company name */}
          {step === 1 && (
            <div>
              <label style={{ display: 'block', fontSize: '13px', fontWeight: 500, color: '#374151', marginBottom: '6px' }}>企业名称 *</label>
              <input
                type="text" value={data.name} onChange={e => updateField('name', e.target.value)}
                placeholder="如：上海星辰智能科技有限公司"
                style={{ width: '100%', padding: '12px 16px', border: '1px solid #e2e8f0', borderRadius: '10px', fontSize: '15px', outline: 'none' }}
              />
            </div>
          )}

          {/* Step 2: Location */}
          {step === 2 && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
              <div>
                <label style={{ display: 'block', fontSize: '13px', fontWeight: 500, color: '#374151', marginBottom: '6px' }}>省份</label>
                <input type="text" value={data.province} onChange={e => updateField('province', e.target.value)}
                  placeholder="如：上海市" style={{ width: '100%', padding: '11px 14px', border: '1px solid #e2e8f0', borderRadius: '8px', fontSize: '14px', outline: 'none' }} />
              </div>
              <div>
                <label style={{ display: 'block', fontSize: '13px', fontWeight: 500, color: '#374151', marginBottom: '6px' }}>城市</label>
                <input type="text" value={data.city} onChange={e => updateField('city', e.target.value)}
                  placeholder="如：上海市" style={{ width: '100%', padding: '11px 14px', border: '1px solid #e2e8f0', borderRadius: '8px', fontSize: '14px', outline: 'none' }} />
              </div>
              <div>
                <label style={{ display: 'block', fontSize: '13px', fontWeight: 500, color: '#374151', marginBottom: '6px' }}>区县（可选）</label>
                <input type="text" value={data.district} onChange={e => updateField('district', e.target.value)}
                  placeholder="如：徐汇区" style={{ width: '100%', padding: '11px 14px', border: '1px solid #e2e8f0', borderRadius: '8px', fontSize: '14px', outline: 'none' }} />
              </div>
            </div>
          )}

          {/* Step 3: Industry */}
          {step === 3 && (
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
              {INDUSTRIES.map(ind => (
                <button key={ind} onClick={() => updateField('industry', ind)}
                  style={{ padding: '10px 16px', borderRadius: '8px', border: data.industry === ind ? '2px solid #126a9a' : '1px solid #e2e8f0', background: data.industry === ind ? '#f0f9ff' : '#fff', color: data.industry === ind ? '#0369a1' : '#374151', fontSize: '13px', fontWeight: 500, cursor: 'pointer' }}>
                  {ind}
                </button>
              ))}
            </div>
          )}

          {/* Step 4: Scale */}
          {step === 4 && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
              {SCALES.map(s => (
                <button key={s} onClick={() => updateField('scale', s)}
                  style={{ padding: '14px 16px', borderRadius: '10px', border: data.scale === s ? '2px solid #126a9a' : '1px solid #e2e8f0', background: data.scale === s ? '#f0f9ff' : '#fff', color: data.scale === s ? '#0369a1' : '#374151', fontSize: '14px', fontWeight: 500, cursor: 'pointer', textAlign: 'left' }}>
                  {s}
                </button>
              ))}
            </div>
          )}

          {/* Step 5: Age */}
          {step === 5 && (
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
              {AGES.map(a => (
                <button key={a} onClick={() => updateField('founded_year', a)}
                  style={{ padding: '10px 16px', borderRadius: '8px', border: data.founded_year === a ? '2px solid #126a9a' : '1px solid #e2e8f0', background: data.founded_year === a ? '#f0f9ff' : '#fff', color: data.founded_year === a ? '#0369a1' : '#374151', fontSize: '13px', fontWeight: 500, cursor: 'pointer' }}>
                  {a}
                </button>
              ))}
            </div>
          )}

          {/* Step 6: Qualifications */}
          {step === 6 && (
            <div>
              <p style={{ fontSize: '12px', color: '#64748b', marginBottom: '12px' }}>选择所有已获得的资质（可多选）：</p>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
                {QUALIFICATIONS.map(q => (
                  <button key={q} onClick={() => toggleArray('qualifications', q)}
                    style={{ padding: '10px 16px', borderRadius: '8px', border: data.qualifications.includes(q) ? '2px solid #126a9a' : '1px solid #e2e8f0', background: data.qualifications.includes(q) ? '#f0f9ff' : '#fff', color: data.qualifications.includes(q) ? '#0369a1' : '#374151', fontSize: '13px', fontWeight: 500, cursor: 'pointer' }}>
                    {q}
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Step 7: R&D */}
          {step === 7 && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
              <div>
                <label style={{ display: 'block', fontSize: '13px', fontWeight: 500, color: '#374151', marginBottom: '6px' }}>知识产权数量（专利+软著）</label>
                <input type="text" value={data.ip_count} onChange={e => updateField('ip_count', e.target.value)}
                  placeholder="如：15" style={{ width: '100%', padding: '11px 14px', border: '1px solid #e2e8f0', borderRadius: '8px', fontSize: '14px', outline: 'none' }} />
              </div>
              <div>
                <label style={{ display: 'block', fontSize: '13px', fontWeight: 500, color: '#374151', marginBottom: '6px' }}>研发费用占营收比例 (%)</label>
                <input type="text" value={data.rd_expense_ratio} onChange={e => updateField('rd_expense_ratio', e.target.value)}
                  placeholder="如：8" style={{ width: '100%', padding: '11px 14px', border: '1px solid #e2e8f0', borderRadius: '8px', fontSize: '14px', outline: 'none' }} />
              </div>
              <div>
                <label style={{ display: 'block', fontSize: '13px', fontWeight: 500, color: '#374151', marginBottom: '6px' }}>研发人员占比 (%)</label>
                <input type="text" value={data.rd_ratio} onChange={e => updateField('rd_ratio', e.target.value)}
                  placeholder="如：30" style={{ width: '100%', padding: '11px 14px', border: '1px solid #e2e8f0', borderRadius: '8px', fontSize: '14px', outline: 'none' }} />
              </div>
            </div>
          )}

          {/* Step 8: Policy needs */}
          {step === 8 && (
            <div>
              <p style={{ fontSize: '12px', color: '#64748b', marginBottom: '12px' }}>选择您最关注的政策方向（可多选）：</p>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
                {POLICY_NEEDS.map(n => (
                  <button key={n} onClick={() => toggleArray('policy_needs', n)}
                    style={{ padding: '10px 16px', borderRadius: '8px', border: data.policy_needs.includes(n) ? '2px solid #f97316' : '1px solid #e2e8f0', background: data.policy_needs.includes(n) ? '#fff7ed' : '#fff', color: data.policy_needs.includes(n) ? '#c2410c' : '#374151', fontSize: '13px', fontWeight: 500, cursor: 'pointer' }}>
                    {n}
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Navigation */}
          <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: '32px' }}>
            {step > 1 ? (
              <button onClick={handleBack} style={{ padding: '11px 24px', borderRadius: '8px', border: '1px solid #e2e8f0', background: '#fff', color: '#64748b', fontSize: '14px', cursor: 'pointer' }}>上一步</button>
            ) : <div />}
            {step < 8 ? (
              <button onClick={handleNext} disabled={!canNext()}
                style={{ padding: '11px 24px', borderRadius: '8px', border: 'none', background: canNext() ? '#126a9a' : '#94a3b8', color: '#fff', fontSize: '14px', fontWeight: 500, cursor: canNext() ? 'pointer' : 'not-allowed' }}>
                下一步
              </button>
            ) : (
              <button onClick={handleSubmit} disabled={loading}
                style={{ padding: '11px 32px', borderRadius: '8px', border: 'none', background: loading ? '#94a3b8' : '#f97316', color: '#fff', fontSize: '14px', fontWeight: 600, cursor: loading ? 'not-allowed' : 'pointer' }}>
                {loading ? '保存中...' : '开始政策匹配 →'}
              </button>
            )}
          </div>
          {error ? (
            <div role="alert" style={{ marginTop: '16px', padding: '10px 14px', borderRadius: '8px', background: '#fef2f2', border: '1px solid #fecaca', color: '#dc2626', fontSize: '13px', lineHeight: 1.5 }}>
              {error}
            </div>
          ) : null}
        </div>

        {/* Skip */}
        <div style={{ textAlign: 'center', marginTop: '16px' }}>
          <button onClick={() => router.push(returnPath)} style={{ background: 'none', border: 'none', color: '#94a3b8', fontSize: '12px', cursor: 'pointer' }}>
            跳过，稍后完善
          </button>
        </div>
      </div>
    </div>
  );
}
