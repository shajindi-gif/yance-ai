'use client';

import { useCallback, useEffect, useRef, useState, Suspense } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import api, { Company, ProductCatalogItem } from '@/lib/api';
import PaymentQr from '@/components/PaymentQr';
import { productPresentation } from '@/lib/product-presentation';

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
  const [pollError, setPollError] = useState('');
  const pollGeneration = useRef(0);
  const [paid, setPaid] = useState(false);
  const [retryProtection, setRetryProtection] = useState(false);
  const payingRef = useRef(false);
  const attemptRef = useRef<{signature:string; key:string; order?:string} | null>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const [countdown, setCountdown] = useState(600);

  const stopTimers = useCallback(() => {
    pollGeneration.current += 1;
    if (pollRef.current) { clearInterval(pollRef.current); pollRef.current = null; }
    if (timerRef.current) { clearInterval(timerRef.current); timerRef.current = null; }
  }, []);

  const startPolling = useCallback((orderId: string) => {
    stopTimers();
    setCountdown(600); setPollError('');
    const generation = pollGeneration.current;
    const deadline = Date.now() + 600_000;
    const poll = async () => {
      if (generation !== pollGeneration.current) return;
      try {
        const result = await api.queryWechatOrder(orderId);
        if (generation !== pollGeneration.current) return;
        if (result.status === 'paid') {
          stopTimers(); setPaid(true);
          router.replace(`/success?order=${orderId}`);
          return;
        }
        setPollError('');
      } catch {
        if (generation !== pollGeneration.current) return;
        setPollError('付款状态暂时无法确认，正在重试；请勿重复付款。');
      }
      if (generation === pollGeneration.current && Date.now() < deadline)
        pollRef.current = setTimeout(() => void poll(), 3000);
    };
    void poll();
    timerRef.current = setInterval(() => {
      const remaining = Math.max(0, Math.ceil((deadline - Date.now()) / 1000));
      setCountdown(remaining);
      if (!remaining) stopTimers();
    }, 1000);
  }, [router, stopTimers]);

  useEffect(() => () => stopTimers(), [stopTimers]);

  useEffect(() => {
    if (!api.isAuthenticated()) { router.push(`/login?next=${encodeURIComponent('/checkout?' + searchParams.toString())}`); return; }
    let cancelled = false;
    Promise.all([
      api.getProducts(),
      api.getCompanies(),
      api.getAuthConfig().catch(() => null),
    ]).then(([products, comps, config]) => {
      if (cancelled) return;
      const p = products.find((item) => item.code === productCode) ?? null;
      setRetryProtection(config?.checkout_idempotency_revision === 1);
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
  }, [requestedCompany, router, productCode, searchParams]);

  const handlePay = async () => {
    if (!selectedCompany || !product || payingRef.current) return;
    payingRef.current = true;
    setPaying(true);
    setError('');
    try {
      if (product.purchase_available === false || product.code !== 'POLICY_REPORT' || product.entitlement_type !== 'report') {
        throw new Error('该产品暂不在此开放购买，请核对交付范围与开通状态');
      }
      const signature = `${product.code}:${selectedCompany}`;
      if (attemptRef.current?.signature !== signature) attemptRef.current = {signature, key:crypto.randomUUID()};
      const attempt = attemptRef.current;
      if (!attempt.order) {
        const order = await api.createOrder({product_code:product.code, resource_id:selectedCompany,
          ...(retryProtection ? {client_request_id:attempt.key} : {})});
        attempt.order = order.id;
      }
      const order = {id:attempt.order};
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
      payingRef.current = false;
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
  const presentation = productPresentation(product);
  const canPurchase = product.purchase_available !== false && product.code === 'POLICY_REPORT' && product.entitlement_type === 'report';

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
                <div style={{ fontSize: '15px', fontWeight: 600, color: '#0d1b2a' }}>{presentation.name}</div>
                <div style={{ fontSize: '12px', color: '#64748b', marginTop: '4px' }}>商品：{product.name} · {product.code}</div>
                <p style={{ fontSize: '12px', lineHeight: 1.6, color: '#475569' }}>{presentation.boundary}</p>
              </div>
              <div style={{ textAlign: 'right', flexShrink: 0, marginLeft: '16px' }}>
                <div style={{ fontSize: '24px', fontWeight: 700, color: '#f97316' }}>¥{price}</div>
              </div>
            </div>

            {/* Company selection */}
            {companies.length > 0 && (
              <div style={{ padding: '16px 0' }}>
                <label style={{ display: 'block', fontSize: '13px', fontWeight: 500, color: '#374151', marginBottom: '8px' }}>选择企业</label>
                <select
                  aria-label="选择企业"
                  value={selectedCompany}
                  disabled={paying || !!pendingOrder} onChange={e => setSelectedCompany(e.target.value)}
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
                请先在工作区创建企业档案，再为该企业购买报告。<p><a href="/onboarding?next=%2Fcheckout%3Fproduct%3DPOLICY_REPORT">创建企业后返回购买 →</a></p>
              </div>
            )}

            {error && (
              <div role="alert" style={{ padding: '10px 14px', background: '#fef2f2', border: '1px solid #fecaca', borderRadius: '8px', color: '#dc2626', fontSize: '13px', marginTop: '12px' }}>{error}{!pendingOrder && <p><a href="/policy-scan">前往政策扫描，准备报告 →</a></p>}{pendingOrder && <p><a href="/orders">查看已有订单，避免重复购买 →</a></p>}</div>
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
                      disabled={paying || (!!pendingOrder && provider !== key)}
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
                {pendingOrder && <p role="status">订单已保留，重试将继续这笔订单。请勿重复下单或付款。</p>}
                <p style={{fontSize:12,color:'var(--muted)'}}>手机上可优先使用支付宝；微信付款二维码需使用另一台设备扫码。</p>
                <button
                  onClick={handlePay}
                  disabled={paying || !selectedCompany || !canPurchase}
                  style={{ width: '100%', padding: '14px', borderRadius: '10px', border: 'none', background: paying ? '#94a3b8' : '#f97316', color: '#fff', fontSize: '16px', fontWeight: 600, cursor: paying ? 'not-allowed' : 'pointer' }}
                >
                  {!canPurchase ? '待开通' : paying ? '处理中...' : provider === 'alipay' ? `确认支付 ¥${price}` : `生成付款二维码 ¥${price}`}
                </button>
                <p style={{ fontSize: '11px', color: '#94a3b8', textAlign: 'center', marginTop: '12px' }}>
                  付款后自动核对订单。未确认成功前，请勿再次付款。
                </p>
              </>
            ) : (
              <div style={{ textAlign: 'center' }}>
                <p style={{ fontSize: '14px', color: '#0d1b2a', fontWeight: 600, margin: '4px 0 12px' }}>
                  请使用微信扫码支付
                </p>
                <PaymentQr value={qrCodeUrl} />
                <div style={{ fontSize: '13px', color: '#64748b', marginTop: '12px' }}>
                  {paid ? (
                    <span style={{ color: '#059669', fontWeight: 600 }}>支付成功，正在跳转…</span>
                  ) : countdown > 0 ? (
                    <>等待支付中… {Math.floor(countdown / 60)}:{String(countdown % 60).padStart(2, '0')}</>
                  ) : (
                    <span style={{ color: '#dc2626' }}>暂未收到付款确认，请核对订单后再继续</span>
                  )}
                </div>
                {pollError && <p role="status">{pollError}</p>}
                <p><a href={`/success?order=${pendingOrder}`}>已完成付款？查看订单结果 →</a></p>
                <button
                  onClick={() => { stopTimers(); setQrCodeUrl(''); }}
                  style={{ marginTop: '12px', background: 'none', border: 'none', color: '#64748b', fontSize: '13px', cursor: 'pointer', textDecoration: 'underline' }}
                >
                  收起二维码，保留订单
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
