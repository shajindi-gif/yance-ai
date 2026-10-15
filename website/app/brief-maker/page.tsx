import Link from 'next/link';

export const metadata = {
  title: '报告与申报材料生成 | 衍策引擎AI',
  description:
    '产业研究报告、申报书、材料清单与合规检查生成，支持 PDF 与 Word 导出。',
};


export default function BriefMakerPage() {
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
            BriefMaker
          </span>
          <h1>材料清单与简报生成</h1>
          <p>
            按政策要求生成材料清单、服务简报和报告初稿，交付内容可追溯到原文条款，人工复核后即可使用。
          </p>
        </div>
      </section>

      {/* Overview */}
      <section className="section">
        <div className="container">
          <div className="split">
            <div className="split-content">
              <span className="section-label">智能生成引擎</span>
              <h2 className="section-title mb-4">从匹配结果到标准文档，一键生成</h2>
              <p>
                BriefMaker 根据政策匹配结果和企业画像数据，自动生成标准化的申报材料清单、企业服务简报和政策推荐报告。
              </p>
              <p>
                每一份输出都包含精确的政策引用、材料要求说明和缺口分析，可以直接用于园区企业服务工作。
              </p>
              <div className="mt-8">
                <Link href="/login?register=1" className="btn btn-primary" style={{ background: '#126a9a', borderColor: '#126a9a', borderRadius: '12px' }}>
                  注册生成报告
                </Link>
              </div>
            </div>
            <div className="split-visual">
              <div style={{ textAlign: 'center', width: '100%' }}>
                <div style={{ fontSize: '3rem', marginBottom: '16px' }}>&#x1F4DD;</div>
                <h4 style={{ marginBottom: '12px' }}>自动生成</h4>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', maxWidth: '280px', margin: '0 auto' }}>
                  {['匹配结果', '材料清单', '服务简报', '推荐报告'].map((step, i) => (
                    <div
                      key={step}
                      style={{
                        padding: '10px 16px',
                        background: i === 0 ? '#126a9a' : i === 3 ? '#f97316' : 'var(--bg-card)',
                        color: i === 0 || i === 3 ? '#fff' : 'var(--text)',
                        border: i === 0 || i === 3 ? 'none' : '1px solid var(--border)',
                        borderRadius: '8px',
                        fontSize: '0.875rem',
                        fontWeight: 600,
                        textAlign: 'center',
                      }}
                    >
                      {i + 1}. {step}
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Three Output Types */}
      <section className="section section-alt">
        <div className="container">
          <div className="section-header">
            <span className="section-label">输出类型</span>
            <h2 className="section-title">三种核心输出文档</h2>
            <p className="section-subtitle">
              BriefMaker 支持生成三种类型的标准化文档，覆盖企业服务的不同阶段。
            </p>
          </div>

          <div className="grid grid-3" style={{ gap: '24px' }}>
            <div className="module-card" style={{ borderTop: '4px solid #126a9a' }}>
              <div className="module-card-name" style={{ color: 'var(--teal)' }}>Output 1</div>
              <h3 className="module-card-title">申报材料清单</h3>
              <p className="module-card-desc">
                针对每个政策项目，生成完整的申报材料清单，标注每项材料的状态和要求。
              </p>
              <ul className="module-card-features">
                <li>完整的材料列表和说明</li>
                <li>已备/缺口材料标注</li>
                <li>材料格式和规格要求</li>
                <li>获取渠道和办理指引</li>
              </ul>
            </div>

            <div className="module-card" style={{ borderTop: '4px solid #16a34a' }}>
              <div className="module-card-name" style={{ color: '#16a34a' }}>Output 2</div>
              <h3 className="module-card-title">企业服务简报</h3>
              <p className="module-card-desc">
                为每家企业生成一对一的服务简报，汇总该企业可享受的政策资源和行动计划。
              </p>
              <ul className="module-card-features">
                <li>企业画像摘要</li>
                <li>可申报政策优先级列表</li>
                <li>材料缺口和行动建议</li>
                <li>预计申报时间线</li>
              </ul>
            </div>

            <div className="module-card" style={{ borderTop: '4px solid #f97316' }}>
              <div className="module-card-name" style={{ color: '#f97316' }}>Output 3</div>
              <h3 className="module-card-title">政策推荐报告</h3>
              <p className="module-card-desc">
                为园区运营团队生成政策推荐报告，帮助规划政策推广和企业服务计划。
              </p>
              <ul className="module-card-features">
                <li>重点政策摘要</li>
                <li>覆盖企业数量分析</li>
                <li>推广优先级建议</li>
                <li>服务资源配置建议</li>
              </ul>
            </div>
          </div>
        </div>
      </section>

      {/* Sample Output */}
      <section className="section">
        <div className="container">
          <div className="section-header">
            <span className="section-label">DEMO / 虚构输出样例</span>
            <h2 className="section-title">申报材料清单样例</h2>
            <p className="section-subtitle">
              下列企业状态、材料数量和门槛数字仅用于演示界面结构，不是当前政策建议；真实结果必须附政策原文和有效期。
            </p>
          </div>

          <div className="dashboard-preview">
            <div className="dashboard-header">
              <span className="dashboard-header-title">
                高新技术企业认定 - 申报材料清单
              </span>
              <span className="badge badge-warning">4 项待补充</span>
            </div>

            <div className="table-wrapper">
              <table className="table">
                <thead>
                  <tr>
                    <th>材料名称</th>
                    <th>规格要求</th>
                    <th>状态</th>
                    <th>备注</th>
                  </tr>
                </thead>
                <tbody>
                  {[
                    { name: '高新技术企业认定申请书', spec: '在线填写并打印', status: '已准备', badge: 'badge-success', note: '通过科技部网站在线填报' },
                    { name: '企业营业执照副本', spec: '复印件加盖公章', status: '已准备', badge: 'badge-success', note: '-' },
                    { name: '知识产权证明材料', spec: '证书复印件', status: '已准备', badge: 'badge-success', note: '已有 8 项有效专利' },
                    { name: '科研项目立项证明', spec: '立项报告/结题报告', status: '待补充', badge: 'badge-warning', note: '需补充 2024 年度项目' },
                    { name: '研发费用专项审计报告', spec: '近三年 / 有资质事务所', status: '待补充', badge: 'badge-warning', note: '需联系审计机构' },
                    { name: '高新技术产品收入证明', spec: '合同/发票等', status: '待补充', badge: 'badge-warning', note: '占比需达 60% 以上' },
                    { name: '企业职工和科技人员说明', spec: '花名册及社保', status: '待补充', badge: 'badge-warning', note: '科技人员占比需达 10%' },
                  ].map((item) => (
                    <tr key={item.name}>
                      <td style={{ fontWeight: 600 }}>{item.name}</td>
                      <td>{item.spec}</td>
                      <td><span className={`badge ${item.badge}`}>{item.status}</span></td>
                      <td>{item.note}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </section>

      {/* Export Formats */}
      <section className="section section-alt">
        <div className="container">
          <div className="section-header">
            <span className="section-label">导出格式</span>
            <h2 className="section-title">支持多种文档格式导出</h2>
          </div>

          <div className="grid grid-4" style={{ gap: '20px' }}>
            {[
              { icon: '\u{1F4C4}', title: 'PDF', desc: '报告支持 PDF 导出（当前已上线）' },
              { icon: '\u{1F4CA}', title: 'Excel', desc: '规划中 · 尚未上线' },
              { icon: '\u{1F4DD}', title: 'Word', desc: '申报材料支持 DOCX 导出（当前已上线）' },
              { icon: '\u{1F517}', title: 'API', desc: '规划中 · 尚未开放' },
            ].map((fmt) => (
              <div key={fmt.title} className="card" style={{ textAlign: 'center', padding: '32px 24px' }}>
                <div style={{ fontSize: '2.5rem', marginBottom: '12px' }}>{fmt.icon}</div>
                <h4 className="card-title">{fmt.title}</h4>
                <p className="card-desc">{fmt.desc}</p>
              </div>
            ))}
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
          <h2 className="cta-title">体验智能材料生成</h2>
          <p className="cta-subtitle">
            在 Demo 中体验 BriefMaker 的材料清单和简报自动生成功能。
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
