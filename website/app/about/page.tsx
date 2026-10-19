import Link from 'next/link';
import Image from 'next/image';

export const metadata = {
  title: '关于我们 | 衍策引擎AI',
  description:
    '团队、产品理念与责任域说明：衍策引擎AI 如何以可追溯的数据与流程服务科技企业政策申报。',
};


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
              color: 'var(--teal)',
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
                衍策引擎做的事：把分散在各级政府网站的政策文件整理成可核对的条件清单，让企业和园区服务方用同一份数据判断申报资格、准备材料。
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
                desc: '每一条建议都附政策原文条款与企业事实，可逐条核对、复核，不输出无法追溯的结论。',
                bg: '#f0f9ff',
                color: 'var(--teal)',
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
                color: 'var(--teal)',
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
            <div className="card" style={{ padding: '32px', borderTop: '3px solid #126a9a' }}>
              <div className="card-icon" style={{ background: '#f0f9ff', color: 'var(--teal)' }}>
                <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="9"/><path d="M12 3a9 9 0 0 1 9 9h-4a5 5 0 0 0-10 0H3a9 9 0 0 1 9-9z" fill="currentColor" stroke="none" opacity=".25"/><circle cx="12" cy="12" r="2" fill="currentColor" stroke="none"/></svg>
              </div>
              <h3 className="card-title">政策语义理解引擎</h3>
              <p className="card-desc" style={{ marginBottom: '20px' }}>
                基于可配置大语言模型与规则校验提取政策条件，条件要素结构化后进入匹配引擎。
              </p>
              <ul className="module-card-features">
                <li>政策文本结构化解析</li>
                <li>条件要素结构化提取</li>
                <li>多政策语义关联分析</li>
                <li>政策日期与状态元数据</li>
              </ul>
            </div>
            <div className="card" style={{ padding: '32px', borderTop: '3px solid #16a34a' }}>
              <div className="card-icon" style={{ background: '#f0fdf4', color: '#16a34a' }}>
                <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 1 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 1 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 1 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 1 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"/></svg>
              </div>
              <h3 className="card-title">企业-政策匹配算法</h3>
              <p className="card-desc" style={{ marginBottom: '20px' }}>
                融合规则评分、向量检索与证据门禁，将企业画像与政策条件进行多维度匹配；准确率由评测集衡量。
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
            <span className="section-label">责任域</span>
            <h2 className="section-title">产品建设所需的职责</h2>
            <p className="section-subtitle">
              产品交付需要覆盖的能力域，随产品阶段逐步完备。
            </p>
          </div>

          <div className="grid grid-3" style={{ gap: '24px' }}>
            {[
              {
                initials: 'AI',
                title: 'AI 与算法团队',
                desc: '负责模型接入、检索、证据、评测和成本边界。',
                bg: '#f0f9ff',
                color: 'var(--teal)',
              },
              {
                initials: 'PD',
                title: '产品与设计团队',
                desc: '负责企业工作流、交互、可用性和真实数据原则。',
                bg: '#f0fdf4',
                color: '#16a34a',
              },
              {
                initials: 'BD',
                title: '行业与客户团队',
                desc: '负责政策规则复核、试点验收和客户实施边界。',
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
            <span className="section-label">建设状态</span>
            <h2 className="section-title">可验证的产品阶段</h2>
          </div>

          <div className="container-narrow">
            <div className="timeline">
              {[
                { title: '当前代码基线', desc: '具备租户、企业、政策、匹配、报告、订单与基础任务模型。' },
                { title: '安全加固进行中', desc: '支付、租户边界、文件入口、文档渲染和真实性声明已进入自动化验证。' },
                { title: 'Agent 工作闭环建设中', desc: 'Harness、证据优先检索、Application Workspace 和人工复核仍在分阶段实现。' },
                { title: '试点进行中', desc: '正在与首批企业和园区开展定向试点，成效数据将在可公开验证后发布。' },
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
              <div className="card-icon" style={{ margin: '0 auto 16px', background: '#f0f9ff', color: 'var(--teal)' }}>
                <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"><rect x="3" y="5" width="18" height="14" rx="2"/><path d="m3 7 9 6 9-6"/></svg>
              </div>
              <h4 className="card-title">邮件联系</h4>
              <p className="card-desc">
                <a href="mailto:yanceai@163.com">yanceai@163.com</a>
              </p>
            </div>
            <div className="card" style={{ textAlign: 'center', padding: '32px' }}>
              <div className="card-icon" style={{ margin: '0 auto 16px', background: '#f0fdf4', color: '#16a34a' }}>
                <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"><rect x="4" y="3" width="10" height="18" rx="1"/><path d="M14 9h5a1 1 0 0 1 1 1v11a1 1 0 0 1-1 1h-5"/><path d="M7 7h4M7 11h4M7 15h4"/></svg>
              </div>
              <h4 className="card-title">公司地址</h4>
              <p className="card-desc">上海市徐汇区</p>
            </div>
            <div className="card" style={{ textAlign: 'center', padding: '32px' }}>
              <div className="card-icon" style={{ margin: '0 auto 16px', background: '#fff7ed', color: '#f97316' }}>
                <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="9"/><path d="M3 12h18M12 3a15 15 0 0 1 0 18 15 15 0 0 1 0-18z"/></svg>
              </div>
              <h4 className="card-title">联系邮箱</h4>
              <p className="card-desc">
                <a href="mailto:yanceai@163.com">yanceai@163.com</a>
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
              免费注册
            </Link>
            <a href="mailto:yanceai@163.com" className="btn btn-outline-white btn-lg">
              发送邮件
            </a>
          </div>
        </div>
      </section>
    </>
  );
}
