'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';

/* -------------------------------------------
   Icons — 统一线性图标（20px stroke，品牌青蓝）
   ------------------------------------------- */
const iconProps = {
  width: 20,
  height: 20,
  viewBox: '0 0 24 24',
  fill: 'none',
  stroke: 'currentColor',
  strokeWidth: 1.8,
  strokeLinecap: 'round' as const,
  strokeLinejoin: 'round' as const,
  'aria-hidden': true,
};

const ICONS: Record<string, React.ReactNode> = {
  target: (
    <svg {...iconProps}>
      <circle cx="12" cy="12" r="9" />
      <circle cx="12" cy="12" r="5" />
      <circle cx="12" cy="12" r="1" fill="currentColor" />
    </svg>
  ),
  doc: (
    <svg {...iconProps}>
      <path d="M14 3H6a1 1 0 0 0-1 1v16a1 1 0 0 0 1 1h12a1 1 0 0 0 1-1V8z" />
      <path d="M14 3v5h5" />
      <path d="M9 13h6M9 17h4" />
    </svg>
  ),
  chart: (
    <svg {...iconProps}>
      <path d="M4 20h16" />
      <path d="M6 20V10M11 20V4M16 20v-8" />
    </svg>
  ),
  building: (
    <svg {...iconProps}>
      <rect x="4" y="3" width="10" height="18" rx="1" />
      <path d="M14 9h5a1 1 0 0 1 1 1v11a1 1 0 0 1-1 1h-5" />
      <path d="M7 7h4M7 11h4M7 15h4" />
    </svg>
  ),
  park: (
    <svg {...iconProps}>
      <path d="M3 21h18" />
      <path d="M6 21V8l6-4 6 4v13" />
      <path d="M10 21v-5h4v5" />
    </svg>
  ),
  bot: (
    <svg {...iconProps}>
      <rect x="5" y="8" width="14" height="11" rx="2" />
      <path d="M12 8V5M9 5h6" />
      <circle cx="9.5" cy="13" r="1" fill="currentColor" />
      <circle cx="14.5" cy="13" r="1" fill="currentColor" />
      <path d="M9.5 16.5h5" />
    </svg>
  ),
  search: (
    <svg {...iconProps}>
      <circle cx="11" cy="11" r="7" />
      <path d="m20 20-3.5-3.5" />
    </svg>
  ),
  shield: (
    <svg {...iconProps}>
      <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
      <path d="m9 12 2 2 4-4" />
    </svg>
  ),
};

function Icon({ name, size = 20 }: { name: string; size?: number }) {
  return (
    <span className="yc-icon" style={{ width: size, height: size }}>
      {ICONS[name] ?? ICONS.target}
    </span>
  );
}

/* -------------------------------------------
   FAQ Data
   ------------------------------------------- */
const FAQ_ITEMS = [
  {
    q: '衍策引擎AI 是什么平台？',
    a: '衍策引擎AI 是面向中国新质生产力科技企业的 AI 产业研究与政策申报服务平台。我们帮助 AI、机器人、生物医药、集成电路、新能源等领域的科技企业完成产业研究、政策匹配、补贴申报辅助、申报材料生成、园区入驻资源匹配和融资 BP 生成。',
  },
  {
    q: '衍策引擎AI 和传统咨询公司有什么区别？',
    a: '衍策引擎AI 将企业信息、政策来源、资格条件、证据和任务保存在持续工作区中，并用结构化流程执行匹配与生成。实际节省时间和输出质量必须通过真实项目与评测验证，本网站不发布未经验证的效率数字。',
  },
  {
    q: '支持哪些行业和地区的政策？',
    a: '行业覆盖 AI、机器人与智能制造、生物医药、集成电路、新能源新材料、数据智能、SaaS 等新质生产力方向。政策覆盖国家级、省级和市级政策，重点深耕上海及各区，企业版可扩展至全国任意地区。',
  },
  {
    q: '数据安全如何保障？',
    a: '当前代码已实现密码哈希、令牌有效期、租户与角色校验、受限文件上传、支付回调校验和隔离的文档渲染。TLS、备份、存储加密、私有化部署与第三方认证必须在具体部署环境中单独配置和验收。',
  },
  {
    q: '能否与企业现有系统集成？',
    a: '当前产品提供内部 API，但面向客户的 API Key、Webhook、OA/CRM/ERP 标准连接器尚在路线图中。企业集成需要先进行数据与安全范围评估。',
  },
  {
    q: 'AI 输出的结果可信吗？',
    a: '资格引擎会在硬门槛失败或证据不足时降级结论，但现阶段仍需人工核对政策原文。完整的条款级引用、人工审批工作流和质量评测正在建设；我们不承诺申报一定成功。',
  },
  {
    q: '园区和孵化器如何使用？',
    a: '现阶段可通过企业画像、政策匹配和报告流程开展试点。批量园区管理、Knowledge Bot 和跨园区数据对比属于后续产品范围，不应视为已上线能力。',
  },
  {
    q: '如何开始使用？',
    a: '注册后完善企业画像，即可生成政策匹配初筛报告。如需 30 分钟专属诊断，发送邮件至 contact@yance.ai 预约，我们将根据企业实际场景进行针对性讲解。',
  },
];

/* -------------------------------------------
   Quick Search Examples
   ------------------------------------------- */
const QUICK_EXAMPLES = [
  '上海 AI 企业政策补贴匹配',
  '高新技术企业申报诊断',
  '专精特新申报条件评估',
  '徐汇 / 张江 / 临港园区入驻方案',
];

/* -------------------------------------------
   Product Modules（与主导航一致的七个模块）
   ------------------------------------------- */
const PRODUCTS = [
  {
    icon: 'target',
    name: 'Policy Match',
    subtitle: '企业政策匹配引擎',
    desc: '基于企业画像和政策语义理解，自动匹配适用政策并生成适配度评分、材料缺口分析和优先级排序。',
    tags: ['语义匹配', '适配度评分', '材料缺口'],
    href: '/login?register=1',
  },
  {
    icon: 'doc',
    name: 'Grant Copilot',
    subtitle: '政策补贴申报助手',
    desc: '从政策解读到材料清单生成，辅助企业完成补贴申报全流程，提供条款级引用和合规性检查。',
    tags: ['申报辅助', '材料生成', '合规检查'],
    href: '/pricing',
  },
  {
    icon: 'chart',
    name: 'Industry Research',
    subtitle: '新质生产力产业研究系统',
    desc: '覆盖 AI、机器人、生物医药、集成电路、新能源等赛道的产业格局、价值链、政策趋势分析。',
    tags: ['产业图谱', '价值链', '趋势分析'],
    href: '/policy-knowledge-base',
  },
  {
    icon: 'building',
    name: 'Company Profile',
    subtitle: '科技企业画像生成器',
    desc: '整合企业工商、知识产权、财务、团队等多维数据，自动生成结构化企业画像，支持申报资质评估。',
    tags: ['多维画像', '资质评估', '数据整合'],
    href: '/company-match',
  },
  {
    icon: 'park',
    name: 'Park Entry',
    subtitle: '园区入驻与资源匹配助手',
    desc: '基于企业行业、发展阶段和资源需求，推荐最优园区入驻方案，匹配产业资源、人才政策和资金支持。',
    tags: ['园区推荐', '资源匹配', '入驻方案'],
    href: '/parks',
  },
  {
    icon: 'doc',
    name: 'Report Studio',
    subtitle: '产业报告与申报材料生成器',
    desc: '一键生成产业研究报告、申报书、融资 BP、项目计划书等专业文档，支持 PDF 和 Word 导出。',
    tags: ['报告生成', 'BP 生成', '多格式导出'],
    href: '/brief-maker',
  },
  {
    icon: 'bot',
    name: 'Knowledge Bot',
    subtitle: '园区政策知识库 Bot',
    desc: '路线图能力：基于园区政策文件构建可追溯问答，并在完成权限和数据边界验收后接入企业渠道。',
    tags: ['路线图', '知识问答', '来源追溯'],
    href: '/policy-knowledge-base',
  },
];

/* -------------------------------------------
   Industry Solutions Data
   ------------------------------------------- */
const SOLUTIONS = [
  {
    icon: 'bot',
    name: 'AI 企业',
    desc: '大模型、AI 基础设施、AI 应用、AI SaaS 等企业的政策支持、算力补贴和场景落地资源。',
    highlights: ['算力补贴', 'AI 备案指导', '场景对接'],
  },
  {
    icon: 'park',
    name: '机器人与智能制造',
    desc: '工业机器人、服务机器人、智能制造装备企业的产业用地、首台套政策和应用示范项目申报。',
    highlights: ['首台套政策', '产业用地', '示范项目'],
  },
  {
    icon: 'search',
    name: '生物医药',
    desc: '创新药、医疗器械、生物制品企业的研发补贴、临床批件申报和产业园区优惠政策匹配。',
    highlights: ['研发补贴', '临床批件', 'GMP 认证'],
  },
  {
    icon: 'chart',
    name: '集成电路',
    desc: '芯片设计、制造、封测、EDA 工具企业的专项扶持政策、流片补贴和人才引进计划。',
    highlights: ['流片补贴', 'EDA 补贴', '人才专项'],
  },
  {
    icon: 'shield',
    name: '新能源新材料',
    desc: '储能、光伏、氢能、新型材料企业的绿色金融支持、碳中和政策和产业基地入驻资源。',
    highlights: ['绿色金融', '碳中和政策', '基地入驻'],
  },
  {
    icon: 'building',
    name: '园区与产业服务机构',
    desc: '产业园区、孵化器、加速器的企业服务能力建设、政策知识库部署和招商智能化工具。',
    highlights: ['企业服务台', '知识库 Bot', '招商工具'],
  },
];

export default function HomePage() {
  const router = useRouter();
  const [openFaq, setOpenFaq] = useState<number | null>(null);
  const [searchInput, setSearchInput] = useState('');

  const submitSearch = (e: React.FormEvent) => {
    e.preventDefault();
    // 报告生成需要企业画像与账户，注册后由 Onboarding 引导完成
    router.push('/login?register=1');
  };

  return (
    <>
      {/* ===== HERO ===== */}
      <section className="yc-hero">
        <div className="yc-hero-mesh" />
        <div className="container" style={{ position: 'relative', zIndex: 1 }}>
          <div style={{ maxWidth: '800px' }}>
            <div className="yc-hero-badge">
              <span className="yc-hero-badge-dot" />
              面向新质生产力科技企业 &middot; 衍策引擎AI
            </div>

            <h1 className="yc-hero-title">
              中国新质生产力企业的<br />
              <span style={{ color: 'var(--teal-bright)' }}>AI 产业研究与政策申报平台</span>
            </h1>

            <p className="yc-hero-subtitle">
              衍策引擎AI 帮助科技企业完成产业研究、政策匹配、补贴申报、园区入驻、项目材料生成和企业成长规划，让企业更快找到政策、资金、资源和增长路径。
            </p>

            <div className="yc-hero-ctas">
              <Link href="/login?register=1" className="yc-btn-primary">
                免费生成政策匹配报告
              </Link>
              <a href="mailto:contact@yance.ai?subject=申报诊断预约" className="yc-btn-outline-white">
                预约 30 分钟诊断
              </a>
            </div>
          </div>
        </div>
      </section>

      {/* ===== SMART INPUT BOX（报告生成入口） ===== */}
      <section className="yc-input-section">
        <div className="container">
          <form className="yc-input-wrapper" onSubmit={submitSearch}>
            <h2 className="yc-input-title">生成你的企业政策与产业机会初筛报告</h2>
            <div className="yc-search-box">
              <div className="yc-search-icon">
                <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                  <circle cx="11" cy="11" r="8" />
                  <line x1="21" y1="21" x2="16.65" y2="16.65" />
                </svg>
              </div>
              <label htmlFor="hero-search" className="yc-visually-hidden">企业信息描述</label>
              <textarea
                id="hero-search"
                className="yc-search-textarea"
                rows={2}
                placeholder="请输入企业名称、所在城市、行业或项目方向，例如：上海 AI SaaS 公司、张江机器人企业、生物医药高新技术企业。"
                value={searchInput}
                onChange={(e) => setSearchInput(e.target.value)}
              />
              <button type="submit" className="yc-search-submit">
                生成报告
              </button>
            </div>
            <div className="yc-quick-examples">
              <span className="yc-quick-label">快捷示例：</span>
              {QUICK_EXAMPLES.map((ex) => (
                <button
                  type="button"
                  key={ex}
                  className="yc-quick-chip"
                  onClick={() => setSearchInput(ex)}
                >
                  {ex}
                </button>
              ))}
            </div>
          </form>
        </div>
      </section>

      {/* ===== REPORT PREVIEW ===== */}
      <section className="section">
        <div className="container">
          <div className="section-header">
            <span className="section-label">报告预览</span>
            <h2 className="section-title">科技企业政策匹配与产业机会初筛报告</h2>
            <p className="section-subtitle">
              输入企业基本信息，AI 自动生成结构化的政策匹配与产业机会分析报告。
            </p>
          </div>

          <div className="yc-report-card">
            <div className="yc-report-header">
              <div className="yc-report-logo">
                <img src="/logo.png" alt="" width={28} height={28} style={{ borderRadius: '6px', verticalAlign: 'middle', marginRight: '10px' }} />
                <span style={{ fontWeight: 800, fontSize: '1.125rem', color: 'var(--teal-bright)' }}>衍策引擎AI</span>
                <span style={{ fontSize: '0.75rem', color: 'rgba(255,255,255,0.6)', marginLeft: '12px' }}>Policy Intelligence Report</span>
              </div>
              <div className="yc-report-meta">
                <span>DEMO / 虚构企业样例</span>
                <span>报告编号：DEMO-SAMPLE-001</span>
              </div>
            </div>

            <div className="yc-report-body">
              <div className="yc-report-grid">
                {[
                  {
                    label: '企业方向',
                    value: 'AI SaaS · 企业级智能客服',
                    detail: '基于大语言模型的企业级 SaaS 产品，面向中大型企业提供智能客服解决方案。',
                  },
                  {
                    label: '新质生产力标签',
                    value: '人工智能 · 数据智能 · SaaS',
                    detail: '符合上海市新质生产力方向，适配人工智能产业发展三年行动方案。',
                  },
                  {
                    label: '推荐政策类型',
                    value: '5 项高适配政策',
                    detail: '含 2 项国家级、2 项市级、1 项区级政策，预估补贴总额 ¥120-280 万。',
                  },
                  {
                    label: '推荐园区资源',
                    value: '3 个适配园区',
                    detail: '张江人工智能岛、徐汇滨江 AI 中心、临港新片区智能产业聚集区。',
                  },
                  {
                    label: '材料缺口',
                    value: '3 项待补充',
                    detail: '缺软件著作权登记证书、上年度审计报告、研发投入专项说明。',
                  },
                  {
                    label: '30 天行动计划',
                    value: '4 步关键行动',
                    detail: '第 1 周完成软著申请 → 第 2 周准备审计材料 → 第 3 周提交预申报 → 第 4 周对接园区。',
                  },
                ].map((item) => (
                  <div key={item.label} className="yc-report-item">
                    <div className="yc-report-item-label">{item.label}</div>
                    <div className="yc-report-item-value">{item.value}</div>
                    <div className="yc-report-item-detail">{item.detail}</div>
                  </div>
                ))}
              </div>
            </div>

            <div className="yc-report-footer">
              <span className="yc-report-disclaimer">
                * DEMO：以上企业、匹配数量、园区、时间线和金额均为虚构展示数据，不代表真实政策结论或客户结果。
              </span>
              <Link href="/login?register=1" className="yc-btn-primary-sm">
                生成你的报告 &rarr;
              </Link>
            </div>
          </div>
        </div>
      </section>

      {/* ===== PRODUCT MODULES ===== */}
      <section className="section section-alt">
        <div className="container">
          <div className="section-header">
            <span className="section-label">产品能力</span>
            <h2 className="section-title">从产业研究到申报落地的全链路 AI 引擎</h2>
            <p className="section-subtitle">
              七个产品模块覆盖政策服务全场景：企业画像、政策匹配、材料生成、园区入驻，每个环节都有对应工具支撑。
            </p>
          </div>

          <div className="yc-product-grid">
            {PRODUCTS.map((p, i) => (
              <Link key={p.name} href={p.href} className={`yc-product-card${i === 0 ? ' yc-product-featured' : ''}`}>
                <div className="yc-product-icon"><Icon name={p.icon} size={22} /></div>
                <div className="yc-product-name">{p.name}</div>
                <div className="yc-product-subtitle">{p.subtitle}</div>
                <p className="yc-product-desc">{p.desc}</p>
                <div className="yc-product-tags">
                  {p.tags.map((t) => (
                    <span key={t} className="yc-product-tag">{t}</span>
                  ))}
                </div>
              </Link>
            ))}
          </div>
        </div>
      </section>

      {/* ===== TRUST & TRACEABILITY ===== */}
      <section className="yc-trust-section">
        <div className="container">
          <div className="section-header">
            <span className="section-label" style={{ color: 'var(--teal-bright)' }}>可信溯源</span>
            <h2 className="section-title" style={{ color: '#fff' }}>
              每条建议，都可追溯、可解释、可复核
            </h2>
            <p className="section-subtitle" style={{ color: 'rgba(255,255,255,0.65)' }}>
              衍策引擎AI 的所有输出都建立在可追溯的数据基础之上，确保专业性和可信度。
            </p>
          </div>

          <div className="yc-trust-chip-row">
            {[
              '政策原文来源',
              '政策时效标注',
              '适用条件说明',
              '匹配规则透明',
              '数据更新时间',
              '引用精确到条',
              '复核机制',
              '操作审计日志',
            ].map((label) => (
              <div key={label} className="yc-trust-chip">
                {label}
              </div>
            ))}
          </div>

          <div className="yc-trust-banner">
            <span className="yc-trust-banner-label">
              人工复核
            </span>
            <span className="yc-trust-banner-text">
              &mdash; 所有 AI 输出均支持人工复核和结果修正流程，确保服务质量
            </span>
          </div>
        </div>
      </section>

      {/* ===== INDUSTRY SOLUTIONS ===== */}
      <section className="section section-alt">
        <div className="container">
          <div className="section-header">
            <span className="section-label">行业解决方案</span>
            <h2 className="section-title">深耕新质生产力六大核心赛道</h2>
            <p className="section-subtitle">
              为每个行业定制政策匹配逻辑和产业研究框架，提供精准的申报辅助服务。
            </p>
          </div>

          <div className="yc-solution-grid">
            {SOLUTIONS.map((s) => (
              <div key={s.name} className="yc-solution-card">
                <div className="yc-solution-icon"><Icon name={s.icon} size={22} /></div>
                <h3 className="yc-solution-name">{s.name}</h3>
                <p className="yc-solution-desc">{s.desc}</p>
                <div className="yc-solution-highlights">
                  {s.highlights.map((h) => (
                    <span key={h} className="yc-solution-highlight">{h}</span>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ===== FAQ ===== */}
      <section className="section section-alt">
        <div className="container">
          <div className="container-narrow">
            <div className="section-header">
              <span className="section-label">常见问题</span>
              <h2 className="section-title">FAQ</h2>
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
              {FAQ_ITEMS.map((item, i) => (
                <div key={i} className="yc-faq-item">
                  <button
                    onClick={() => setOpenFaq(openFaq === i ? null : i)}
                    className="yc-faq-question"
                    aria-expanded={openFaq === i}
                  >
                    {item.q}
                    <span className={`yc-faq-icon${openFaq === i ? ' open' : ''}`}>+</span>
                  </button>
                  {openFaq === i && (
                    <div className="yc-faq-answer">{item.a}</div>
                  )}
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* ===== COMPLIANCE ===== */}
      <section className="yc-compliance-section">
        <div className="container">
          <div className="yc-compliance-box">
            <div className="yc-compliance-icon">
              <Icon name="shield" size={24} />
            </div>
            <p className="yc-compliance-text">
              衍策引擎AI 提供产业研究、政策信息整理、材料生成和申报辅助服务，具体申报条件、申报结果和补贴金额以主管部门、园区、政策文件和审核结果为准。
            </p>
          </div>
        </div>
      </section>

      {/* ===== FINAL CTA ===== */}
      <section className="yc-cta-section">
        <div className="container">
          <h2 className="yc-cta-title">让你的企业更快找到政策、资金和资源</h2>
          <p className="yc-cta-subtitle">
            注册后完善企业画像即可生成政策匹配初筛报告，或预约 30 分钟专属诊断。
          </p>
          <div className="yc-cta-actions">
            <Link href="/login?register=1" className="yc-btn-primary">
              免费生成政策匹配报告
            </Link>
            <a href="mailto:contact@yance.ai?subject=产品咨询" className="yc-btn-outline-white">
              联系我们
            </a>
          </div>
          <div className="yc-cta-info">
            <span>contact@yance.ai</span>
            <span className="yc-cta-sep">|</span>
            <span>衍策引擎AI</span>
          </div>
        </div>
      </section>
    </>
  );
}
