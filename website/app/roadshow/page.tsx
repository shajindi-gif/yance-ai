import Link from 'next/link';

export default function RoadshowPage() {
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
            路演与试点
          </span>
          <h1>徐汇试点与路演计划</h1>
          <p>
            了解 Policy Agent 的推广路线和试点合作机会，成为智能园区服务的先行者。
          </p>
        </div>
      </section>

      {/* Pilot Overview */}
      <section className="section">
        <div className="container">
          <div className="split">
            <div className="split-content">
              <span className="section-label">徐汇试点</span>
              <h2 className="section-title mb-4">徐汇园区试点合作</h2>
              <p>
                我们正在与上海市徐汇区的产业园区合作，开展 Policy Agent 的首批试点部署。试点园区将享受优先部署、定制支持和优惠价格。
              </p>
              <p>
                试点合作面向徐汇区各类产业园区、孵化器和产业服务机构，通过真实业务场景验证产品价值，共同推动园区服务智能化升级。
              </p>
              <div className="mt-8">
                <Link
                  href="/login?register=1"
                  className="btn btn-primary"
                  style={{ background: '#f97316', borderColor: '#f97316', borderRadius: '12px' }}
                >
                  申请试点合作
                </Link>
              </div>
            </div>
            <div>
              <div className="pilot-card">
                <h3>试点权益</h3>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '16px', marginTop: '16px' }}>
                  {[
                    { icon: '\u{26A1}', title: '优先部署', desc: '试点园区优先安排部署，最快 2 周上线' },
                    { icon: '\u{1F464}', title: '专属支持', desc: '配备专属实施团队和客户成功经理' },
                    { icon: '\u{1F4B0}', title: '优惠价格', desc: '试点期间享受特别优惠价格方案' },
                    { icon: '\u{1F91D}', title: '产品共建', desc: '深度参与产品需求定义和功能迭代' },
                  ].map((benefit) => (
                    <div
                      key={benefit.title}
                      style={{
                        display: 'flex',
                        gap: '12px',
                        padding: '12px',
                        background: 'rgba(14,165,233,0.08)',
                        borderRadius: '12px',
                      }}
                    >
                      <span style={{ fontSize: '1.5rem' }}>{benefit.icon}</span>
                      <div>
                        <h4 style={{ fontSize: '0.9375rem', fontWeight: 600, color: 'var(--text)' }}>
                          {benefit.title}
                        </h4>
                        <p style={{ fontSize: '0.8125rem', color: 'var(--text-secondary)' }}>
                          {benefit.desc}
                        </p>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Pilot Timeline */}
      <section className="section section-alt">
        <div className="container">
          <div className="section-header">
            <span className="section-label">试点路线</span>
            <h2 className="section-title">3 个月试点时间表</h2>
          </div>

          <div className="container-narrow">
            <div className="timeline">
              <div className="timeline-item">
                <h3 className="timeline-item-title">第 1-2 周：需求对接与数据准备</h3>
                <p className="timeline-item-desc">
                  深入了解园区业务需求，对接企业数据源，初始化政策知识库。完成系统配置和环境搭建。
                </p>
              </div>
              <div className="timeline-item">
                <h3 className="timeline-item-title">第 3-4 周：基础模块部署</h3>
                <p className="timeline-item-desc">
                  部署 PolicyCopilot 和 CompanyProfile 模块，覆盖核心企业的政策问答和画像服务。园区团队培训。
                </p>
              </div>
              <div className="timeline-item">
                <h3 className="timeline-item-title">第 5-8 周：智能匹配上线</h3>
                <p className="timeline-item-desc">
                  接入 SubsidyMatch 和 BriefMaker 模块，实现企业-政策自动匹配和材料清单自动生成。收集反馈持续优化。
                </p>
              </div>
              <div className="timeline-item">
                <h3 className="timeline-item-title">第 9-12 周：全面运营</h3>
                <p className="timeline-item-desc">
                  上线 ParkOps 工作台，整合所有模块。评估试点成果，制定推广计划。
                </p>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* KPI Targets */}
      <section className="section">
        <div className="container">
          <div className="section-header">
            <span className="section-label">试点目标</span>
            <h2 className="section-title">试点 KPI 目标</h2>
          </div>

          <div className="grid grid-4" style={{ gap: '20px' }}>
            {[
              { value: '200+', label: '覆盖企业数', desc: '试点园区核心企业' },
              { value: '85%+', label: '匹配准确率', desc: '政策匹配精确度' },
              { value: '<30min', label: '服务响应时间', desc: '单次企业服务耗时' },
              { value: '3x', label: '效率提升倍数', desc: '对比人工服务效率' },
            ].map((kpi) => (
              <div key={kpi.label} className="stat-card" style={{ padding: '32px 20px' }}>
                <div className="stat-value" style={{ color: '#0ea5e9' }}>
                  {kpi.value}
                </div>
                <div className="stat-label" style={{ fontWeight: 600, color: 'var(--text)' }}>
                  {kpi.label}
                </div>
                <p style={{ fontSize: '0.75rem', color: 'var(--text-tertiary)', marginTop: '4px' }}>
                  {kpi.desc}
                </p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Roadshow Timeline */}
      <section className="section section-alt">
        <div className="container">
          <div className="section-header">
            <span className="section-label">路演路线</span>
            <h2 className="section-title">2025 路演计划</h2>
            <p className="section-subtitle">
              我们将在全国多个城市开展园区智能服务路演活动，欢迎预约参加。
            </p>
          </div>

          <div className="container-narrow">
            <div className="timeline">
              {[
                { city: '上海站 - 徐汇区', desc: '徐汇区产业园区专场，面向漕河泾、徐汇滨江等园区运营团队。重点演示政策问答和企业画像模块。', status: '已开放报名', badge: 'badge-success' },
                { city: '上海站 - 张江', desc: '张江科学城专场，面向生物医药、集成电路等高科技产业园区。重点演示行业政策匹配和材料生成。', status: '即将开放', badge: 'badge-primary' },
                { city: '杭州站', desc: '杭州高新区和数字经济产业园专场。聚焦互联网和数字经济领域政策服务。', status: '规划中', badge: 'badge-orange' },
                { city: '深圳站', desc: '深圳南山和前海片区专场。面向科技创新型园区和深港合作区。', status: '规划中', badge: 'badge-orange' },
                { city: '北京站', desc: '中关村和亦庄开发区专场。面向国家级高新区和经开区。', status: '规划中', badge: 'badge-orange' },
              ].map((event) => (
                <div key={event.city} className="timeline-item">
                  <h3 className="timeline-item-title">{event.city}</h3>
                  <p className="timeline-item-desc">{event.desc}</p>
                  <div style={{ marginTop: '8px' }}>
                    <span className={`badge ${event.badge}`}>{event.status}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* Partnership Models */}
      <section className="section">
        <div className="container">
          <div className="section-header">
            <span className="section-label">合作模式</span>
            <h2 className="section-title">灵活的合作模式</h2>
          </div>

          <div className="grid grid-3" style={{ gap: '24px' }}>
            <div className="card" style={{ borderTop: '3px solid #0ea5e9' }}>
              <div className="card-icon" style={{ background: '#f0f9ff', color: '#0ea5e9' }}>
                &#x1F91D;
              </div>
              <h3 className="card-title">试点合作</h3>
              <p className="card-desc">
                成为首批试点园区，享受优先部署和优惠价格，共同验证和优化产品。适合愿意深度参与产品共建的园区。
              </p>
            </div>
            <div className="card" style={{ borderTop: '3px solid #16a34a' }}>
              <div className="card-icon" style={{ background: '#f0fdf4', color: '#16a34a' }}>
                &#x1F3EB;
              </div>
              <h3 className="card-title">渠道合作</h3>
              <p className="card-desc">
                面向园区服务商、咨询机构和行业协会，成为 Policy Agent 的渠道合作伙伴，共同推广智能政策服务。
              </p>
            </div>
            <div className="card" style={{ borderTop: '3px solid #f97316' }}>
              <div className="card-icon" style={{ background: '#fff7ed', color: '#f97316' }}>
                &#x1F4E1;
              </div>
              <h3 className="card-title">技术合作</h3>
              <p className="card-desc">
                面向政务平台和大型系统集成商，提供 API 和 SDK 集成能力，将政策智能服务嵌入现有业务系统。
              </p>
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
          <h2 className="cta-title">加入 Policy Agent 园区智能服务生态</h2>
          <p className="cta-subtitle">
            无论你是园区运营方、服务商还是技术集成商，我们都欢迎你的合作意向。
          </p>
          <div className="cta-actions">
            <Link
              href="/login?register=1"
              className="btn btn-lg"
              style={{ background: '#f97316', color: '#fff', borderColor: '#f97316', borderRadius: '12px' }}
            >
              预约演示
            </Link>
            <a href="mailto:contact@yance.ai" className="btn btn-outline-white btn-lg">
              联系合作
            </a>
          </div>
        </div>
      </section>
    </>
  );
}
