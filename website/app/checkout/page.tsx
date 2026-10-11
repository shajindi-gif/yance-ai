'use client';

import { useCallback, useEffect, useRef, useState, Suspense } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import api, { Company, ProductCatalogItem } from '@/lib/api';

type Provider = 'alipay' | 'wechat';

function CheckoutContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const productCode = searchParams.get('product') || 'POLICY_REPORT';
  const requestedCompany = searchParams.get('company') || '';
  const [product, setProduct] = useState<ProductCatalogItem | null>(null);
  const [companies, setCompanies] = useState<Company[]>([]);
  const [selectedCompany, setSelectedCompany] = useState<string>('');
  const [paying, setPaying] = useState(false);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);
  const [provider, setProvider] = useState<Provider>('alipay');
  const [qrCodeUrl, setQrCodeUrl] = useState('');
  const [pendingOrder, setPendingOrder] = useState('');
  const [paid, setPaid] = useState(false);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const [countdown, setCountdown] = useState(600);

  const stopTimers = useCallback(() => {
    if (pollRef.current) { clearInterval(pollRef.current); pollRef.current = null; }
    if (timerRef.current) { clearInterval(timerRef.current); timerRef.current = null; }
  }, []);

  const startPolling = useCallback((orderId: string) => {
    stopTimers();
    setCountdown(600);
    pollRef.current = setInterval(async () => {
      try {
        const result = await api.queryWechatOrder(orderId);
        if (result.status === 'paid' || result.trade_state === 'SUCCESS') {
          stopTimers();
          setPaid(true);
          window.setTimeout(() => router.push(`/success?order=${orderId}`), 800);
        }
      } catch {
        /* transient polling errors are ignored; next tick retries */
      }
    }, 3000);
    timerRef.current = setInterval(() => {
      setCountdown((seconds) => {
        if (seconds <= 1) {
          stopTimers();
          return 0;
        }
        return seconds - 1;
      });
    }, 1000);
  }, [router, stopTimers]);

  useEffect(() => () => stopTimers(), [stopTimers]);

  useEffect(() => {
    if (!api.isAuthenticated()) { router.push('/login?register=1'); return; }
    let cancelled = false;
    Promise.all([
      api.getProducts(),
      api.getCompanies(),
    ]).then(([products, comps]) => {
      if (cancelled) return;
      const p = products.find((item) => item.code === productCode) ?? null;
      setProduct(p);
      setCompanies(comps);
      if (comps.length > 0) {
        const selected = comps.some((company) => company.id === requestedCompany)
          ? requestedCompany
          : comps[0].id;
        setSelectedCompany(selected);
      }
      setLoading(false);
    }).catch(() => {
      if (!cancelled) {
        setLoading(false);
        setError('加载失败');
      }
    });
    return () => {
      cancelled = true;
    };
  }, [requestedCompany, router, productCode]);

  const handlePay = async () => {
    if (!selectedCompany || !product) return;
    setPaying(true);
    setError('');
    try {
      if (product.entitlement_type !== 'report') {
        throw new Error('该产品需要从具体机会或申报工作区创建订单');
      }
      const order = await api.createOrder({
        product_code: product.code,
        resource_id: selectedCompany,
      });
      setPendingOrder(order.id);
      if (provider === 'alipay') {
        const checkout = await api.createCheckout(order.id);
        window.location.assign(checkout.url);
        return;
      }
      const wechat = await api.createWechatNativeOrder(order.id);
      setQrCodeUrl(wechat.code_url);
      startPolling(order.id);
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
        <button onClick={() => router.push('/pricing')} style={{ padding: '10px 24px', background: '#126a9a', color: '#fff', border: 'none', borderRadius: '8px', cursor: 'pointer' }}>返回定价页</button>
      </div>
    </div>
  );

  const price = product.promotional_price ?? product.price;

  return (
    <div style={{ minHeight: '100vh', background: '#f8fafc', paddingTop: '100px' }}>
      <div style={{ maxWidth: '560px', margin: '0 auto', padding: '32px 24px' }}>
        <button onClick={() => router.push('/pricing')} style={{ background: 'none', border: 'none', color: 'var(--teal)', fontSize: '13px', cursor: 'pointer', marginBottom: '24px', padding: 0 }}>← 返回定价页</button>

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

            {companies.length === 0 && (
              <div role="status" style={{ padding: '12px 14px', background: '#fff7ed', border: '1px solid #fed7aa', borderRadius: '8px', color: '#9a3412', fontSize: '13px', marginTop: '12px' }}>
                请先在工作区创建企业档案，再为该企业购买报告。
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

            {!qrCodeUrl ? (
              <>
                <div style={{ display: 'flex', gap: '8px', marginBottom: '16px' }}>
                  {([['alipay', '支付宝'], ['wechat', '微信支付']] as [Provider, string][]).map(([key, label]) => (
                    <button
                      key={key}
                      type="button"
                      onClick={() => setProvider(key)}
                      aria-pressed={provider === key}
                      style={{
                        flex: 1,
                        padding: '10px',
                        borderRadius: '8px',
                        fontSize: '14px',
                        fontWeight: 600,
                        cursor: 'pointer',
                        border: provider === key ? '2px solid #126a9a' : '1px solid #e2e8f0',
                        background: provider === key ? '#f2f8fc' : '#fff',
                        color: provider === key ? '#126a9a' : '#64748b',
                      }}
                    >
                      {label}
                    </button>
                  ))}
                </div>
                <button
                  onClick={handlePay}
                  disabled={paying || !selectedCompany}
                  style={{ width: '100%', padding: '14px', borderRadius: '10px', border: 'none', background: paying ? '#94a3b8' : '#f97316', color: '#fff', fontSize: '16px', fontWeight: 600, cursor: paying ? 'not-allowed' : 'pointer' }}
                >
                  {paying ? '处理中...' : provider === 'alipay' ? `确认支付 ¥${price}` : `生成付款二维码 ¥${price}`}
                </button>
                <p style={{ fontSize: '11px', color: '#94a3b8', textAlign: 'center', marginTop: '12px' }}>
                  仅在服务端已配置并通过验证的支付供应商可用时创建结算页面。
                </p>
              </>
            ) : (
              <div style={{ textAlign: 'center' }}>
                <p style={{ fontSize: '14px', color: '#0d1b2a', fontWeight: 600, margin: '4px 0 12px' }}>
                  请使用微信扫码支付
                </p>
                {/* code_url 渲染为二维码；仅公开用于唤起支付，不含敏感信息 */}
                <img
                  src={`https://api.qrserver.com/v1/create-qr-code/?size=200x200&margin=8&data=${encodeURIComponent(qrCodeUrl)}`}
                  alt="微信支付的二维码"
                  width={200}
                  height={200}
                  style={{ borderRadius: '8px', border: '1px solid #e2e8f0' }}
                />
                <div style={{ fontSize: '13px', color: '#64748b', marginTop: '12px' }}>
                  {paid ? (
                    <span style={{ color: '#059669', fontWeight: 600 }}>支付成功，正在跳转…</span>
                  ) : countdown > 0 ? (
                    <>等待支付中… {Math.floor(countdown / 60)}:{String(countdown % 60).padStart(2, '0')}</>
                  ) : (
                    <span style={{ color: '#dc2626' }}>二维码已过期，请重新发起</span>
                  )}
                </div>
                <button
                  onClick={() => { stopTimers(); setQrCodeUrl(''); setPendingOrder(''); }}
                  style={{ marginTop: '12px', background: 'none', border: 'none', color: '#64748b', fontSize: '13px', cursor: 'pointer', textDecoration: 'underline' }}
                >
                  更换支付方式或取消
                </button>
              </div>
            )}
          </div>
        </div>

        {/* Trust signals */}
        <div style={{ display: 'flex', justifyContent: 'center', gap: '24px', marginTop: '24px', fontSize: '12px', color: '#94a3b8' }}>
          <span>金额由服务端产品目录确定</span>
          <span>支付回调校验金额与币种</span>
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
