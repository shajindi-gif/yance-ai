'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import api, { ProductCatalogItem } from '@/lib/api';

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
      router.push('/login?register=1');
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
          <p>按当前产品目录选择所需服务。无需订阅，无自动续费；具体权益与支付渠道以购买页面为准。</p>
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
                const isPurchasableHere = product.price === 0 || product.entitlement_type === 'report';
                const displayedPrice = product.promotional_price ?? product.price;
                return (
                  <div key={product.code} className={`pricing-card${isFeatured ? ' pricing-card-featured' : ''}`} style={isFeatured ? { borderColor: 'var(--teal)' , borderWidth: '1px' } : {}}>
                    {isFeatured && (
                      <div style={{ position: 'absolute', top: '-14px', left: '50%', transform: 'translateX(-50%)', padding: '4px 16px', background: 'var(--teal)' , color: '#fff', fontSize: '0.75rem', fontWeight: 600, borderRadius: '9999px', whiteSpace: 'nowrap' }}>推荐</div>
                    )}
                    <div className="pricing-name">{product.name}</div>
                    <div className="pricing-desc">{product.description}</div>
                    <div className="pricing-price">
                      {displayedPrice === 0 ? (
                        <span style={{ color: '#16a34a' }}>免费</span>
                      ) : (
                        <>
                          {product.original_price && (
                            <span style={{ textDecoration: 'line-through', color: '#94a3b8', fontSize: '0.875rem', marginRight: '8px' }}>¥{product.original_price}</span>
                          )}
                          ¥{displayedPrice}
                          <span className="pricing-price-unit">/ 份</span>
                        </>
                      )}
                    </div>
                    <div className="pricing-divider" />
                    <ul className="pricing-features">
                      <li>购买前核对产品、价格与权益</li>
                      <li>交付物归属当前企业或具体机会</li>
                      <li>付款状态可在订单中查询</li>
                    </ul>
                    <button
                      onClick={() => handleCTA(product)}
                      disabled={!isPurchasableHere}
                      className={`btn ${isFeatured ? '' : 'btn-outline'}`}
                      style={isFeatured
                        ? { background: 'var(--teal)' , color: '#fff', borderColor: 'var(--teal)' , borderRadius: '12px', width: '100%', cursor: isPurchasableHere ? 'pointer' : 'not-allowed' }
                        : { borderRadius: '12px', width: '100%', cursor: isPurchasableHere ? 'pointer' : 'not-allowed' }}
                    >
                      {displayedPrice === 0
                        ? '免费开始'
                        : isPurchasableHere
                          ? '选择企业并购买'
                          : '进入工作区后购买'}
                    </button>
                    {!isPurchasableHere && displayedPrice !== 0 ? (
                      <p style={{ margin: '8px 0 0', fontSize: '12px', color: 'var(--text-muted)', lineHeight: 1.5 }}>
                        该产品在政策机会详情页内下单：先免费注册，运行匹配后在机会工作区购买。
                      </p>
                    ) : null}
                  </div>
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
            <h2 className="section-title">从发现机会到完成申报</h2>
          </div>
          <div className="card" style={{ padding: '32px', textAlign: 'center' }}>
            <p style={{ color: '#475569', margin: 0 }}>
              企业画像 → 政策扫描 → 资格与证据 → 资源绑定订单 → 可下载交付物。每个已启用产品的名称、说明和价格直接来自数据库。
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
              衍策引擎AI 使用 AI 自动化传统政策咨询中大量重复的信息搜索、规则判断、条件比对和材料整理工作。
              我们出售的是<strong>效率、结构化和即时交付</strong>，而非虚假的"内部渠道"或"特殊关系"。
            </p>
            <ul style={{ paddingLeft: '24px', color: '#64748b', fontSize: '0.9rem', lineHeight: 1.8 }}>
              <li>所有政策匹配结果均来源于公开政策数据库，可追溯</li>
              <li>匹配评分由具体条件计算得出，非 LLM 随机生成</li>
              <li>不承诺申报成功率，不承诺获得补贴金额</li>
              <li>需要第三方审计/鉴证的材料，系统会明确提示</li>
            </ul>
          </div>
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
