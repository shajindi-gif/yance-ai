'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import api from '@/lib/api';

interface Product {
  id: string;
  code: string;
  name: string;
  description: string;
  product_type: string;
  price: number;
  original_price: number | null;
  promotional_price: number | null;
  entitlement_type: string;
}

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'https://api.yance.ai/api/v1';

export default function PricingPage() {
  const router = useRouter();
  const [products, setProducts] = useState<Product[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch(API_BASE + '/products')
      .then(r => r.json())
      .then(data => { setProducts(data); setLoading(false); })
      .catch(() => setLoading(false));
  }, []);

  const handleCTA = (product: Product) => {
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

  const FEATURES: Record<string, string[]> = {
    FREE_POLICY_MATCH: [
      '企业画像建立',
      'AI 政策匹配',
      'Top 5 政策机会',
      '基础匹配理由',
      '政策来源追溯',
    ],
    POLICY_REPORT: [
      '完整政策匹配（不限条数）',
      '企业资格矩阵',
      '条件差距分析',
      '行动路线图（P0-P3）',
      '申报日历',
      '材料准备清单',
      '专业 PDF 交付',
      '无限次查看与下载',
    ],
    POLICY_DIAGNOSIS: [
      '单政策全部硬性条件逐条判断',
      '已满足 / 未满足 / 无法判断',
      '材料清单 + 申报流程',
      '时间节点 + 评分机制',
      '主要风险 + 竞争优势',
      '下一步行动 Checklist',
      '专业 PDF 交付',
    ],
    APPLICATION_PLAN: [
      '诊断全部内容',
      '申报策略 + 企业亮点提炼',
      '材料目录 + 证明目录',
      '项目实施计划',
      '信息缺口分析',
      '填报 Checklist',
      '专业 PDF 交付',
    ],
  };

  return (
    <>
      <section className="page-banner" style={{ background: 'linear-gradient(135deg, #0d1b2a 0%, #1b2d44 60%, #0d1b2a 100%)' }}>
        <div className="container">
          <span className="badge" style={{ background: 'rgba(14,165,233,0.2)', color: '#0ea5e9', marginBottom: '16px' }}>按次付费</span>
          <h1>按次购买，需要时再买</h1>
          <p>无需订阅，无自动续费。免费注册即可体验政策匹配，深度交付物按次购买。</p>
        </div>
      </section>

      <section className="section">
        <div className="container">
          {loading ? (
            <div style={{ textAlign: 'center', padding: '60px 0', color: '#64748b' }}>加载产品目录...</div>
          ) : (
            <div className="grid grid-4" style={{ gap: '20px', alignItems: 'start' }}>
              {products.map((product) => {
                const isFeatured = product.code === 'POLICY_REPORT';
                const features = FEATURES[product.code] || [];
                return (
                  <div key={product.code} className={`pricing-card${isFeatured ? ' pricing-card-featured' : ''}`} style={isFeatured ? { borderColor: '#f97316', borderWidth: '2px' } : {}}>
                    {isFeatured && (
                      <div style={{ position: 'absolute', top: '-14px', left: '50%', transform: 'translateX(-50%)', padding: '4px 16px', background: '#f97316', color: '#fff', fontSize: '0.75rem', fontWeight: 600, borderRadius: '9999px', whiteSpace: 'nowrap' }}>推荐</div>
                    )}
                    <div className="pricing-name">{product.name}</div>
                    <div className="pricing-desc">{product.description}</div>
                    <div className="pricing-price">
                      {product.price === 0 ? (
                        <span style={{ color: '#16a34a' }}>免费</span>
                      ) : (
                        <>
                          {product.original_price && (
                            <span style={{ textDecoration: 'line-through', color: '#94a3b8', fontSize: '0.875rem', marginRight: '8px' }}>¥{product.original_price}</span>
                          )}
                          ¥{product.price}
                          <span className="pricing-price-unit">/ 份</span>
                        </>
                      )}
                    </div>
                    <div className="pricing-divider" />
                    <ul className="pricing-features">
                      {features.map((f) => (<li key={f}>{f}</li>))}
                    </ul>
                    <button
                      onClick={() => handleCTA(product)}
                      className={`btn ${isFeatured ? '' : 'btn-outline'}`}
                      style={isFeatured
                        ? { background: '#f97316', color: '#fff', borderColor: '#f97316', borderRadius: '12px', width: '100%', cursor: 'pointer' }
                        : { borderRadius: '12px', width: '100%', cursor: 'pointer' }}
                    >
                      {product.price === 0 ? '免费开始' : '立即购买'}
                    </button>
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
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '8px', flexWrap: 'wrap', padding: '24px 0' }}>
            {[
              { label: '免费匹配', price: '¥0' },
              { label: '体检报告', price: '¥99' },
              { label: '申报诊断', price: '¥299' },
              { label: '申报方案', price: '¥699' },
            ].map((step, i) => (
              <div key={step.label} style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <div style={{ padding: '16px 24px', background: '#fff', borderRadius: '12px', textAlign: 'center', minWidth: '120px', border: '1px solid var(--border, #e2e8f0)' }}>
                  <div style={{ fontWeight: 700, color: '#0d1b2a' }}>{step.label}</div>
                  <div style={{ color: '#f97316', fontWeight: 600, marginTop: '4px' }}>{step.price}</div>
                </div>
                {i < 3 && <span style={{ fontSize: '20px', color: '#94a3b8' }}>→</span>}
              </div>
            ))}
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
          <h2 className="cta-title">30 秒注册，立即发现你能申报的政策</h2>
          <p className="cta-subtitle">免费注册即可体验政策匹配，无需信用卡。</p>
          <div className="cta-actions">
            <button onClick={() => api.isAuthenticated() ? router.push('/dashboard') : router.push('/login?register=1')} className="btn btn-lg" style={{ background: '#f97316', color: '#fff', borderColor: '#f97316', borderRadius: '12px', cursor: 'pointer' }}>免费开始</button>
            <a href="mailto:contact@yance.ai" className="btn btn-outline-white btn-lg">企业定制咨询</a>
          </div>
        </div>
      </section>
    </>
  );
}
