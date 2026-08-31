import Link from 'next/link';

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
              color: '#0ea5e9',
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
                基于企业画像和政策匹配引擎，为每家企业推荐最适用的政策资源，服务精准度提升 3 倍以上。
              </p>
            </div>
            <div className="card" style={{ borderTop: '3px solid #0ea5e9' }}>
              <div className="card-icon" style={{ background: '#f0f9ff', color: '#0ea5e9' }}>
                &#x26A1;
              </div>
              <h3 className="card-title">效率提升</h3>
              <p className="card-desc">
                从政策解读到材料生成全流程自动化，单次企业服务时间从平均 4 小时缩短至 30 分钟。
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
                      覆盖国家级、省级、市级和区级政策，实时更新，结构化存储。
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
                        background: i === 0 ? '#0d1b2a' : i === 1 ? '#1b2d44' : i === 2 ? '#0ea5e9' : i === 3 ? '#16a34a' : '#f97316',
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
            <span className="section-label">部署流程</span>
            <h2 className="section-title">从接入到上线，4 周完成</h2>
          </div>

          <div className="grid grid-4" style={{ gap: '20px' }}>
            {[
              { week: '第 1 周', title: '需求对接', desc: '了解园区业务需求、数据现状和服务目标', badge: 'badge-primary' },
              { week: '第 2 周', title: '数据接入', desc: '对接园区企业数据源，初始化政策知识库', badge: 'badge-green' },
              { week: '第 3 周', title: '系统部署', desc: '部署核心模块，配置匹配规则和权限体系', badge: 'badge-orange' },
              { week: '第 4 周', title: '培训上线', desc: '园区团队培训，试运行并正式上线', badge: 'badge-success' },
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
            <span className="section-label">客户成效</span>
            <h2 className="section-title">实际运营数据</h2>
          </div>

          <div className="grid grid-4" style={{ gap: '20px' }}>
            {[
              { value: '3x', label: '服务精准度提升' },
              { value: '87%', label: '企业政策覆盖率' },
              { value: '30min', label: '单次服务耗时' },
              { value: '95%', label: '园区团队满意度' },
            ].map((stat) => (
              <div key={stat.label} className="stat-card">
                <div className="stat-value">{stat.value}</div>
                <div className="stat-label">{stat.label}</div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Testimonial */}
      <section className="section section-alt">
        <div className="container">
          <div className="container-narrow">
            <div className="quote-card">
              <p className="quote-text">
                部署 Policy Agent 之后，我们的企业服务团队从每天只能服务 5 家企业，提升到可以同时服务 20 家企业。更重要的是，每一项服务建议都有据可查。
              </p>
              <div className="quote-author">
                <div className="quote-author-avatar">YD</div>
                <div>
                  <div className="quote-author-name">某园区运营总监</div>
                  <div className="quote-author-role">上海市徐汇区产业园区</div>
                </div>
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
            注册即享 3 次免费政策匹配报告，30 秒开通，无需信用卡。
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
