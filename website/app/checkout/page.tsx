'use client';

import { useEffect, useState, Suspense } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import api, { API_BASE } from '@/lib/api';

function CheckoutContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const productCode = searchParams.get('product') || 'POLICY_REPORT';
  const [product, setProduct] = useState<any>(null);
  const [companies, setCompanies] = useState<any[]>([]);
  const [selectedCompany, setSelectedCompany] = useState<string>('');
  const [paying, setPaying] = useState(false);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!api.isAuthenticated()) { router.push('/login?register=1'); return; }
    Promise.all([
      fetch(`${API_BASE}/products`).then(r => r.json()),
      api.getCompanies(),
    ]).then(([products, comps]) => {
      const p = products.find((x: any) => x.code === productCode);
      setProduct(p);
      setCompanies(comps);
      if (comps.length > 0) setSelectedCompany(comps[0].id);
      setLoading(false);
    }).catch(() => { setLoading(false); setError('加载失败'); });
  }, [router, productCode]);

  const handlePay = async () => {
    if (!selectedCompany || !product) return;
    setPaying(true);
    setError('');
    try {
      const result = await api.demoPay(product.code, selectedCompany);
      if (result.order_id) {
        router.push('/reports?purchased=1');
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : '支付失败，请重试');
    } finally {
      setPaying(false);
    }
  };

  if (loading) return (
    <div style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', background: '#f8fafc' }}>
      <div style={{ color: '#64748b' }}>加载中...</div>
    </div>
  );

  if (!product) return (
    <div style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', background: '#f8fafc' }}>
      <div style={{ textAlign: 'center' }}>
        <div style={{ fontSize: '48px', marginBottom: '16px' }}>❌</div>
        <h2 style={{ color: '#0d1b2a', marginBottom: '8px' }}>产品未找到</h2>
        <p style={{ color: '#64748b', marginBottom: '20px' }}>请从定价页选择产品</p>
        <button onClick={() => router.push('/pricing')} style={{ padding: '10px 24px', background: '#0ea5e9', color: '#fff', border: 'none', borderRadius: '8px', cursor: 'pointer' }}>返回定价页</button>
      </div>
    </div>
  );

  const price = product.promotional_price || product.price;

  return (
    <div style={{ minHeight: '100vh', background: '#f8fafc', paddingTop: '100px' }}>
      <div style={{ maxWidth: '560px', margin: '0 auto', padding: '32px 24px' }}>
        <button onClick={() => router.push('/pricing')} style={{ background: 'none', border: 'none', color: '#0ea5e9', fontSize: '13px', cursor: 'pointer', marginBottom: '24px', padding: 0 }}>← 返回定价页</button>

        <div style={{ background: '#fff', borderRadius: '16px', border: '1px solid #e2e8f0', overflow: 'hidden' }}>
          {/* Order summary */}
          <div style={{ padding: '32px' }}>
            <h1 style={{ fontSize: '20px', fontWeight: 700, color: '#0d1b2a', margin: '0 0 24px' }}>确认订单</h1>

            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'start', padding: '16px 0', borderBottom: '1px solid #f1f5f9' }}>
              <div>
                <div style={{ fontSize: '15px', fontWeight: 600, color: '#0d1b2a' }}>{product.name}</div>
                <div style={{ fontSize: '12px', color: '#64748b', marginTop: '4px' }}>{product.description}</div>
              </div>
              <div style={{ textAlign: 'right', flexShrink: 0, marginLeft: '16px' }}>
                {product.original_price && (
                  <div style={{ textDecoration: 'line-through', color: '#94a3b8', fontSize: '13px' }}>¥{product.original_price}</div>
                )}
                <div style={{ fontSize: '24px', fontWeight: 700, color: '#f97316' }}>¥{price}</div>
              </div>
            </div>

            {/* Company selection */}
            {companies.length > 0 && (
              <div style={{ padding: '16px 0' }}>
                <label style={{ display: 'block', fontSize: '13px', fontWeight: 500, color: '#374151', marginBottom: '8px' }}>选择企业</label>
                <select
                  value={selectedCompany}
                  onChange={e => setSelectedCompany(e.target.value)}
                  style={{ width: '100%', padding: '10px 14px', border: '1px solid #e2e8f0', borderRadius: '8px', fontSize: '14px', outline: 'none' }}
                >
                  {companies.map(c => (
                    <option key={c.id} value={c.id}>{c.name} ({c.industry || '—'} / {c.province || '—'})</option>
                  ))}
                </select>
              </div>
            )}

            {error && (
              <div style={{ padding: '10px 14px', background: '#fef2f2', border: '1px solid #fecaca', borderRadius: '8px', color: '#dc2626', fontSize: '13px', marginTop: '12px' }}>{error}</div>
            )}
          </div>

          {/* Payment section */}
          <div style={{ padding: '24px 32px', background: '#f8fafc', borderTop: '1px solid #e2e8f0' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
              <span style={{ fontSize: '14px', color: '#64748b' }}>应付金额</span>
              <span style={{ fontSize: '28px', fontWeight: 700, color: '#0d1b2a' }}>¥{price}</span>
            </div>
            <button
              onClick={handlePay}
              disabled={paying || !selectedCompany}
              style={{ width: '100%', padding: '14px', borderRadius: '10px', border: 'none', background: paying ? '#94a3b8' : '#f97316', color: '#fff', fontSize: '16px', fontWeight: 600, cursor: paying ? 'not-allowed' : 'pointer' }}
            >
              {paying ? '处理中...' : `确认支付 ¥${price}`}
            </button>
            <p style={{ fontSize: '11px', color: '#94a3b8', textAlign: 'center', marginTop: '12px' }}>
              当前为演示支付模式 · 接入支付宝/微信后将启用真实支付
            </p>
          </div>
        </div>

        {/* Trust signals */}
        <div style={{ display: 'flex', justifyContent: 'center', gap: '24px', marginTop: '24px', fontSize: '12px', color: '#94a3b8' }}>
          <span>🔒 数据加密</span>
          <span>📄 可开发票</span>
          <span>♾️ 永久下载</span>
        </div>
      </div>
    </div>
  );
}

export default function CheckoutPage() {
  return (
    <Suspense fallback={<div style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', background: '#f8fafc', color: '#64748b' }}>加载中...</div>}>
      <CheckoutContent />
    </Suspense>
  );
}
