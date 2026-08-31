import Link from 'next/link';

export default function PolicyKnowledgeBasePage() {
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
            PolicyCopilot
          </span>
          <h1>政策知识库</h1>
          <p>
            结构化存储和智能检索各级政府政策文件，为园区服务提供可靠的政策数据基础。
          </p>
        </div>
      </section>

      {/* Overview Stats */}
      <section className="section">
        <div className="container">
          <div className="section-header">
            <span className="section-label">数据规模</span>
            <h2 className="section-title">智能政策知识引擎</h2>
            <p className="section-subtitle">
              覆盖国家级、省级、市级和区级政策文件，通过结构化处理和语义索引，让每一条政策都可搜索、可问答、可引用。
            </p>
          </div>

          <div className="grid grid-4" style={{ gap: '20px' }}>
            {[
              { value: '10,000+', label: '政策文件总数', color: '' },
              { value: '50+', label: '覆盖城市', color: 'green' },
              { value: '每日', label: '更新频率', color: 'orange' },
              { value: '98%', label: '结构化覆盖率', color: '' },
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
        </div>
      </section>

      {/* Policy Categories */}
      <section className="section section-alt">
        <div className="container">
          <div className="section-header">
            <span className="section-label">分类体系</span>
            <h2 className="section-title">多维度政策分类</h2>
          </div>

          <div className="grid grid-3" style={{ gap: '24px' }}>
            <div className="card" style={{ borderTop: '3px solid #0ea5e9' }}>
              <div className="card-icon" style={{ background: '#f0f9ff', color: '#0ea5e9' }}>
                &#x1F3DB;&#xFE0F;
              </div>
              <h3 className="card-title">按行政级别</h3>
              <ul className="module-card-features">
                <li>国家级政策 (科技部、工信部等)</li>
                <li>省级政策 (省/直辖市)</li>
                <li>市级政策 (地级市)</li>
                <li>区级政策 (开发区/高新区)</li>
              </ul>
            </div>
            <div className="card" style={{ borderTop: '3px solid #16a34a' }}>
              <div className="card-icon" style={{ background: '#f0fdf4', color: '#16a34a' }}>
                &#x1F3ED;
              </div>
              <h3 className="card-title">按行业领域</h3>
              <ul className="module-card-features">
                <li>人工智能与数字经济</li>
                <li>生物医药与大健康</li>
                <li>集成电路与半导体</li>
                <li>新能源与新材料</li>
                <li>先进制造与智能制造</li>
              </ul>
            </div>
            <div className="card" style={{ borderTop: '3px solid #f97316' }}>
              <div className="card-icon" style={{ background: '#fff7ed', color: '#f97316' }}>
                &#x1F4CB;
              </div>
              <h3 className="card-title">按政策类型</h3>
              <ul className="module-card-features">
                <li>企业资质认定 (高企、专精特新)</li>
                <li>资金补贴与奖励</li>
                <li>税收优惠</li>
                <li>人才政策</li>
                <li>场地与租金补贴</li>
              </ul>
            </div>
          </div>
        </div>
      </section>

      {/* Knowledge Structure */}
      <section className="section">
        <div className="container">
          <div className="section-header">
            <span className="section-label">数据结构</span>
            <h2 className="section-title">政策结构化处理</h2>
            <p className="section-subtitle">
              将原始政策文件转化为结构化的知识单元，支持精确检索和智能匹配。
            </p>
          </div>

          <div className="dashboard-preview">
            <div className="dashboard-header">
              <span className="dashboard-header-title">政策结构化示例</span>
              <span className="badge badge-success">已结构化</span>
            </div>

            <div className="grid grid-2" style={{ gap: '24px' }}>
              <div>
                <h4 style={{ marginBottom: '16px', color: 'var(--text-secondary)', fontSize: '0.875rem' }}>
                  原始政策文本
                </h4>
                <div
                  className="card-flat"
                  style={{ background: 'var(--bg-alt)', fontSize: '0.875rem', lineHeight: 1.8 }}
                >
                  <p style={{ color: 'var(--text)', fontWeight: 600 }}>
                    关于组织开展2024年度高新技术企业认定工作的通知
                  </p>
                  <p style={{ marginTop: '12px', color: 'var(--text-secondary)' }}>
                    各区科技行政部门、各有关单位：根据《高新技术企业认定管理办法》(国科发火〔2016〕32号)...
                    申报企业须是在本市行政区域内注册一年以上的居民企业...
                    企业近三个会计年度的研究开发费用总额占同期销售收入总额的比例符合要求...
                  </p>
                </div>
              </div>
              <div>
                <h4 style={{ marginBottom: '16px', color: 'var(--text-secondary)', fontSize: '0.875rem' }}>
                  结构化输出
                </h4>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                  {[
                    { label: '政策名称', value: '2024年度高新技术企业认定' },
                    { label: '发布机构', value: '上海市科学技术委员会' },
                    { label: '适用条件', value: '注册1年以上 / 研发费用占比达标 / IP数量要求' },
                    { label: '申报截止', value: '2025-06-30' },
                    { label: '补贴标准', value: '首次认定奖励 20 万元' },
                  ].map((field) => (
                    <div key={field.label} className="card-flat" style={{ padding: '10px 16px' }}>
                      <span
                        style={{
                          fontWeight: 600,
                          fontSize: '0.7rem',
                          color: 'var(--text-tertiary)',
                          textTransform: 'uppercase',
                          letterSpacing: '0.05em',
                        }}
                      >
                        {field.label}
                      </span>
                      <p style={{ color: 'var(--text)', fontSize: '0.875rem', marginTop: '2px' }}>
                        {field.value}
                      </p>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* AI Q&A Features */}
      <section className="section section-alt">
        <div className="container">
          <div className="section-header">
            <span className="section-label">智能问答</span>
            <h2 className="section-title">政策问答与引用溯源</h2>
          </div>

          <div className="grid grid-2" style={{ gap: '32px' }}>
            <div className="card" style={{ padding: '32px' }}>
              <h3 className="card-title" style={{ marginBottom: '24px' }}>
                示例问答
              </h3>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                {[
                  {
                    q: '高新技术企业认定需要多少项知识产权？',
                    a: '根据《高新技术企业认定管理工作指引》，企业通过自主研发、受让、受赠、并购等方式获得知识产权。I类知识产权1项以上或II类知识产权5项以上。',
                    src: '《高新技术企业认定管理工作指引》第三章',
                  },
                  {
                    q: '上海市对专精特新企业有哪些补贴？',
                    a: '上海市对专精特新企业主要支持政策包括：1) 专项资金奖励；2) 融资支持；3) 人才引进；4) 市场开拓等。',
                    src: '《上海市专精特新企业发展条例》第四章',
                  },
                ].map((qa) => (
                  <div
                    key={qa.q}
                    style={{
                      background: 'var(--bg-alt)',
                      padding: '20px',
                      borderRadius: '12px',
                      borderLeft: '3px solid #0ea5e9',
                    }}
                  >
                    <p
                      style={{
                        fontSize: '0.875rem',
                        fontWeight: 600,
                        color: 'var(--text)',
                        marginBottom: '8px',
                      }}
                    >
                      Q: {qa.q}
                    </p>
                    <p style={{ fontSize: '0.875rem', color: 'var(--text-secondary)' }}>
                      A: {qa.a}
                    </p>
                    <p
                      style={{
                        fontSize: '0.75rem',
                        color: '#0ea5e9',
                        marginTop: '8px',
                        fontWeight: 500,
                      }}
                    >
                      来源：{qa.src}
                    </p>
                  </div>
                ))}
              </div>
            </div>

            <div>
              <div className="feature-list">
                {[
                  { icon: '\u{1F4AC}', title: '自然语言问答', desc: '用自然语言提问，无需记忆政策编号和术语。' },
                  { icon: '\u{1F517}', title: '精确引用溯源', desc: '每个回答标注来源政策文件和具体条款。' },
                  { icon: '\u{1F504}', title: '多轮对话', desc: '支持上下文连续追问和条件细化。' },
                  { icon: '\u{1F4CA}', title: '多政策对比', desc: '支持多个政策的条件对比和差异分析。' },
                  { icon: '\u{1F6E1}\u{FE0F}', title: '人工复核支持', desc: '关键输出支持人工复核和结果修正。' },
                ].map((feat) => (
                  <div key={feat.title} className="feature-item">
                    <div className="feature-item-icon">{feat.icon}</div>
                    <div>
                      <h4 className="feature-item-title">{feat.title}</h4>
                      <p className="feature-item-desc">{feat.desc}</p>
                    </div>
                  </div>
                ))}
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
          <h2 className="cta-title">注册体验智能政策知识库</h2>
          <p className="cta-subtitle">
            注册后即可使用自然语言政策问答和知识检索，发现你的企业能申报哪些政策。
          </p>
          <div className="cta-actions">
            <Link
              href="/login?register=1"
              className="btn btn-lg"
              style={{ background: '#f97316', color: '#fff', borderColor: '#f97316', borderRadius: '12px' }}
            >
              免费注册
            </Link>
            <Link href="/parks" className="btn btn-outline-white btn-lg">
              了解园区方案
            </Link>
          </div>
        </div>
      </section>
    </>
  );
}
