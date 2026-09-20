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
              background: 'rgba(18,106,154,0.16)',
              color: 'var(--teal)',
              marginBottom: '16px',
            }}
          >
            政策知识库
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
            <span className="section-label">真实数据原则</span>
            <h2 className="section-title">数据规模尚未公开</h2>
            <p className="section-subtitle">
              政策数量、覆盖城市、更新频率和结构化率必须由数据库与评测系统计算；当前不展示占位数字。
            </p>
          </div>

          <div className="card-flat" style={{ padding: '24px 28px', display: 'flex', flexWrap: 'wrap', gap: '8px 28px', alignItems: 'center', justifyContent: 'center', fontSize: '0.875rem', color: 'var(--text-secondary)' }}>
            <span>政策文件总数 · 待统计</span>
            <span>覆盖城市 · 待统计</span>
            <span>更新频率 · 待统计</span>
            <span>结构化覆盖率 · 待评测</span>
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
            <div className="card" style={{ borderTop: '3px solid #126a9a' }}>
              <div className="card-icon" style={{ background: '#f0f9ff', color: 'var(--teal)' }}>
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
              <span className="dashboard-header-title">DEMO：政策结构化数据模型</span>
              <span className="badge badge-success">虚构示例</span>
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
                    示例政策 A（非真实政策文件）
                  </p>
                  <p style={{ marginTop: '12px', color: 'var(--text-secondary)' }}>
                    本段仅用于演示标题、发布机构、适用条件、日期与权益字段如何被结构化。
                  </p>
                </div>
              </div>
              <div>
                <h4 style={{ marginBottom: '16px', color: 'var(--text-secondary)', fontSize: '0.875rem' }}>
                  结构化输出
                </h4>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                  {[
                    { label: '政策名称', value: '示例政策 A' },
                    { label: '发布机构', value: '示例发布机构' },
                    { label: '适用条件', value: '示例条件 1 / 示例条件 2' },
                    { label: '申报截止', value: '待来源解析' },
                    { label: '补贴标准', value: '待来源解析' },
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
                DEMO：无真实来源时的回答边界
              </h3>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                {[
                  {
                    q: '某项认定需要多少项知识产权？',
                    a: '当前示例没有政策原文，系统必须返回 Need More Information，而不是猜测数量。',
                    src: 'No source in demo',
                  },
                  {
                    q: '某地区有哪些企业补贴？',
                    a: '系统需要先检索有效期和适用地区匹配的来源，再显示条款、发布日期与置信度。',
                    src: 'No source in demo',
                  },
                ].map((qa) => (
                  <div
                    key={qa.q}
                    style={{
                      background: 'var(--bg-alt)',
                      padding: '20px',
                      borderRadius: '12px',
                      borderLeft: '3px solid #126a9a',
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
                        color: 'var(--teal)',
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
