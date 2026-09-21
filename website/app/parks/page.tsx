import Link from 'next/link';

export const metadata = {
  title: '园区入驻与资源匹配 | 衍策引擎AI',
  description:
    '按企业行业、发展阶段与资源需求推荐园区入驻方案，匹配产业资源与扶持政策。',
};


export default function ParksPage() {
  return (
    <>
      {/* Page Banner */}
      <section
        className="page-banner"
        style={{
          background: 'linear-gradient(135deg, #0d1b2a 0%, #1b2d44 60%, #0d1b2a 100%)',
        }}
      >
        <div className="container">
          <span
            className="badge"
            style={{
              background: 'rgba(14,165,233,0.2)',
              color: 'var(--teal)',
              marginBottom: '16px',
            }}
          >
            园区解决方案
          </span>
          <h1>重新定义园区企业服务</h1>
          <p>
            为产业园区、孵化器和加速器提供一站式智能政策服务平台，让企业服务工作从经验驱动转向数据驱动。
          </p>
        </div>
      </section>

      {/* Overview - Value Props */}
      <section className="section">
        <div className="container">
          <div className="section-header">
            <span className="section-label">方案概览</span>
            <h2 className="section-title">为什么选择 Policy Agent</h2>
            <p className="section-subtitle">
              Policy Agent 帮助园区建立标准化、智能化、可追溯的企业服务体系，提升服务效率和入驻企业满意度。
            </p>
          </div>

          <div className="grid grid-3" style={{ gap: '24px' }}>
            <div className="card" style={{ borderTop: '3px solid #f97316' }}>
              <div className="card-icon" style={{ background: '#fff7ed', color: '#f97316' }}>
                &#x1F3AF;
              </div>
              <h3 className="card-title">精准服务</h3>
              <p className="card-desc">
                基于企业画像和政策条件形成可复核的匹配结果；准确率需在真实试点数据上评测。
              </p>
            </div>
            <div className="card" style={{ borderTop: '3px solid #126a9a' }}>
              <div className="card-icon" style={{ background: '#f0f9ff', color: 'var(--teal)' }}>
                &#x26A1;
              </div>
              <h3 className="card-title">效率提升</h3>
              <p className="card-desc">
                将政策检索、资格判断、材料缺口和文档任务放入同一工作流，减少重复搬运信息。
              </p>
            </div>
            <div className="card" style={{ borderTop: '3px solid #16a34a' }}>
              <div className="card-icon" style={{ background: '#f0fdf4', color: '#16a34a' }}>
                &#x1F4C8;
              </div>
              <h3 className="card-title">数据驱动</h3>
              <p className="card-desc">
                实时掌握园区企业服务全貌，运营决策有据可依，服务覆盖率和企业满意度持续提升。
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* Who It Serves */}
      <section className="section section-alt">
        <div className="container">
          <div className="section-header">
            <span className="section-label">适用客户</span>
            <h2 className="section-title">服务各类产业服务机构</h2>
          </div>

          <div className="grid grid-4" style={{ gap: '20px' }}>
            {[
              { icon: '\u{1F3ED}', title: '产业园区', desc: '国家级/市级产业园区的企业服务部门' },
              { icon: '\u{1F331}', title: '孵化器', desc: '科技企业孵化器和创业服务中心' },
              { icon: '\u{1F680}', title: '加速器', desc: '产业加速器和科技成果转化平台' },
              { icon: '\u{1F3DB}\u{FE0F}', title: '政务平台', desc: '区域经济发展中心和招商引资平台' },
            ].map((item) => (
              <div key={item.title} className="card-flat" style={{ textAlign: 'center', padding: '32px 24px' }}>
                <div
                  className="card-icon"
                  style={{ margin: '0 auto 16px', background: 'var(--bg-alt)' }}
                >
                  {item.icon}
                </div>
                <h4 className="card-title">{item.title}</h4>
                <p className="card-desc">{item.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Features Grid */}
      <section className="section">
        <div className="container">
          <div className="section-header">
            <span className="section-label">核心功能</span>
            <h2 className="section-title">端到端的园区智能服务体系</h2>
            <p className="section-subtitle">
              五大核心模块覆盖从政策数据到服务交付的完整链路。
            </p>
          </div>

          <div className="split">
            <div className="split-content">
              <h3 className="mb-4">五层产品架构</h3>
              <div className="feature-list">
                <div className="feature-item">
                  <div className="feature-item-icon">&#x1F4DA;</div>
                  <div>
                    <h4 className="feature-item-title">政策数据库</h4>
                    <p className="feature-item-desc">
                      对已导入政策保存来源、地区、日期和状态；覆盖范围以后台真实数据为准。
                    </p>
                  </div>
                </div>
                <div className="feature-item">
                  <div className="feature-item-icon" style={{ background: '#f0fdf4', color: '#16a34a' }}>
                    &#x1F3E2;
                  </div>
                  <div>
                    <h4 className="feature-item-title">企业画像引擎</h4>
                    <p className="feature-item-desc">
                      整合工商注册、知识产权、财务数据、资质认证等多维度企业信息。
                    </p>
                  </div>
                </div>
                <div className="feature-item">
                  <div className="feature-item-icon" style={{ background: '#fff7ed', color: '#f97316' }}>
                    &#x1F916;
                  </div>
                  <div>
                    <h4 className="feature-item-title">智能匹配引擎</h4>
                    <p className="feature-item-desc">
                      融合规则引擎和 AI 模型，自动计算企业与政策的适配度评分。
                    </p>
                  </div>
                </div>
                <div className="feature-item">
                  <div className="feature-item-icon">&#x1F4CB;</div>
                  <div>
                    <h4 className="feature-item-title">材料生成引擎</h4>
                    <p className="feature-item-desc">
                      自动生成申报材料清单、服务简报和政策推荐报告。
                    </p>
                  </div>
                </div>
                <div className="feature-item">
                  <div className="feature-item-icon" style={{ background: '#f0fdf4', color: '#16a34a' }}>
                    &#x1F4CA;
                  </div>
                  <div>
                    <h4 className="feature-item-title">运营工作台</h4>
                    <p className="feature-item-desc">
                      统一管理服务任务、跟踪申报进度、生成运营分析报告。
                    </p>
                  </div>
                </div>
              </div>
            </div>
            <div className="split-visual">
              <div style={{ textAlign: 'center', width: '100%' }}>
                <div style={{ fontSize: '3rem', marginBottom: '16px' }}>&#x1F3D7;&#xFE0F;</div>
                <h4 style={{ marginBottom: '12px' }}>分层架构</h4>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                  {['运营层 (ParkOps)', '交付层 (BriefMaker)', '引擎层 (SubsidyMatch)', '画像层 (CompanyProfile)', '数据层 (PolicyCopilot)'].map((layer, i) => (
                    <div
                      key={layer}
                      style={{
                        padding: '12px 16px',
                        background: i === 0 ? '#0d1b2a' : i === 1 ? '#1b2d44' : i === 2 ? '#126a9a' : i === 3 ? '#16a34a' : '#f97316',
                        color: '#fff',
                        borderRadius: '8px',
                        fontSize: '0.875rem',
                        fontWeight: 600,
                        textAlign: 'center',
                      }}
                    >
                      {layer}
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Deployment Process */}
      <section className="section section-alt">
        <div className="container">
          <div className="section-header">
            <span className="section-label">示例实施方案</span>
            <h2 className="section-title">分阶段试点路线</h2>
            <p className="section-subtitle">以下为方案模板，不代表已签约项目或固定交付周期。</p>
          </div>

          <div className="grid grid-4" style={{ gap: '20px' }}>
            {[
              { week: '阶段 1', title: '需求对接', desc: '确认业务需求、数据边界和验收目标', badge: 'badge-primary' },
              { week: '阶段 2', title: '数据接入', desc: '在获得授权后导入企业资料与政策来源', badge: 'badge-green' },
              { week: '阶段 3', title: '受控试点', desc: '配置规则、权限和人工复核流程', badge: 'badge-orange' },
              { week: '阶段 4', title: '评测验收', desc: '使用真实结果评估质量、成本和时延', badge: 'badge-success' },
            ].map((step) => (
              <div key={step.week} className="card" style={{ textAlign: 'center' }}>
                <div className={step.badge} style={{ marginBottom: '16px', display: 'inline-block' }}>
                  {step.week}
                </div>
                <h4 className="card-title">{step.title}</h4>
                <p className="card-desc">{step.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Metrics */}
      <section className="section">
        <div className="container">
          <div className="section-header">
            <span className="section-label">真实数据原则</span>
            <h2 className="section-title">尚无可公开的客户成效数据</h2>
            <p className="section-subtitle">试点完成后，指标将从真实事件和评测结果中生成；当前不展示模拟提升率。</p>
          </div>

          <div className="card-flat" style={{ padding: '28px', textAlign: 'center' }}>
            客户成效数据将在试点完成后，从真实事件与评测结果中生成并公开。
          </div>
        </div>
      </section>

      {/* Testimonial */}
      <section className="section section-alt">
        <div className="container">
          <div className="container-narrow">
            <div className="quote-card">
              <p className="quote-text">验收目标：每一项服务建议都能回到政策来源、企业事实和人工复核记录。</p>
              <div className="quote-author-role" style={{ textAlign: 'center', fontSize: '0.8125rem', color: 'var(--text-muted)' }}>
                衍策引擎AI 服务原则
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* CTA */}
      <section
        className="cta-section"
        style={{
          background: 'linear-gradient(135deg, #0d1b2a 0%, #1b2d44 50%, #0d1b2a 100%)',
        }}
      >
        <div className="container">
          <h2 className="cta-title">让你的园区服务更智能</h2>
          <p className="cta-subtitle">
            注册后可创建企业工作区；可用额度与付费能力以账户中的真实配置为准。
          </p>
          <div className="cta-actions">
            <Link
              href="/login?register=1"
              className="btn btn-lg"
              style={{ background: '#f97316', color: '#fff', borderColor: '#f97316', borderRadius: '12px' }}
            >
              免费注册
            </Link>
            <Link href="/pricing" className="btn btn-outline-white btn-lg">
              查看价格
            </Link>
          </div>
        </div>
      </section>
    </>
  );
}
