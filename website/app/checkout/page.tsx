'use client';

import { useCallback, useEffect, useRef, useState, Suspense } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import api, { Company, ProductCatalogItem } from '@/lib/api';
import PaymentQr from '@/components/PaymentQr';
import { productPresentation } from '@/lib/product-presentation';
import pageStyles from './page.module.css';

type Provider = 'alipay' | 'wechat';

function CheckoutContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const productCode = searchParams.get('product') || 'POLICY_REPORT';
  const resumeId = searchParams.get('order') || '';
  const [resumeAmount, setResumeAmount] = useState<number | null>(null);
  const [resumeBlocked, setResumeBlocked] = useState(false);
  const resumeSupported = useRef(false);
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
  const [countdown, setCountdown] = useState(0);

  const stopTimers = useCallback(() => {
    pollGeneration.current += 1;
    if (pollRef.current) { clearInterval(pollRef.current); pollRef.current = null; }
    if (timerRef.current) { clearInterval(timerRef.current); timerRef.current = null; }
  }, []);

  const startPolling = useCallback((orderId: string, expiresAt: string) => {
    stopTimers();
    setPollError('');
    const generation = pollGeneration.current;
    const deadline = Date.parse(expiresAt);
    if (!Number.isFinite(deadline) || deadline <= Date.now()) {
      setCountdown(0);
      setPollError('付款码已到期，请返回订单核对状态后继续。');
      return;
    }
    setCountdown(Math.ceil((deadline - Date.now()) / 1000));
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
    ]).then(async ([products, comps, config]) => {
      resumeSupported.current = config?.checkout_resume_revision === 1;
      const state = resumeId && resumeSupported.current ? await api.getCheckoutState(resumeId) : null;
      if (cancelled) return;
      const p = products.find((item) => item.code === (state?.order.product_code ?? productCode)) ?? null;
      setResumeBlocked(!!resumeId && (!state || !state.can_continue || state.order.currency !== "CNY"));
      if (resumeId && !state) setError("当前后台尚不支持恢复付款，请到订单列表核对；不会另建订单。");
      if (state) {
        const order = state.order;
        if (order.status === "paid") { router.replace(`/success?order=${order.id}`); return; }
        setResumeAmount(Number(order.amount)); setPendingOrder(order.id);
        setSelectedCompany(order.resource_id ?? "");
        if (state.provider === "wechat" || state.provider === "alipay") setProvider(state.provider);
        attemptRef.current = {signature:`${order.product_code}:${order.resource_id}`,key:crypto.randomUUID(),order:order.id};
        if (state.reason) setError(state.reason);
      }
      setRetryProtection(config?.checkout_idempotency_revision === 1);
      setProduct(p);
      setCompanies(comps);
      if (comps.length > 0 && !state) {
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
  }, [requestedCompany, router, productCode, searchParams, resumeId]);

  const handlePay = async () => {
    if (!selectedCompany || !product || payingRef.current || resumeBlocked) return;
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
        if (order.status === "paid") { router.replace(`/success?order=${order.id}`); return; }
        if (typeof order.amount === "number") {
          setResumeAmount(order.amount);
          if (order.amount !== (resumeAmount ?? product.promotional_price ?? product.price)) {
            setPendingOrder(order.id);
            throw new Error('价格已更新，请核对订单金额后再次确认付款；本次尚未调用支付渠道。');
          }
        }
      }
      const order = {id:attempt.order};
      setPendingOrder(order.id);
      if (resumeSupported.current && !resumeId) {
        const query = new URLSearchParams({order:order.id,product:product.code,company:selectedCompany});
        window.history.replaceState(null, "", `/checkout?${query}`);
      }
      if (provider === 'alipay') {
        const checkout = await api.createCheckout(order.id);
        window.location.assign(checkout.url);
        return;
      }
      const wechat = await api.createWechatNativeOrder(order.id);
      setQrCodeUrl(wechat.code_url);
      startPolling(order.id, wechat.expires_at);
    } catch (err) {
      setError(err instanceof Error ? err.message : '支付失败，请重试');
    } finally {
      payingRef.current = false;
      setPaying(false);
    }
  };

  if (loading) return (
    <div className={pageStyles.layout}>
      <div className={pageStyles.section}>加载中...</div>
    </div>
  );

  if (!product) return (
    <div className={pageStyles.layout}>
      <div className={pageStyles.section2}>
        <div className={pageStyles.section3}>暂时无法结账</div>
        <h2 className={pageStyles.heading}>产品未找到</h2>
        <p className={pageStyles.description}>请从定价页选择产品</p>
        <button onClick={() => router.push('/pricing')} className={pageStyles.action}>返回定价页</button>
      </div>
    </div>
  );

  const price = resumeAmount ?? product.promotional_price ?? product.price;
  const presentation = productPresentation(product);
  const canPurchase = !resumeBlocked && product.purchase_available !== false && product.code === 'POLICY_REPORT' && product.entitlement_type === 'report';

  return (
    <div className={pageStyles.section4}>
      <div className={pageStyles.section5}>
        <button onClick={() => router.push('/pricing')} className={pageStyles.action2}>← 返回定价页</button>

        <div className={pageStyles.section6}>
          {/* Order summary */}
          <div className={pageStyles.section7}>
            <h1 className={pageStyles.heading2}>确认订单</h1>

            <div className={pageStyles.layout2}>
              <div>
                <div className={pageStyles.section8}>{presentation.name}</div>
                <div className={pageStyles.section9}>商品：{product.name} · {product.code}</div>
                <p className={pageStyles.description2}>{presentation.boundary}</p>
              </div>
              <div className={pageStyles.section10}>
                <div className={pageStyles.section11}>¥{price}</div>
              </div>
            </div>

            {/* Company selection */}
            {companies.length > 0 && (
              <div className={pageStyles.section12}>
                <label className={pageStyles.layout3}>选择企业</label>
                <select
                  aria-label="选择企业"
                  value={selectedCompany}
                  disabled={paying || !!pendingOrder} onChange={e => setSelectedCompany(e.target.value)}
                  className={pageStyles.section13}
                >
                  {companies.map(c => (
                    <option key={c.id} value={c.id}>{c.name} ({c.industry || '—'} / {c.province || '—'})</option>
                  ))}
                </select>
              </div>
            )}

            {companies.length === 0 && (
              <div role="status" className={pageStyles.section14}>
                请先在工作区创建企业档案，再为该企业购买报告。<p><a href="/onboarding?next=%2Fcheckout%3Fproduct%3DPOLICY_REPORT">创建企业后返回购买 →</a></p>
              </div>
            )}

            {error && (
              <div role="alert" className={pageStyles.section15}>{error}{!pendingOrder && <p><a href="/discover">前往政策扫描，准备报告 →</a> · <a href="/orders">查看已有订单</a></p>}{pendingOrder && <p><a href="/orders">查看已有订单，避免重复购买 →</a></p>}</div>
            )}
          </div>

          {/* Payment section */}
          <div className={pageStyles.section16}>
            <div className={pageStyles.layout4}>
              <span className={pageStyles.label}>应付金额</span>
              <span className={pageStyles.label2}>¥{price}</span>
            </div>

            {!qrCodeUrl ? (
              <>
                <div className={pageStyles.layout5}>
                  {([['alipay', '支付宝'], ['wechat', '微信支付']] as [Provider, string][]).map(([key, label]) => (
                    <button
                      key={key}
                      type="button"
                      disabled={paying || (!!pendingOrder && provider !== key)}
                      onClick={() => setProvider(key)}
                      aria-pressed={provider === key}
                      className={pageStyles.inlineAction} style={{ border: provider === key ? '2px solid #126a9a' : '1px solid #e2e8f0', background: provider === key ? '#f2f8fc' : 'var(--surface)', color: provider === key ? 'var(--accent)' : '#64748b' }}
                    >
                      {label}
                    </button>
                  ))}
                </div>
                {pendingOrder && <p role="status">订单已保留，重试将继续这笔订单。请勿重复下单或付款。</p>}
                <p className={pageStyles.description3}>手机上可优先使用支付宝；微信付款二维码需使用另一台设备扫码。</p>
                <button
                  onClick={handlePay}
                  disabled={paying || !selectedCompany || !canPurchase}
                  className={pageStyles.inlineAction2} style={{ background: paying ? '#94a3b8' : 'var(--accent)', cursor: paying ? 'not-allowed' : 'pointer' }}
                >
                  {!canPurchase ? (resumeBlocked ? '暂不能继续付款' : '待开通') : paying ? '处理中...' : provider === 'alipay' ? `确认支付 ¥${price}` : `生成付款二维码 ¥${price}`}
                </button>
                <p className={pageStyles.description4}>
                  付款后自动核对订单。未确认成功前，请勿再次付款。
                </p>
              </>
            ) : (
              <div className={pageStyles.section2}>
                <p className={pageStyles.description5}>
                  请使用微信扫码支付
                </p>
                <PaymentQr value={qrCodeUrl} />
                <div className={pageStyles.section17}>
                  {paid ? (
                    <span className={pageStyles.label3}>支付成功，正在跳转…</span>
                  ) : countdown > 0 ? (
                    <>等待支付中… {Math.floor(countdown / 60)}:{String(countdown % 60).padStart(2, '0')}</>
                  ) : (
                    <span className={pageStyles.label4}>暂未收到付款确认，请核对订单后再继续</span>
                  )}
                </div>
                {pollError && <p role="status">{pollError}</p>}
                <p><a href={`/success?order=${pendingOrder}`}>已完成付款？查看订单结果 →</a></p>
                <button
                  onClick={() => { stopTimers(); setQrCodeUrl(''); }}
                  className={pageStyles.action3}
                >
                  收起二维码，保留订单
                </button>
              </div>
            )}
          </div>
        </div>

        {/* Trust signals */}
        <div className={pageStyles.layout6}>
          <span>金额由服务端产品目录确定</span>
          <span>支付回调校验金额与币种</span>
        </div>
      </div>
    </div>
  );
}

export default function CheckoutPage() {
  return (
    <Suspense fallback={<div className={pageStyles.layout7}>加载中...</div>}>
      <CheckoutContent />
    </Suspense>
  );
}
