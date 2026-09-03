'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import api, { Entitlement } from '@/lib/api';

const UPSSELL = [
  { code: 'POLICY_DIAGNOSIS', name: '单项目申报诊断', desc: '针对一项政策深度判断：能不能申报、缺什么、怎么准备' },
  { code: 'APPLICATION_PLAN', name: 'AI 申报方案包', desc: '申报策略、材料目录、实施计划、信息缺口分析' },
];

export default function ReportsPage() {
  const router = useRouter();
  const [entitlements, setEntitlements] = useState<Entitlement[]>([]);
  const [loading, setLoading] = useState(true);
  const [downloading, setDownloading] = useState<string | null>(null);

  useEffect(() => {
    if (!api.isAuthenticated()) { router.push('/login'); return; }
    let cancelled = false;
    api.getEntitlements()
      .then((ents) => {
        if (!cancelled) setEntitlements(ents);
      })
      .catch(() => {
        if (!cancelled) setEntitlements([]);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [router]);

  const handleDownload = async (companyId: string) => {
    setDownloading(companyId);
    try {
      const blob = await api.downloadReport(companyId);
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `政策机会分析报告_${new Date().toISOString().slice(0, 10)}.pdf`;
      a.click();
      URL.revokeObjectURL(url);
    } catch { /* ignore */ }
    setDownloading(null);
  };

  if (loading) return (
    <div style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', background: '#f8fafc' }}>
      <div style={{ color: '#64748b' }}>加载中...</div>
    </div>
  );

  const reportEnts = entitlements.filter(e => e.resource_type === 'report');

  return (
    <div style={{ minHeight: '100vh', background: '#f8fafc', paddingTop: '80px' }}>
      <div style={{ maxWidth: '960px', margin: '0 auto', padding: '32px 24px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px' }}>
          <div>
            <h1 style={{ fontSize: '24px', fontWeight: 700, color: '#0d1b2a', margin: '0 0 4px' }}>我的报告</h1>
            <p style={{ fontSize: '13px', color: '#64748b', margin: 0 }}>已购买的报告可随时查看和下载</p>
          </div>
          <Link href="/dashboard" style={{ fontSize: '13px', color: '#0ea5e9', textDecoration: 'none' }}>← 返回工作台</Link>
        </div>

        {reportEnts.length === 0 ? (
          <div style={{ background: '#fff', borderRadius: '16px', padding: '60px 32px', textAlign: 'center', border: '1px solid #e2e8f0' }}>
            <div style={{ fontSize: '48px', marginBottom: '16px' }}>📊</div>
            <h3 style={{ fontSize: '16px', color: '#0d1b2a', marginBottom: '8px' }}>暂无报告</h3>
            <p style={{ fontSize: '13px', color: '#64748b', marginBottom: '20px' }}>完成政策匹配后可购买体检报告</p>
            <Link href="/dashboard" style={{ display: 'inline-block', padding: '10px 24px', background: '#0ea5e9', color: '#fff', borderRadius: '8px', textDecoration: 'none', fontSize: '14px' }}>开始匹配</Link>
          </div>
        ) : (
          <>
            {/* Reports list */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '12px', marginBottom: '32px' }}>
              {reportEnts.map(ent => (
                <div key={ent.id} style={{ background: '#fff', borderRadius: '12px', border: '1px solid #e2e8f0', padding: '20px 24px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <div>
                    <div style={{ fontSize: '15px', fontWeight: 600, color: '#0d1b2a', marginBottom: '4px' }}>{ent.product_name}</div>
                    <div style={{ fontSize: '12px', color: '#64748b' }}>购买于 {new Date(ent.created_at).toLocaleDateString('zh-CN')} · 可无限次下载</div>
                  </div>
                  <button
                    onClick={() => ent.resource_id && handleDownload(ent.resource_id)}
                    disabled={!ent.resource_id || downloading === ent.resource_id}
                    style={{ padding: '9px 20px', borderRadius: '8px', border: 'none', background: downloading === ent.resource_id ? '#94a3b8' : '#0ea5e9', color: '#fff', fontSize: '13px', fontWeight: 500, cursor: downloading === ent.resource_id ? 'not-allowed' : 'pointer' }}
                  >
                    {downloading === ent.resource_id ? '下载中...' : '下载 PDF'}
                  </button>
                </div>
              ))}
            </div>

            {/* Upsell */}
            <div style={{ marginBottom: '24px' }}>
              <h2 style={{ fontSize: '18px', fontWeight: 700, color: '#0d1b2a', marginBottom: '4px' }}>进一步服务</h2>
              <p style={{ fontSize: '13px', color: '#64748b', marginBottom: '16px' }}>体检报告发现了政策机会，以下服务帮你深入准备</p>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
                {UPSSELL.map(item => (
                  <div key={item.code} style={{ background: '#fff', borderRadius: '12px', border: '1px solid #e2e8f0', padding: '24px' }}>
                    <div style={{ fontSize: '15px', fontWeight: 600, color: '#0d1b2a', marginBottom: '8px' }}>{item.name}</div>
                    <div style={{ fontSize: '12px', color: '#64748b', marginBottom: '16px', lineHeight: 1.6 }}>{item.desc}</div>
                    <button
                      disabled
                      style={{ width: '100%', padding: '10px', borderRadius: '8px', border: 'none', background: '#cbd5e1', color: '#475569', fontSize: '13px', fontWeight: 600 }}
                    >
                      从具体机会工作区创建（建设中）
                    </button>
                  </div>
                ))}
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
