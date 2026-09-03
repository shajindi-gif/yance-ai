import Link from 'next/link';

export default function CompanyMatchPage() {
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
            SubsidyMatch
          </span>
          <h1>企业画像与政策匹配</h1>
          <p>
            自动构建园区企业多维度画像，智能匹配适用政策，让每一项服务决策都有据可依。
          </p>
        </div>
      </section>

      {/* Overview - Company Profile */}
      <section className="section">
        <div className="container">
          <div className="split">
            <div className="split-content">
              <span className="section-label">CompanyProfile</span>
              <h2 className="section-title mb-4">园区企业智能画像</h2>
              <p>
                CompanyProfile 模块自动整合企业工商注册、知识产权、财务数据、资质认证、行业分类等多维度信息，为每家园区企业构建完整的智能画像。
              </p>
              <p>
                基于画像数据，系统能够自动识别企业的发展阶段、行业定位和成长潜力，为精准服务提供数据基础。
              </p>
              <div className="mt-8">
                <Link href="/login?register=1" className="btn btn-primary" style={{ background: '#0ea5e9', borderColor: '#0ea5e9', borderRadius: '12px' }}>
                  查看企业画像 Demo
                </Link>
              </div>
            </div>
            <div className="split-visual">
              <div style={{ width: '100%' }}>
                <h4 style={{ marginBottom: '16px', textAlign: 'center' }}>企业画像示例</h4>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                  {[
                    { label: '基本信息', status: '已完善', badge: 'badge-success' },
                    { label: '知识产权', status: '12 项专利', badge: 'badge-success' },
                    { label: '资质认证', status: '高新认定', badge: 'badge-warning' },
                    { label: '财务数据', status: '待更新', badge: 'badge-orange' },
                    { label: '行业标签', status: 'AI/数字经济', badge: 'badge-primary' },
                  ].map((item) => (
                    <div
                      key={item.label}
                      className="card-flat"
                      style={{
                        padding: '12px 16px',
                        display: 'flex',
                        justifyContent: 'space-between',
                        alignItems: 'center',
                      }}
                    >
                      <span style={{ fontWeight: 600, fontSize: '0.875rem' }}>{item.label}</span>
                      <span className={`badge ${item.badge}`}>{item.status}</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Data Dimensions */}
      <section className="section section-alt">
        <div className="container">
          <div className="section-header">
            <span className="section-label">画像维度</span>
            <h2 className="section-title">多维度企业数据整合</h2>
            <p className="section-subtitle">
              从多个数据源自动获取和整合企业信息，构建 360 度全方位画像。
            </p>
          </div>

          <div className="grid grid-3" style={{ gap: '24px' }}>
            {[
              { icon: '\u{1F4C4}', title: '工商与法务', desc: '注册资本、经营范围、股东信息、变更记录、关联公司等基础工商数据。', accent: '' },
              { icon: '\u{1F4A1}', title: '知识产权', desc: '发明专利、实用新型、软件著作权、商标等知识产权的数量、类别和时间分布。', accent: 'green' },
              { icon: '\u{1F4B0}', title: '财务指标', desc: '营业收入、研发投入、纳税金额、利润等核心财务数据。', accent: 'orange' },
              { icon: '\u{1F3C6}', title: '资质认证', desc: '高新技术企业、专精特新、科技型中小企业等资质认定状态和有效期。', accent: '' },
              { icon: '\u{1F3ED}', title: '行业分类', desc: '基于经营范围和主营产品的行业标签自动分类，支持多标签和细分领域。', accent: 'green' },
              { icon: '\u{1F4C8}', title: '成长性评估', desc: '基于营收增长、知识产权增长、人员增长等指标的企业成长性综合评估。', accent: 'orange' },
            ].map((dim) => (
              <div
                key={dim.title}
                className="card"
                style={{
                  borderTop: `3px solid ${dim.accent === 'green' ? '#16a34a' : dim.accent === 'orange' ? '#f97316' : '#0ea5e9'}`,
                }}
              >
                <div
                  className="card-icon"
                  style={{
                    background: dim.accent === 'green' ? '#f0fdf4' : dim.accent === 'orange' ? '#fff7ed' : '#f0f9ff',
                    color: dim.accent === 'green' ? '#16a34a' : dim.accent === 'orange' ? '#f97316' : '#0ea5e9',
                  }}
                >
                  {dim.icon}
                </div>
                <h3 className="card-title">{dim.title}</h3>
                <p className="card-desc">{dim.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Matching Engine */}
      <section className="section">
        <div className="container">
          <div className="split">
            <div className="split-content">
              <span className="section-label">SubsidyMatch</span>
              <h2 className="section-title mb-4">政策资源智能匹配引擎</h2>
              <p>
                将企业画像与政策条件进行智能匹配，系统自动计算每个政策项目与企业的适配度，并按优先级排列。
              </p>
              <p>
                匹配结果包含适配度评分、关键条件对比、材料缺口分析和申报时间建议，帮助园区快速确定服务优先级。
              </p>
              <div className="mt-8">
                <Link href="/login?register=1" className="btn btn-primary" style={{ background: '#f97316', borderColor: '#f97316', borderRadius: '12px' }}>
                  查看匹配示例
                </Link>
              </div>
            </div>
            <div className="split-visual">
              <div style={{ width: '100%' }}>
                <h4 style={{ marginBottom: '16px', textAlign: 'center' }}>匹配结果示例</h4>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                  {[
                    { name: '高新技术企业认定', score: 92, color: '#16a34a' },
                    { name: '专精特新中小企业', score: 85, color: '#0ea5e9' },
                    { name: '科技型中小企业评价', score: 88, color: '#0ea5e9' },
                    { name: '研发费用加计扣除', score: 78, color: '#f97316' },
                  ].map((match) => (
                    <div key={match.name} className="card-flat" style={{ padding: '16px 20px' }}>
                      <div
                        style={{
                          display: 'flex',
                          justifyContent: 'space-between',
                          marginBottom: '8px',
                        }}
                      >
                        <span style={{ fontWeight: 600, fontSize: '0.875rem' }}>{match.name}</span>
                        <span
                          className="badge"
                          style={{
                            background: `${match.color}15`,
                            color: match.color,
                            fontWeight: 700,
                          }}
                        >
                          {match.score}% 匹配
                        </span>
                      </div>
                      <div
                        style={{
                          height: '6px',
                          background: 'var(--bg-alt)',
                          borderRadius: '3px',
                        }}
                      >
                        <div
                          style={{
                            width: `${match.score}%`,
                            height: '100%',
                            background: match.color,
                            borderRadius: '3px',
                            transition: 'width 0.6s ease',
                          }}
                        />
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Sample Output */}
      <section className="section section-alt">
        <div className="container">
          <div className="section-header">
            <span className="section-label">DEMO / 虚构数据</span>
            <h2 className="section-title">企业政策匹配报告界面样例</h2>
          </div>

          <div className="dashboard-preview">
            <div className="dashboard-header">
              <span className="dashboard-header-title">企业：上海XX科技有限公司</span>
              <span className="badge badge-primary">匹配完成</span>
            </div>

            <div className="grid grid-4" style={{ gap: '16px', marginBottom: '24px' }}>
              {[
                { value: '15', label: '匹配政策数', color: '' },
                { value: '8', label: '高适配度 (>80%)', color: 'green' },
                { value: '4', label: '材料缺口项', color: 'orange' },
                { value: '3', label: '可立即申报', color: '' },
              ].map((stat) => (
                <div key={stat.label} className="stat-card">
                  <div
                    className={`stat-value${stat.color === 'green' ? ' stat-value-green' : stat.color === 'orange' ? ' stat-value-orange' : ''}`}
                  >
                    {stat.value}
                  </div>
                  <div className="stat-label">{stat.label}</div>
                </div>
              ))}
            </div>

            <div className="table-wrapper">
              <table className="table">
                <thead>
                  <tr>
                    <th>政策项目</th>
                    <th>适配度</th>
                    <th>级别</th>
                    <th>截止日期</th>
                    <th>状态</th>
                  </tr>
                </thead>
                <tbody>
                  <tr>
                    <td style={{ fontWeight: 600 }}>高新技术企业认定</td>
                    <td>92%</td>
                    <td>国家级</td>
                    <td>2025-06-30</td>
                    <td><span className="badge badge-success">可申报</span></td>
                  </tr>
                  <tr>
                    <td style={{ fontWeight: 600 }}>专精特新中小企业</td>
                    <td>85%</td>
                    <td>市级</td>
                    <td>2025-08-15</td>
                    <td><span className="badge badge-success">可申报</span></td>
                  </tr>
                  <tr>
                    <td style={{ fontWeight: 600 }}>科技型中小企业评价</td>
                    <td>88%</td>
                    <td>国家级</td>
                    <td>2025-12-31</td>
                    <td><span className="badge badge-success">可申报</span></td>
                  </tr>
                  <tr>
                    <td style={{ fontWeight: 600 }}>研发费用加计扣除</td>
                    <td>78%</td>
                    <td>国家级</td>
                    <td>2025-05-31</td>
                    <td><span className="badge badge-warning">需补充材料</span></td>
                  </tr>
                </tbody>
              </table>
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
          <h2 className="cta-title">为你的企业生成政策匹配报告</h2>
          <p className="cta-subtitle">
            注册后创建企业画像并运行扫描；结果数量、耗时、金额与截止日期均以真实来源和运行记录为准。
          </p>
          <div className="cta-actions">
            <Link
              href="/login?register=1"
              className="btn btn-lg"
              style={{ background: '#f97316', color: '#fff', borderColor: '#f97316', borderRadius: '12px' }}
            >
              免费生成报告
            </Link>
            <Link href="/pricing" className="btn btn-outline-white btn-lg">
              了解价格
            </Link>
          </div>
        </div>
      </section>
    </>
  );
}
