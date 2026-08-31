'use client';

import { useState } from 'react';
import Link from 'next/link';

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
    a: '传统咨询公司按人天收费、交付周期长、覆盖面有限。衍策引擎AI 通过 AI 引擎实现政策语义理解、企业画像自动构建、智能匹配和材料生成，将原本数周的工作压缩到分钟级，同时保持专业级输出质量和全流程可追溯。',
  },
  {
    q: '支持哪些行业和地区的政策？',
    a: '行业覆盖 AI、机器人与智能制造、生物医药、集成电路、新能源新材料、数据智能、SaaS 等新质生产力方向。政策覆盖国家级、省级和市级政策，重点深耕上海及各区，企业版可扩展至全国任意地区。',
  },
  {
    q: '数据安全如何保障？',
    a: '所有企业数据加密存储，严格的权限控制体系。系统支持操作审计日志和人工复核机制。企业版提供私有化部署选项，数据完全在客户环境中运行。',
  },
  {
    q: '能否与企业现有系统集成？',
    a: '专业版和企业版提供 API 集成能力，可与企业现有的 OA、CRM、ERP 等系统对接。企业版支持深度定制集成。',
  },
  {
    q: 'AI 输出的结果可信吗？',
    a: '每条建议都附带政策原文引用和来源溯源，支持精确到条款级别。系统内置 10 项可追溯字段，并支持人工复核和结果修正流程。我们不承诺申报一定成功，具体条件以主管部门和政策文件为准。',
  },
  {
    q: '园区和孵化器如何使用？',
    a: '园区和孵化器可以通过我们的 Knowledge Bot（政策知识库 Bot）和 Park Entry（园区入驻匹配）功能，为在园企业提供批量政策服务。企业版支持多园区统一管理和跨园区数据对比。',
  },
  {
    q: '如何开始使用？',
    a: '你可以直接在首页输入企业信息生成政策匹配初筛报告，或预约 30 分钟的专属诊断，我们将根据企业实际场景进行针对性讲解。发送邮件至 contact@yance.ai 即可预约。',
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
  '新质生产力产业研究报告',
];

/* -------------------------------------------
   Product Matrix Data
   ------------------------------------------- */
const PRODUCTS = [
  {
    name: 'Policy Match',
    subtitle: '企业政策匹配引擎',
    icon: '\u{1F3AF}',
    desc: '基于企业画像和政策语义理解，自动匹配适用政策并生成适配度评分、材料缺口分析和优先级排序。',
    tags: ['语义匹配', '适配度评分', '材料缺口'],
  },
  {
    name: 'Grant Copilot',
    subtitle: '政策补贴申报助手',
    icon: '\u{1F4DD}',
    desc: '从政策解读到材料清单生成，辅助企业完成补贴申报全流程，提供条款级引用和合规性检查。',
    tags: ['申报辅助', '材料生成', '合规检查'],
  },
  {
    name: 'Industry Research',
    subtitle: '新质生产力产业研究系统',
    icon: '\u{1F4CA}',
    desc: '覆盖 AI、机器人、生物医药、集成电路、新能源等赛道的产业格局、价值链、政策趋势和投资标的分析。',
    tags: ['产业图谱', '价值链', '趋势分析'],
  },
  {
    name: 'Company Profile',
    subtitle: '科技企业画像生成器',
    icon: '\u{1F3E2}',
    desc: '整合企业工商、知识产权、财务、团队等多维数据，自动生成结构化企业画像，支持申报资质评估。',
    tags: ['多维画像', '资质评估', '数据整合'],
  },
  {
    name: 'Park Entry',
    subtitle: '园区入驻与资源匹配助手',
    icon: '\u{1F3D7}\u{FE0F}',
    desc: '基于企业行业、发展阶段和资源需求，推荐最优园区入驻方案，匹配产业资源、人才政策和资金支持。',
    tags: ['园区推荐', '资源匹配', '入驻方案'],
  },
  {
    name: 'Report Studio',
    subtitle: '产业报告与申报材料生成器',
    icon: '\u{1F4D1}',
    desc: '一键生成产业研究报告、申报书、融资 BP、项目计划书等专业文档，支持 PDF 和 Word 导出。',
    tags: ['报告生成', 'BP 生成', '多格式导出'],
  },
  {
    name: 'Knowledge Bot',
    subtitle: '园区政策知识库 Bot',
    icon: '\u{1F916}',
    desc: '基于园区政策文件训练的问答 Bot，可嵌入园区官网或企微，为在园企业提供 7x24 政策咨询服务。',
    tags: ['知识问答', '官网嵌入', '7x24 服务'],
  },
];

/* -------------------------------------------
   Industry Solutions Data
   ------------------------------------------- */
const SOLUTIONS = [
  {
    icon: '\u{1F9E0}',
    name: 'AI 企业',
    desc: '大模型、AI 基础设施、AI 应用、AI SaaS 等企业的政策支持、算力补贴和场景落地资源。',
    highlights: ['算力补贴', 'AI 备案指导', '场景对接'],
  },
  {
    icon: '\u{1F916}',
    name: '机器人与智能制造',
    desc: '工业机器人、服务机器人、智能制造装备企业的产业用地、首台套政策和应用示范项目申报。',
    highlights: ['首台套政策', '产业用地', '示范项目'],
  },
  {
    icon: '\u{1F9EC}',
    name: '生物医药',
    desc: '创新药、医疗器械、生物制品企业的研发补贴、临床批件申报和产业园区优惠政策匹配。',
    highlights: ['研发补贴', '临床批件', 'GMP 认证'],
  },
  {
    icon: '\u{1F4A1}',
    name: '集成电路',
    desc: '芯片设计、制造、封测、EDA 工具企业的专项扶持政策、流片补贴和人才引进计划。',
    highlights: ['流片补贴', 'EDA 补贴', '人才专项'],
  },
  {
    icon: '\u{26A1}',
    name: '新能源新材料',
    desc: '储能、光伏、氢能、新型材料企业的绿色金融支持、碳中和政策和产业基地入驻资源。',
    highlights: ['绿色金融', '碳中和政策', '基地入驻'],
  },
  {
    icon: '\u{1F3D7}\u{FE0F}',
    name: '园区与产业服务机构',
    desc: '产业园区、孵化器、加速器的企业服务能力建设、政策知识库部署和招商智能化工具。',
    highlights: ['企业服务台', '知识库 Bot', '招商工具'],
  },
];

export default function HomePage() {
  const [openFaq, setOpenFaq] = useState<number | null>(null);
  const [searchInput, setSearchInput] = useState('');
  const [annual, setAnnual] = useState(false);

  return (
    <>
      {/* ===== HERO SECTION ===== */}
      <section className="yc-hero">
        <div className="yc-hero-mesh" />
        <div className="container" style={{ position: 'relative', zIndex: 1 }}>
          <div style={{ maxWidth: '800px' }}>
            {/* Badge */}
            <div className="yc-hero-badge">
              <span className="yc-hero-badge-dot" />
              面向新质生产力科技企业 &middot; 衍策引擎AI
            </div>

            <h1 className="yc-hero-title">
              中国新质生产力企业的<br />
              <span style={{ color: '#0ea5e9' }}>AI 产业研究与政策申报平台</span>
            </h1>

            <p className="yc-hero-subtitle">
              衍策引擎AI 帮助科技企业完成产业研究、政策匹配、补贴申报、园区入驻、项目材料生成和企业成长规划，让企业更快找到政策、资金、资源和增长路径。
            </p>

            {/* CTAs */}
            <div className="yc-hero-ctas">
              <Link href="/login?register=1" className="yc-btn-primary">
                生成政策匹配报告
              </Link>
              <Link href="/pricing" className="yc-btn-outline">
                预约申报诊断
              </Link>
            </div>
          </div>
        </div>
      </section>

      {/* ===== PLATFORM ENTRY STRIP ===== */}
      <section className="yc-platform-strip">
        <div className="container">
          <div className="yc-platform-label">衍策引擎AI 全平台覆盖</div>
          <div className="yc-platform-grid">
            <Link href="/chrome-extension" className="yc-platform-card">
              <span className="yc-platform-icon">{'\u{1F310}'}</span>
              <span className="yc-platform-name">浏览器插件</span>
              <span className="yc-platform-desc">政策页面实时决策注入</span>
            </Link>
            <Link href="/downloads" className="yc-platform-card">
              <span className="yc-platform-icon">{'\u{1F4F1}'}</span>
              <span className="yc-platform-name">微信小程序</span>
              <span className="yc-platform-desc">30秒政策快查</span>
            </Link>
            <Link href="/downloads" className="yc-platform-card">
              <span className="yc-platform-icon">{'\u{1F4AC}'}</span>
              <span className="yc-platform-name">钉钉 / 飞书 Bot</span>
              <span className="yc-platform-desc">群内 @ 即查政策</span>
            </Link>
            <Link href="/downloads" className="yc-platform-card">
              <span className="yc-platform-icon">{'\u{1F4BB}'}</span>
              <span className="yc-platform-name">桌面客户端</span>
              <span className="yc-platform-desc">Mac / Windows 原生</span>
            </Link>
          </div>
        </div>
      </section>

      {/* ===== SMART INPUT BOX SECTION ===== */}
      <section className="yc-input-section">
        <div className="container">
          <div className="yc-input-wrapper">
            <h2 className="yc-input-title">生成你的企业政策与产业机会初筛报告</h2>
            <div className="yc-search-box">
              <div className="yc-search-icon">
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <circle cx="11" cy="11" r="8" />
                  <line x1="21" y1="21" x2="16.65" y2="16.65" />
                </svg>
              </div>
              <textarea
                className="yc-search-textarea"
                rows={2}
                placeholder="请输入企业名称、所在城市、行业或项目方向，例如：上海 AI SaaS 公司、张江机器人企业、生物医药高新技术企业。"
                value={searchInput}
                onChange={(e) => setSearchInput(e.target.value)}
              />
              <button className="yc-search-submit">
                生成报告
              </button>
            </div>
            <div className="yc-quick-examples">
              <span className="yc-quick-label">快捷示例：</span>
              {QUICK_EXAMPLES.map((ex) => (
                <button
                  key={ex}
                  className="yc-quick-chip"
                  onClick={() => setSearchInput(ex)}
                >
                  {ex}
                </button>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* ===== REPORT PREVIEW CARD SECTION ===== */}
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
            {/* Report Header */}
            <div className="yc-report-header">
              <div className="yc-report-logo">
                <img src="/logo.png" alt="" width={28} height={28} style={{ borderRadius: '6px', verticalAlign: 'middle', marginRight: '10px' }} />
                <span style={{ fontWeight: 800, fontSize: '1.125rem', color: '#0ea5e9' }}>衍策引擎AI</span>
                <span style={{ fontSize: '0.75rem', color: 'rgba(255,255,255,0.6)', marginLeft: '12px' }}>Policy Intelligence Report</span>
              </div>
              <div className="yc-report-meta">
                <span>报告编号：YC-2026-0627</span>
                <span>生成时间：2026.06.27</span>
              </div>
            </div>

            {/* Report Body */}
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

            {/* Report Footer */}
            <div className="yc-report-footer">
              <span className="yc-report-disclaimer">
                * 以上为示例报告，实际内容以企业真实数据和最新政策文件为准。补贴金额为预估区间，具体以主管部门审核结果为准。
              </span>
              <Link href="/login?register=1" className="yc-btn-primary-sm">
                生成你的报告 &rarr;
              </Link>
            </div>
          </div>
        </div>
      </section>

      {/* ===== CORE CAPABILITIES SECTION ===== */}
      <section className="section section-alt">
        <div className="container">
          <div className="section-header">
            <span className="section-label">核心能力</span>
            <h2 className="section-title">从产业研究到申报落地的全链路 AI 引擎</h2>
            <p className="section-subtitle">
              衍策引擎AI 整合产业数据、政策引擎和 AI 生成能力，为科技企业提供一站式政策与产业服务。
            </p>
          </div>

          {/* Equation bar */}
          <div className="yc-equation-bar">
            <span className="yc-equation-label">衍策引擎AI</span>
            <span className="yc-equation-eq">=</span>
            {['产业研究', '政策匹配', '申报辅助', '企业画像', '园区入驻', '材料生成'].map((item, i, arr) => (
              <span key={item} style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <span className="yc-equation-chip">{item}</span>
                {i < arr.length - 1 && <span className="yc-equation-plus">+</span>}
              </span>
            ))}
          </div>

          {/* 6 core modules */}
          <div className="grid grid-3" style={{ gap: '24px' }}>
            {[
              {
                icon: '\u{1F50D}',
                title: '产业研究',
                desc: '覆盖新质生产力核心赛道的产业格局、价值链、技术趋势和政策环境深度分析。',
                tag: '数据层',
              },
              {
                icon: '\u{1F3AF}',
                title: '政策匹配',
                desc: 'AI 驱动的政策语义引擎，自动匹配企业画像与政策条件，输出适配度评分和优先级排序。',
                tag: '引擎层',
              },
              {
                icon: '\u{1F4CB}',
                title: '申报材料生成',
                desc: '自动生成申报书、材料清单、合规检查报告，支持条款级政策引用和格式规范校验。',
                tag: '交付层',
              },
              {
                icon: '\u{1F3E2}',
                title: '企业画像',
                desc: '整合工商、知识产权、财务、团队等多维数据，生成结构化科技企业画像和资质评估。',
                tag: '数据层',
              },
              {
                icon: '\u{1F3D7}\u{FE0F}',
                title: '园区入驻',
                desc: '基于企业行业和发展阶段，智能推荐园区入驻方案，匹配产业资源和扶持政策。',
                tag: '引擎层',
              },
              {
                icon: '\u{1F916}',
                title: '园区 / 机构解决方案',
                desc: '为园区和孵化器提供政策知识库 Bot、企业服务台和招商智能化工具的 SaaS 部署方案。',
                tag: '平台层',
              },
            ].map((mod) => (
              <div key={mod.title} className="yc-capability-card">
                <div className="yc-capability-tag">{mod.tag}</div>
                <div className="yc-capability-icon">{mod.icon}</div>
                <h3 className="yc-capability-title">{mod.title}</h3>
                <p className="yc-capability-desc">{mod.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ===== PRODUCT MATRIX SECTION ===== */}
      <section className="section">
        <div className="container">
          <div className="section-header">
            <span className="section-label">产品矩阵</span>
            <h2 className="section-title">七大产品模块，覆盖政策服务全场景</h2>
            <p className="section-subtitle">
              从政策发现到申报落地，每个环节都有专业工具支撑。
            </p>
          </div>

          <div className="yc-product-grid">
            {PRODUCTS.map((p, i) => (
              <div key={p.name} className={`yc-product-card${i === 0 ? ' yc-product-featured' : ''}`}>
                <div className="yc-product-icon">{p.icon}</div>
                <div className="yc-product-name">{p.name}</div>
                <div className="yc-product-subtitle">{p.subtitle}</div>
                <p className="yc-product-desc">{p.desc}</p>
                <div className="yc-product-tags">
                  {p.tags.map((t) => (
                    <span key={t} className="yc-product-tag">{t}</span>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ===== TRUST & TRACEABILITY SECTION ===== */}
      <section className="yc-trust-section">
        <div className="container">
          <div className="section-header">
            <span className="badge" style={{ background: 'rgba(14,165,233,0.2)', color: '#0ea5e9', marginBottom: '16px' }}>
              可信溯源
            </span>
            <h2 className="section-title" style={{ color: '#fff' }}>
              每条建议，都可追溯、可解释、可复核
            </h2>
            <p className="section-subtitle" style={{ color: 'rgba(255,255,255,0.65)' }}>
              衍策引擎AI 的所有输出都建立在可追溯的数据基础之上，确保专业性和可信度。
            </p>
          </div>

          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '12px', justifyContent: 'center', marginBottom: '32px' }}>
            {[
              { icon: '\u{1F4DC}', label: '政策原文来源' },
              { icon: '\u{1F4C5}', label: '政策时效标注' },
              { icon: '\u{2696}\u{FE0F}', label: '适用条件说明' },
              { icon: '\u{1F4CF}', label: '匹配规则透明' },
              { icon: '\u{1F4CA}', label: '数据更新时间' },
              { icon: '\u{1F50D}', label: '引用精确到条' },
              { icon: '\u{1F504}', label: '复核机制' },
              { icon: '\u{1F4DD}', label: '操作审计日志' },
              { icon: '\u{1F6E1}\u{FE0F}', label: '数据安全保障' },
              { icon: '\u{1F4E4}', label: '报告可导出' },
            ].map((chip) => (
              <div key={chip.label} className="yc-trust-chip">
                <span>{chip.icon}</span>
                {chip.label}
              </div>
            ))}
          </div>

          <div className="yc-trust-banner">
            <span style={{ fontSize: '0.875rem', fontWeight: 600, color: '#0ea5e9' }}>
              {'\uD83D\uDEE1\uFE0F'} 人工复核
            </span>
            <span style={{ fontSize: '0.875rem', color: 'rgba(255,255,255,0.7)', marginLeft: '8px' }}>
              &mdash; 所有 AI 输出均支持人工复核和结果修正流程，确保服务质量
            </span>
          </div>
        </div>
      </section>

      {/* ===== INDUSTRY SOLUTIONS SECTION ===== */}
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
                <div className="yc-solution-icon">{s.icon}</div>
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

      {/* ===== PRICING SECTION ===== */}
      <section className="section">
        <div className="container">
          <div className="section-header">
            <span className="section-label">价格方案</span>
            <h2 className="section-title">灵活的定价，匹配不同阶段的企业</h2>
            <p className="section-subtitle">
              从初创科技企业到大型园区集团，找到适合你的方案。
            </p>

            {/* Annual toggle */}
            <div className="yc-pricing-toggle">
              <button
                onClick={() => setAnnual(false)}
                className={`yc-toggle-btn${!annual ? ' yc-toggle-active' : ''}`}
              >
                月付
              </button>
              <button
                onClick={() => setAnnual(true)}
                className={`yc-toggle-btn${annual ? ' yc-toggle-active' : ''}`}
              >
                年付
                <span className="yc-toggle-badge">省 20%</span>
              </button>
            </div>
          </div>

          <div className="grid grid-3" style={{ gap: '24px' }}>
            {[
              {
                name: '初创版',
                desc: '适合科技型中小企业和初创公司',
                monthly: 1999,
                features: [
                  'Policy Match 政策匹配引擎',
                  'Company Profile 企业画像',
                  '基础政策库（市级政策）',
                  '每月 10 次报告生成',
                  '邮件支持',
                ],
                featured: false,
              },
              {
                name: '成长版',
                desc: '适合高新技术企业和专精特新企业',
                monthly: 5999,
                features: [
                  '全部 7 个产品模块',
                  '完整政策库（国家+省+市级）',
                  'Grant Copilot 申报助手',
                  'Report Studio 报告生成器',
                  '不限报告生成次数',
                  '专属客户成功经理',
                  'API 集成支持',
                ],
                featured: true,
              },
              {
                name: '机构版',
                desc: '适合园区、孵化器和产业服务机构',
                monthly: 19999,
                features: [
                  '成长版全部功能',
                  'Knowledge Bot 知识库 Bot',
                  'Park Entry 园区匹配系统',
                  '私有化部署选项',
                  '多园区管理',
                  '定制政策库接入',
                  'SLA 保障',
                  '专属技术支持团队',
                ],
                featured: false,
              },
            ].map((tier) => {
              const price = annual ? Math.round(tier.monthly * 0.8) : tier.monthly;
              return (
                <div key={tier.name} className={`yc-pricing-card${tier.featured ? ' yc-pricing-featured' : ''}`}>
                  {tier.featured && <div className="yc-pricing-badge">最受欢迎</div>}
                  <div className="yc-pricing-name">{tier.name}</div>
                  <div className="yc-pricing-desc">{tier.desc}</div>
                  <div className="yc-pricing-price">
                    &yen;{price.toLocaleString()}
                    <span className="yc-pricing-unit"> 元/月</span>
                  </div>
                  <div className="yc-pricing-period">{annual ? '按年付费' : '按月付费'}</div>
                  <div className="yc-pricing-divider" />
                  <ul className="yc-pricing-features">
                    {tier.features.map((f) => (
                      <li key={f}>
                        <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true">
                          <path d="M3 8.5L6.5 12L13 4" stroke="#22c55e" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
                        </svg>
                        {f}
                      </li>
                    ))}
                  </ul>
                  <Link
                    href="/login?register=1"
                    className={`yc-btn-pricing${tier.featured ? ' yc-btn-pricing-primary' : ''}`}
                  >
                    {tier.name === '机构版' ? '联系销售' : '开始使用'}
                  </Link>
                </div>
              );
            })}
          </div>

          <div style={{ textAlign: 'center', marginTop: '32px' }}>
            <Link href="/pricing" className="btn btn-ghost">
              查看完整功能对比表 &rarr;
            </Link>
          </div>
        </div>
      </section>

      {/* ===== FAQ SECTION ===== */}
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

      {/* ===== COMPLIANCE SECTION ===== */}
      <section className="yc-compliance-section">
        <div className="container">
          <div className="yc-compliance-box">
            <div className="yc-compliance-icon">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#0ea5e9" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
              </svg>
            </div>
            <p className="yc-compliance-text">
              衍策引擎AI 提供产业研究、政策信息整理、材料生成和申报辅助服务，具体申报条件、申报结果和补贴金额以主管部门、园区、政策文件和审核结果为准。
            </p>
          </div>
        </div>
      </section>

      {/* ===== DASHBOARD CTA ===== */}
      <section className="yc-dash-cta-strip">
        <div className="container">
          <div className="yc-dash-cta-inner">
            <div>
              <h3 className="yc-dash-cta-title">登录查看全部政策红利</h3>
              <p className="yc-dash-cta-desc">
                你的企业已有 <strong>23</strong> 项可匹配政策，<strong>5</strong> 项正在申报中，预计红利 <strong>¥380万</strong>
              </p>
            </div>
            <Link href="/dashboard" className="yc-btn-primary">
              打开政策仪表盘 &rarr;
            </Link>
          </div>
        </div>
      </section>

      {/* ===== CTA SECTION ===== */}
      <section className="yc-cta-section">
        <div className="container">
          <h2 className="yc-cta-title">让你的企业更快找到政策、资金和资源</h2>
          <p className="yc-cta-subtitle">
            30 分钟了解 衍策引擎AI 如何帮助你的科技企业完成政策匹配、申报规划和园区对接。
          </p>
          <div className="yc-cta-actions">
            <Link href="/login?register=1" className="yc-btn-primary">
              生成政策匹配报告
            </Link>
            <a href="mailto:contact@yance.ai" className="yc-btn-outline-white">
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
