'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import api, { ProductCatalogItem } from '@/lib/api';
import { productPresentation } from '@/lib/product-presentation';

export default function PricingPage() {
  const router = useRouter();
  const [products, setProducts] = useState<ProductCatalogItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [retry, setRetry] = useState(0);

  useEffect(() => {
    let cancelled = false;
    setLoading(true); setError('');
    api.getProducts()
      .then((data) => {
        if (!cancelled) setProducts(data);
      })
      .catch(() => {
        if (!cancelled) setError('当前无法读取服务端产品目录，请稍后重试。');
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [retry]);

  const handleCTA = (product: ProductCatalogItem) => {
    if (product.code === 'FREE_POLICY_MATCH') {
      if (api.isAuthenticated()) router.push('/dashboard');
      else router.push('/login?register=1');
      return;
    }
    if (!api.isAuthenticated()) {
      router.push(`/login?register=1&next=${encodeURIComponent('/checkout?product=' + product.code)}`);
      return;
    }
    router.push(`/checkout?product=${product.code}`);
  };

  return (
    <>
      <section className="page-banner" style={{ background: 'linear-gradient(135deg, #0d1b2a 0%, #1b2d44 60%, #0d1b2a 100%)' }}>
        <div className="container">
          <span className="badge" style={{ background: 'rgba(14,165,233,0.2)', color: 'var(--teal)', marginBottom: '16px' }}>按次付费</span>
          <h1>按次购买，需要时再买</h1>
          <p>先免费发现机会，再按需要购买。金额来自服务端目录；项目产品单独标注开通状态，购买前请核对交付范围与账户权益。</p>
        </div>
      </section>

      <section className="section">
        <div className="container">
          {loading ? (
            <div role="status"><span className="yc-visually-hidden">加载产品目录...</span><div className="grid grid-4 pricing-loading" aria-hidden="true">{[0,1,2,3].map(item => <div className="pricing-card" key={item}><div className="pricing-placeholder" /><div className="pricing-placeholder" /><div className="pricing-placeholder" /></div>)}</div></div>
          ) : error ? (
            <div role="alert" style={{ textAlign: 'center', padding: '60px 0', color: '#b91c1c' }}><p>{error}</p><button type="button" className="btn btn-outline" onClick={() => setRetry(value => value + 1)}>重新加载产品目录</button></div>
          ) : products.length === 0 ? (
            <div style={{ textAlign: 'center', padding: '60px 0', color: '#64748b' }}>
              当前没有已启用的产品。这里不会用静态价格代替真实服务端目录。
            </div>
          ) : (
            <div className="grid grid-4 pricing-catalogue">
              {products.map((product) => {
                const isFeatured = product.code === 'POLICY_REPORT';
                const isPurchasableHere = product.code === 'FREE_POLICY_MATCH' || (product.purchase_available !== false && product.code === 'POLICY_REPORT' && product.entitlement_type === 'report');
                const presentation = productPresentation(product);
                const displayedPrice = product.promotional_price ?? product.price;
                return (
                  <article aria-label={presentation.name} key={product.code} className={`pricing-card${isFeatured ? ' pricing-card-featured' : ''}`} style={isFeatured ? { borderColor: 'var(--teal)' , borderWidth: '1px' } : {}}>
                    {isFeatured && (
                      <div style={{ position: 'absolute', top: '-14px', left: '50%', transform: 'translateX(-50%)', padding: '4px 16px', background: 'var(--teal)' , color: '#fff', fontSize: '0.75rem', fontWeight: 600, borderRadius: '9999px', whiteSpace: 'nowrap' }}>按需首购</div>
                    )}
                    <h2 className="pricing-name">{presentation.name}</h2>
                    <p className="pricing-desc">{isPurchasableHere ? '按次使用 · 具体权益以购买页面为准' : '待开通 · 目录产品，交付待验收'}</p>
                    <div className="pricing-price">
                      {displayedPrice === 0 ? (
                        <span style={{ color: '#16a34a' }}>免费</span>
                      ) : (
                        <>
                          ¥{displayedPrice}
                          <span className="pricing-price-unit">{presentation.unit}</span>
                        </>
                      )}
                    </div>
                    <div className="pricing-divider" />
                    <ul className="pricing-features">
                      {presentation.features.map(feature => <li key={feature}>{feature}</li>)}
                    </ul>
                    <button
                      onClick={() => handleCTA(product)}
                      disabled={!isPurchasableHere}
                      className={`btn ${isFeatured ? '' : 'btn-outline'}`}
                      style={isFeatured
                        ? { background: 'var(--teal)' , color: '#fff', borderColor: 'var(--teal)' , borderRadius: '12px', width: '100%', cursor: isPurchasableHere ? 'pointer' : 'not-allowed' }
                        : { borderRadius: '12px', width: '100%', cursor: isPurchasableHere ? 'pointer' : 'not-allowed' }}
                    >
                      {product.code === 'FREE_POLICY_MATCH'
                        ? '免费开始'
                        : isPurchasableHere
                          ? '选择企业并购买'
                          : '待开通'}
                    </button>
                    <p className="pricing-boundary">{product.purchase_unavailable_reason || presentation.boundary}</p>
                  </article>
                );
              })}
            </div>
          )}
        </div>
      </section>

      {/* Value Chain */}
      <section className="section section-alt">
        <div className="container">
          <div className="section-header">
            <span className="section-label">产品阶梯</span>
            <h2 className="section-title">按交付选择，按证据推进</h2>
          </div>
          <div className="card" style={{ padding: '32px', textAlign: 'center' }}>
            <p style={{ color: '#475569', margin: 0 }}>
              企业资料 → 政策初筛 → 条件与证据核对 → 材料准备 → 客户自主复核。目录价格来自服务端；套餐名称是交付范围说明，不改变商品编号、历史订单或已有权益。
            </p>
          </div>
        </div>
      </section>

      {/* Trust */}
      <section className="section">
        <div className="container container-narrow">
          <div className="section-header">
            <span className="section-label">我们的承诺</span>
            <h2 className="section-title">AI 辅助，不伪造</h2>
          </div>
          <div className="card" style={{ padding: '32px' }}>
            <p style={{ fontSize: '0.95rem', lineHeight: 1.7, color: '#334155', marginBottom: '16px' }}>
              政策与原文由服务器采集，企业资料由客户提供。采集入库不代表已核验、完整或仍然有效；复核由客户本人或客户授权团队完成。
            </p>
            <ul style={{ paddingLeft: '24px', color: '#64748b', fontSize: '0.9rem', lineHeight: 1.8 }}>
              <li>核对政策来源、有效期与当期申报截止时间</li>
              <li>缺失资料保持证据不足，客户确认不等于政府认定</li>
              <li>不承诺申报成功率，不承诺获得补贴金额</li>
              <li>付款凭证不等于正式税票；开票以实际申请流程为准</li>
            </ul>
          </div>
        </div>
      </section>

      <section className="section section-alt">
        <div className="container container-narrow">
          <h2 className="section-title">持续协作，先把每一次交付做好</h2>
          <p>团队订阅仍在准备中，暂不开放购买。现有客户的订单与账户权益继续按原约定执行。</p>
          <details className="pricing-faq"><summary>购买前需要确认什么？</summary><p>先确认企业、政策或批次、输入资料、交付格式及支付渠道。信息不足时可能得到“证据不足”或“不符合”的结果，付款不代表申报资格成立。</p></details>
          <details className="pricing-faq"><summary>衍策会替企业审核和申报吗？</summary><p>业务复核由客户本人或授权团队完成。衍策辅助检索和材料准备，不提供人工业务审核、政府认定或补贴到账保证。</p></details>
          <details className="pricing-faq"><summary>如何查看已有购买记录？</summary><p>登录后在订单与账户权益中核对。已有购买不因展示名称调整而失效；遇到交付异常，请保留订单编号联系支持。</p></details>
        </div>
      </section>
      {/* CTA */}
      <section className="cta-section" style={{ background: 'linear-gradient(135deg, #0d1b2a 0%, #1b2d44 50%, #0d1b2a 100%)' }}>
        <div className="container">
          <h2 className="cta-title">创建工作区，开始政策机会初筛</h2>
          <p className="cta-subtitle">免费注册即可体验政策匹配，无需信用卡。</p>
          <div className="cta-actions">
            <button onClick={() => api.isAuthenticated() ? router.push('/dashboard') : router.push('/login?register=1')} className="btn btn-lg" style={{ background: 'var(--teal)' , color: '#fff', borderColor: 'var(--teal)' , borderRadius: '12px', cursor: 'pointer' }}>免费开始</button>
            <a href="mailto:yanceai@163.com" className="btn btn-outline-white btn-lg">企业定制咨询</a>
          </div>
        </div>
      </section>
    </>
  );
}
