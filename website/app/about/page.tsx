import Link from 'next/link';
import Image from 'next/image';

export default function AboutPage() {
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
            关于衍策引擎
          </span>
          <h1>关于我们</h1>
          <p>
            上海衍策引擎人工智能科技有限公司 &mdash; 用 AI 重新定义园区企业服务。
          </p>
        </div>
      </section>

      {/* Company Story */}
      <section className="section">
        <div className="container">
          <div className="split">
            <div className="split-content">
              <span className="section-label">我们的故事</span>
              <h2 className="section-title mb-4">让园区服务更智能</h2>
              <p>
                衍策引擎成立于上海，专注于为产业园区和科技服务机构提供 AI 驱动的政策服务解决方案。
              </p>
              <p>
                我们发现，园区企业服务的核心痛点不在于政策数量不够，而在于信息不对称：政策文件复杂难懂，企业画像分散割裂，申报流程繁琐低效。园区工作人员凭经验和手工操作来服务企业，覆盖面和精准度都受到限制。
              </p>
              <p>
                衍策引擎的使命是：通过 AI 技术打通政策数据和企业数据的壁垒，让每一个园区都能为入驻企业提供精准、高效、可追溯的政策服务。
              </p>
            </div>
            <div className="split-visual">
              <div style={{ textAlign: 'center' }}>
                <Image
                  src="/logo.png"
                  alt="衍策引擎AI"
                  width={120}
                  height={120}
                  style={{ borderRadius: '24px', margin: '0 auto 24px' }}
                />
                <h3 style={{ marginBottom: '8px' }}>衍策引擎AI</h3>
                <p style={{ color: 'var(--text-secondary)', fontSize: '0.875rem' }}>
                  上海衍策引擎人工智能科技有限公司
                </p>
                <div
                  style={{
                    marginTop: '16px',
                    display: 'flex',
                    gap: '8px',
                    justifyContent: 'center',
                    flexWrap: 'wrap',
                  }}
                >
                  {['AI', '园区服务', '政策智能'].map((tag) => (
                    <span
                      key={tag}
                      style={{
                        padding: '4px 12px',
                        borderRadius: '9999px',
                        fontSize: '0.75rem',
                        fontWeight: 600,
                        background: 'var(--bg-alt)',
                        color: 'var(--text-secondary)',
                        border: '1px solid var(--border)',
                      }}
                    >
                      {tag}
                    </span>
                  ))}
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Values */}
      <section className="section section-alt">
        <div className="container">
          <div className="section-header">
            <span className="section-label">核心价值观</span>
            <h2 className="section-title">我们相信什么</h2>
          </div>

          <div className="grid grid-4" style={{ gap: '24px' }}>
            {[
              {
                icon: '\u{1F3AF}',
                title: '精准服务',
                desc: '每一条政策建议都基于数据驱动的精准匹配，而非经验猜测。',
                bg: '#f0f9ff',
                color: '#0ea5e9',
              },
              {
                icon: '\u{1F50D}',
                title: '透明可追溯',
                desc: '所有 AI 输出都附带数据来源和政策引用，让服务结果可复核、可解释。',
                bg: '#f0fdf4',
                color: '#16a34a',
              },
              {
                icon: '\u{1F4AA}',
                title: '务实落地',
                desc: '产品设计以园区实际工作场景为核心，追求真正的效率提升，而非技术噱头。',
                bg: '#fff7ed',
                color: '#f97316',
              },
              {
                icon: '\u{1F91D}',
                title: '生态共建',
                desc: '与园区、服务商和政务平台共同构建智能服务生态，实现多方共赢。',
                bg: '#f0f9ff',
                color: '#0ea5e9',
              },
            ].map((val) => (
              <div key={val.title} className="value-card">
                <div
                  className="value-card-icon"
                  style={{ background: val.bg, color: val.color }}
                >
                  {val.icon}
                </div>
                <h3 className="card-title">{val.title}</h3>
                <p className="card-desc">{val.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Technology */}
      <section className="section">
        <div className="container">
          <div className="section-header">
            <span className="section-label">技术实力</span>
            <h2 className="section-title">核心技术能力</h2>
          </div>

          <div className="grid grid-2" style={{ gap: '32px' }}>
            <div className="card" style={{ padding: '32px', borderTop: '3px solid #0ea5e9' }}>
              <div className="card-icon" style={{ background: '#f0f9ff', color: '#0ea5e9' }}>
                &#x1F9E0;
              </div>
              <h3 className="card-title">政策语义理解引擎</h3>
              <p className="card-desc" style={{ marginBottom: '20px' }}>
                基于大语言模型和领域微调，深度理解政策文本的语义结构，精确提取适用条件、申报要求、资金标准等关键信息。
              </p>
              <ul className="module-card-features">
                <li>政策文本结构化解析</li>
                <li>条件要素精确提取</li>
                <li>多政策语义关联分析</li>
                <li>时效性自动追踪</li>
              </ul>
            </div>
            <div className="card" style={{ padding: '32px', borderTop: '3px solid #16a34a' }}>
              <div className="card-icon" style={{ background: '#f0fdf4', color: '#16a34a' }}>
                &#x2699;&#xFE0F;
              </div>
              <h3 className="card-title">企业-政策匹配算法</h3>
              <p className="card-desc" style={{ marginBottom: '20px' }}>
                融合规则引擎和机器学习模型，将企业画像与政策条件进行多维度匹配，计算精准适配度评分。
              </p>
              <ul className="module-card-features">
                <li>多维度条件匹配</li>
                <li>动态权重调整</li>
                <li>缺口分析与补全路径</li>
                <li>时间窗口优化</li>
              </ul>
            </div>
          </div>
        </div>
      </section>

      {/* Team */}
      <section className="section section-alt">
        <div className="container">
          <div className="section-header">
            <span className="section-label">团队</span>
            <h2 className="section-title">我们的团队</h2>
            <p className="section-subtitle">
              来自 AI、企业服务、产业园区运营等领域的资深从业者，兼具技术深度和行业理解。
            </p>
          </div>

          <div className="grid grid-3" style={{ gap: '24px' }}>
            {[
              {
                initials: 'AI',
                title: 'AI 与算法团队',
                desc: '自然语言处理、知识图谱和推荐系统领域的研发工程师，负责核心算法和产品智能化能力。',
                bg: '#f0f9ff',
                color: '#0ea5e9',
              },
              {
                initials: 'PD',
                title: '产品与设计团队',
                desc: '深耕企业服务和 SaaS 产品领域的产品经理和设计师，以用户场景驱动产品设计。',
                bg: '#f0fdf4',
                color: '#16a34a',
              },
              {
                initials: 'BD',
                title: '行业与客户团队',
                desc: '来自产业园区运营和政策服务领域的行业专家，深入理解客户需求并推动落地实施。',
                bg: '#fff7ed',
                color: '#f97316',
              },
            ].map((team) => (
              <div key={team.initials} className="card" style={{ textAlign: 'center', padding: '32px' }}>
                <div
                  style={{
                    width: '72px',
                    height: '72px',
                    margin: '0 auto 16px',
                    background: team.bg,
                    borderRadius: '50%',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    fontSize: '1.5rem',
                    fontWeight: 800,
                    color: team.color,
                  }}
                >
                  {team.initials}
                </div>
                <h4 className="card-title">{team.title}</h4>
                <p className="card-desc">{team.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Milestones */}
      <section className="section">
        <div className="container">
          <div className="section-header">
            <span className="section-label">发展历程</span>
            <h2 className="section-title">关键里程碑</h2>
          </div>

          <div className="container-narrow">
            <div className="timeline">
              {[
                { title: '公司成立', desc: '上海衍策引擎人工智能科技有限公司在上海注册成立，确定园区智能政策服务方向。' },
                { title: '产品 V1.0 发布', desc: 'Policy Agent 核心模块开发完成，包括 PolicyCopilot 和 CompanyProfile。' },
                { title: '徐汇试点启动', desc: '与上海徐汇区产业园区签约首批试点合作，开始在真实场景中验证产品价值。' },
                { title: '全模块上线', desc: '五大核心模块全部上线，形成完整的园区智能政策服务产品体系。' },
              ].map((milestone) => (
                <div key={milestone.title} className="timeline-item">
                  <h3 className="timeline-item-title">{milestone.title}</h3>
                  <p className="timeline-item-desc">{milestone.desc}</p>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* Contact */}
      <section className="section section-alt">
        <div className="container">
          <div className="section-header">
            <span className="section-label">联系我们</span>
            <h2 className="section-title">与我们取得联系</h2>
          </div>

          <div className="grid grid-3" style={{ gap: '24px' }}>
            <div className="card" style={{ textAlign: 'center', padding: '32px' }}>
              <div className="card-icon" style={{ margin: '0 auto 16px', background: '#f0f9ff', color: '#0ea5e9' }}>
                &#x1F4E7;
              </div>
              <h4 className="card-title">邮件联系</h4>
              <p className="card-desc">
                <a href="mailto:contact@yance.ai">contact@yance.ai</a>
              </p>
            </div>
            <div className="card" style={{ textAlign: 'center', padding: '32px' }}>
              <div className="card-icon" style={{ margin: '0 auto 16px', background: '#f0fdf4', color: '#16a34a' }}>
                &#x1F3E2;
              </div>
              <h4 className="card-title">公司地址</h4>
              <p className="card-desc">上海市徐汇区</p>
            </div>
            <div className="card" style={{ textAlign: 'center', padding: '32px' }}>
              <div className="card-icon" style={{ margin: '0 auto 16px', background: '#fff7ed', color: '#f97316' }}>
                &#x1F310;
              </div>
              <h4 className="card-title">官方网站</h4>
              <p className="card-desc">
                <a href="https://yance.ai" target="_blank" rel="noopener noreferrer">
                  衍策引擎AI
                </a>
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
          <h2 className="cta-title">加入我们的园区智能服务之旅</h2>
          <p className="cta-subtitle">
            无论是产品咨询、合作意向还是加入我们团队，都欢迎联系衍策引擎。
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
              发送邮件
            </a>
          </div>
        </div>
      </section>
    </>
  );
}
