'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import api, { API_BASE } from '@/lib/api';

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
      <section className="page-banner" style={{ background: 'linear-gradient(135deg, #0d1b2a 0%, #1b2d44 60%, #0d1b2a 100%)' }}>
        <div className="container">
          <span className="badge" style={{ background: 'rgba(14,165,233,0.2)', color: '#0ea5e9', marginBottom: '16px' }}>政策知识库</span>
          <h1>全国政策知识库</h1>
          <p>登录后查看数据库中带来源的政策记录，并获取与你企业匹配的政策机会。</p>
        </div>
      </section>

      <section className="section">
        <div className="container">
          {/* Filters */}
          <div style={{ display: 'flex', gap: '8px', marginBottom: '32px', flexWrap: 'wrap' }}>
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
                style={{
                  padding: '8px 20px', borderRadius: '9999px', fontSize: '13px', fontWeight: 500, cursor: 'pointer',
                  border: filter === f.key ? '2px solid #0ea5e9' : '1px solid #e2e8f0',
                  background: filter === f.key ? '#f0f9ff' : '#fff',
                  color: filter === f.key ? '#0369a1' : '#64748b',
                }}
              >
                {f.label}
              </button>
            ))}
          </div>

          {loading ? (
            <div style={{ textAlign: 'center', padding: '60px', color: '#64748b' }}>加载政策库...</div>
          ) : filtered.length === 0 ? (
            <div style={{ textAlign: 'center', padding: '60px', color: '#64748b' }}>
              暂无可展示的真实政策数据。登录后扫描企业机会，系统不会用静态示例冒充最新政策。
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
              {filtered.map((p) => (
                <div key={p.id ?? `${p.policy_title}-${p.jurisdiction}`} style={{ background: '#fff', borderRadius: '12px', border: '1px solid #e2e8f0', padding: '24px', transition: 'box-shadow 0.2s' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'start', marginBottom: '12px' }}>
                    <div style={{ flex: 1 }}>
                      <div style={{ display: 'flex', gap: '8px', alignItems: 'center', marginBottom: '8px' }}>
                        <span style={{ padding: '3px 10px', borderRadius: '6px', fontSize: '11px', fontWeight: 600, color: LEVEL_COLORS[p.level] || '#64748b', background: (LEVEL_COLORS[p.level] || '#64748b') + '15' }}>
                          {LEVEL_LABELS[p.level] || p.level}
                        </span>
                        <span style={{ fontSize: '12px', color: '#94a3b8' }}>{p.jurisdiction}</span>
                      </div>
                      <h3 style={{ fontSize: '16px', fontWeight: 600, color: '#0d1b2a', margin: 0, lineHeight: 1.5 }}>{p.policy_title}</h3>
                    </div>
                    <div style={{ textAlign: 'right', flexShrink: 0, marginLeft: '16px' }}>
                      <div style={{ fontSize: '18px', fontWeight: 700, color: '#f97316' }}>{p.support_amount}</div>
                      <div style={{ fontSize: '11px', color: '#94a3b8', marginTop: '2px' }}>{p.support_type}</div>
                    </div>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <div style={{ fontSize: '12px', color: '#64748b' }}>
                      {p.issuing_authority}
                      {p.deadline && <span style={{ marginLeft: '16px', color: '#dc2626' }}>截止：{new Date(p.deadline).toLocaleDateString('zh-CN')}</span>}
                    </div>
                    <Link href="/login?register=1" style={{ fontSize: '13px', color: '#0ea5e9', textDecoration: 'none', fontWeight: 500 }}>
                      注册查看匹配度 →
                    </Link>
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* CTA */}
          <div style={{ textAlign: 'center', marginTop: '48px', padding: '40px', background: 'linear-gradient(135deg, #f0f9ff, #eff6ff)', borderRadius: '16px' }}>
            <h2 style={{ fontSize: '20px', fontWeight: 700, color: '#0d1b2a', marginBottom: '8px' }}>找到适合你企业的政策</h2>
            <p style={{ fontSize: '14px', color: '#64748b', marginBottom: '20px' }}>注册后基于企业画像执行初筛；资格与金额须以带来源的政策条款和人工复核为准。</p>
            <Link href="/login?register=1" style={{ display: 'inline-block', padding: '12px 32px', background: '#f97316', color: '#fff', borderRadius: '10px', textDecoration: 'none', fontSize: '15px', fontWeight: 600 }}>免费政策匹配</Link>
          </div>
        </div>
      </section>
    </>
  );
}
