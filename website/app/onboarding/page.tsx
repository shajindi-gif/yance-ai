'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import api from '@/lib/api';
import { safeReturnPath } from '@/lib/return-path';
import pageStyles from './page.module.css';

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
    <div className={pageStyles.section}>
      <div className={pageStyles.section2}>
        {/* Header */}
        <div className={pageStyles.section3}>
          <img src="/logo.png" alt="衍策引擎AI" className={pageStyles.section4} />
          <h1 className={pageStyles.heading}>完善企业画像</h1>
          <p className={pageStyles.description}>填写更多信息，获取更精准的政策匹配</p>
        </div>

        {/* Progress */}
        <div className={pageStyles.layout}>
          {STEPS.map(s => (
            <div key={s.id} className={pageStyles.inlineSection} style={{ background: s.id <= step ? 'var(--accent)' : 'rgba(255,255,255,0.15)' }} />
          ))}
        </div>

        {/* Step info */}
        <div className={pageStyles.section5}>
          <span className={pageStyles.label}>步骤 {step}/8</span>
          <h2 className={pageStyles.heading2}>{STEPS[step - 1].title}</h2>
          <p className={pageStyles.description}>{STEPS[step - 1].desc}</p>
        </div>

        {/* Form card */}
        <div className={pageStyles.section6}>
          {/* Step 1: Company name */}
          {step === 1 && (
            <div>
              <label className={pageStyles.layout2}>企业名称 *</label>
              <input
                type="text" value={data.name} onChange={e => updateField('name', e.target.value)}
                placeholder="如：上海星辰智能科技有限公司"
                className={pageStyles.section7}
              />
            </div>
          )}

          {/* Step 2: Location */}
          {step === 2 && (
            <div className={pageStyles.layout3}>
              <div>
                <label className={pageStyles.layout2}>省份</label>
                <input type="text" value={data.province} onChange={e => updateField('province', e.target.value)}
                  placeholder="如：上海市" className={pageStyles.section8} />
              </div>
              <div>
                <label className={pageStyles.layout2}>城市</label>
                <input type="text" value={data.city} onChange={e => updateField('city', e.target.value)}
                  placeholder="如：上海市" className={pageStyles.section8} />
              </div>
              <div>
                <label className={pageStyles.layout2}>区县（可选）</label>
                <input type="text" value={data.district} onChange={e => updateField('district', e.target.value)}
                  placeholder="如：徐汇区" className={pageStyles.section8} />
              </div>
            </div>
          )}

          {/* Step 3: Industry */}
          {step === 3 && (
            <div className={pageStyles.layout4}>
              {INDUSTRIES.map(ind => (
                <button key={ind} onClick={() => updateField('industry', ind)}
                  className={pageStyles.inlineAction} style={{ border: data.industry === ind ? '2px solid #126a9a' : '1px solid #e2e8f0', background: data.industry === ind ? '#f0f9ff' : 'var(--surface)', color: data.industry === ind ? '#0369a1' : 'var(--ink)' }}>
                  {ind}
                </button>
              ))}
            </div>
          )}

          {/* Step 4: Scale */}
          {step === 4 && (
            <div className={pageStyles.layout5}>
              {SCALES.map(s => (
                <button key={s} onClick={() => updateField('scale', s)}
                  className={pageStyles.inlineAction2} style={{ border: data.scale === s ? '2px solid #126a9a' : '1px solid #e2e8f0', background: data.scale === s ? '#f0f9ff' : 'var(--surface)', color: data.scale === s ? '#0369a1' : 'var(--ink)' }}>
                  {s}
                </button>
              ))}
            </div>
          )}

          {/* Step 5: Age */}
          {step === 5 && (
            <div className={pageStyles.layout4}>
              {AGES.map(a => (
                <button key={a} onClick={() => updateField('founded_year', a)}
                  className={pageStyles.inlineAction} style={{ border: data.founded_year === a ? '2px solid #126a9a' : '1px solid #e2e8f0', background: data.founded_year === a ? '#f0f9ff' : 'var(--surface)', color: data.founded_year === a ? '#0369a1' : 'var(--ink)' }}>
                  {a}
                </button>
              ))}
            </div>
          )}

          {/* Step 6: Qualifications */}
          {step === 6 && (
            <div>
              <p className={pageStyles.description2}>选择所有已获得的资质（可多选）：</p>
              <div className={pageStyles.layout4}>
                {QUALIFICATIONS.map(q => (
                  <button key={q} onClick={() => toggleArray('qualifications', q)}
                    className={pageStyles.inlineAction} style={{ border: data.qualifications.includes(q) ? '2px solid #126a9a' : '1px solid #e2e8f0', background: data.qualifications.includes(q) ? '#f0f9ff' : 'var(--surface)', color: data.qualifications.includes(q) ? '#0369a1' : 'var(--ink)' }}>
                    {q}
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Step 7: R&D */}
          {step === 7 && (
            <div className={pageStyles.layout3}>
              <div>
                <label className={pageStyles.layout2}>知识产权数量（专利+软著）</label>
                <input type="text" value={data.ip_count} onChange={e => updateField('ip_count', e.target.value)}
                  placeholder="如：15" className={pageStyles.section8} />
              </div>
              <div>
                <label className={pageStyles.layout2}>研发费用占营收比例 (%)</label>
                <input type="text" value={data.rd_expense_ratio} onChange={e => updateField('rd_expense_ratio', e.target.value)}
                  placeholder="如：8" className={pageStyles.section8} />
              </div>
              <div>
                <label className={pageStyles.layout2}>研发人员占比 (%)</label>
                <input type="text" value={data.rd_ratio} onChange={e => updateField('rd_ratio', e.target.value)}
                  placeholder="如：30" className={pageStyles.section8} />
              </div>
            </div>
          )}

          {/* Step 8: Policy needs */}
          {step === 8 && (
            <div>
              <p className={pageStyles.description2}>选择您最关注的政策方向（可多选）：</p>
              <div className={pageStyles.layout4}>
                {POLICY_NEEDS.map(n => (
                  <button key={n} onClick={() => toggleArray('policy_needs', n)}
                    className={pageStyles.inlineAction} style={{ border: data.policy_needs.includes(n) ? '2px solid #f97316' : '1px solid #e2e8f0', background: data.policy_needs.includes(n) ? 'var(--accent-soft)' : 'var(--surface)', color: data.policy_needs.includes(n) ? 'var(--teal-dark)' : 'var(--ink)' }}>
                    {n}
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Navigation */}
          <div className={pageStyles.layout6}>
            {step > 1 ? (
              <button onClick={handleBack} className={pageStyles.action}>上一步</button>
            ) : <div />}
            {step < 8 ? (
              <button onClick={handleNext} disabled={!canNext()}
                className={pageStyles.inlineAction3} style={{ background: canNext() ? 'var(--accent)' : '#94a3b8', cursor: canNext() ? 'pointer' : 'not-allowed' }}>
                下一步
              </button>
            ) : (
              <button onClick={handleSubmit} disabled={loading}
                className={pageStyles.inlineAction4} style={{ background: loading ? '#94a3b8' : 'var(--accent)', cursor: loading ? 'not-allowed' : 'pointer' }}>
                {loading ? '保存中...' : '开始政策匹配 →'}
              </button>
            )}
          </div>
          {error ? (
            <div role="alert" className={pageStyles.section9}>
              {error}
            </div>
          ) : null}
        </div>

        {/* Skip */}
        <div className={pageStyles.section10}>
          <button onClick={() => router.push(returnPath)} className={pageStyles.action2}>
            跳过，稍后完善
          </button>
        </div>
      </div>
    </div>
  );
}
