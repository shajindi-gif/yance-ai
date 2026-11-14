'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import api, { API_BASE } from '@/lib/api';
import pageStyles from './page.module.css';

interface Policy {
  id?: string;
  policy_title: string;
  jurisdiction: string;
  level: string;
  province: string;
  support_amount: string;
  support_type: string;
  deadline: string | null;
  issuing_authority: string;
}

const LEVEL_LABELS: Record<string, string> = {
  national: '国家级',
  provincial: '省级',
  municipal: '市级',
  district: '区级',
};

const LEVEL_COLORS: Record<string, string> = {
  national: '#1e40af',
  provincial: '#7c3aed',
  municipal: '#0369a1',
  district: '#0d9488',
};

export default function PoliciesPage() {
  const [policies, setPolicies] = useState<Policy[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState<string>('all');

  useEffect(() => {
    let cancelled = false;
    const token = api.getToken();
    if (token) {
      api.getCompanies().then(companies => {
        if (companies.length > 0) {
          return fetch(`${API_BASE}/reports/match`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
            body: JSON.stringify({ company_id: companies[0].id }),
          }).then(r => r.json());
        }
        return null;
      }).then(data => {
        if (!cancelled && data?.full) {
          setPolicies(data.full);
        }
        if (!cancelled) setLoading(false);
      }).catch(() => {
        if (!cancelled) setLoading(false);
      });
    } else {
      // Public pages do not invent policy rows or amounts when no source-backed API is available.
      setPolicies([]);
      setLoading(false);
    }
    return () => {
      cancelled = true;
    };
  }, []);

  const filtered = filter === 'all' ? policies : policies.filter(p => p.level === filter);

  return (
    <>
      <section className={["page-banner", pageStyles.section].filter(Boolean).join(' ')} >
        <div className="container">
          <span className={["badge", pageStyles.label].filter(Boolean).join(' ')} >政策知识库</span>
          <h1>全国政策知识库</h1>
          <p>登录后查看数据库中带来源的政策记录，并获取与你企业匹配的政策机会。</p>
        </div>
      </section>

      <section className="section">
        <div className="container">
          {/* Filters */}
          <div className={pageStyles.layout}>
            {[
              { key: 'all', label: '全部' },
              { key: 'national', label: '国家级' },
              { key: 'provincial', label: '省级' },
              { key: 'municipal', label: '市级' },
              { key: 'district', label: '区级' },
            ].map(f => (
              <button
                key={f.key}
                onClick={() => setFilter(f.key)}
                className={pageStyles.inlineAction} style={{ border: filter === f.key ? '2px solid #126a9a' : '1px solid #e2e8f0', background: filter === f.key ? '#f0f9ff' : 'var(--surface)', color: filter === f.key ? '#0369a1' : '#64748b' }}
              >
                {f.label}
              </button>
            ))}
          </div>

          {loading ? (
            <div className={pageStyles.section2}>加载政策库...</div>
          ) : filtered.length === 0 ? (
            <div className={pageStyles.section2}>
              暂无可展示的真实政策数据。登录后扫描企业机会，系统不会用静态示例冒充最新政策。
            </div>
          ) : (
            <div className={pageStyles.layout2}>
              {filtered.map((p) => (
                <div key={p.id ?? `${p.policy_title}-${p.jurisdiction}`} className={pageStyles.section3}>
                  <div className={pageStyles.layout3}>
                    <div className={pageStyles.section4}>
                      <div className={pageStyles.layout4}>
                        <span className={pageStyles.inlineLabel} style={{ color: LEVEL_COLORS[p.level] || '#64748b', background: (LEVEL_COLORS[p.level] || '#64748b') + '15' }}>
                          {LEVEL_LABELS[p.level] || p.level}
                        </span>
                        <span className={pageStyles.label2}>{p.jurisdiction}</span>
                      </div>
                      <h3 className={pageStyles.heading}>{p.policy_title}</h3>
                    </div>
                    <div className={pageStyles.section5}>
                      <div className={pageStyles.section6}>{p.support_amount}</div>
                      <div className={pageStyles.section7}>{p.support_type}</div>
                    </div>
                  </div>
                  <div className={pageStyles.layout5}>
                    <div className={pageStyles.section8}>
                      {p.issuing_authority}
                      {p.deadline && <span className={pageStyles.label3}>截止：{new Date(p.deadline).toLocaleDateString('zh-CN')}</span>}
                    </div>
                    <Link href="/login?register=1" className={pageStyles.link}>
                      注册查看匹配度 →
                    </Link>
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* CTA */}
          <div className={pageStyles.section9}>
            <h2 className={pageStyles.heading2}>找到适合你企业的政策</h2>
            <p className={pageStyles.description}>注册后基于企业画像执行初筛；资格与金额须以带来源的政策条款和人工复核为准。</p>
            <Link href="/login?register=1" className={pageStyles.link2}>免费政策匹配</Link>
          </div>
        </div>
      </section>
    </>
  );
}
