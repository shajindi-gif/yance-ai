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
    a: '注册后完善企业画像，即可生成政策匹配初筛报告。如需 30 分钟专属诊断，发送邮件至 yanceai@163.com 预约，我们将根据企业实际场景进行针对性讲解。',
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
              衍策引擎 AI · 企业政策与资金顾问
            </div>

            <h1 className="yc-hero-title">
              让企业更容易<br />
              <span style={{ color: 'var(--teal-bright)' }}>找到适合自己的政策</span>
            </h1>

            <p className="yc-hero-subtitle">
              根据企业所在地区、所属行业和经营情况，查找可能适用的扶持政策，
              核对申报条件，整理所需材料，生成可追溯的初筛报告。
            </p>

            <div className="yc-hero-ctas">
              <Link href="/login?register=1" className="yc-btn-primary">
                开始政策匹配
              </Link>
              <a href="#report-preview" className="yc-btn-outline-white">
                查看报告示例
              </a>
            </div>
          </div>
        </div>
      </section>

      {/* ===== SMART INPUT BOX（报告生成入口） ===== */}
      <section className="yc-input-section">
        <div className="container">
          <form className="yc-input-wrapper" onSubmit={submitSearch}>
            <h2 className="yc-input-title">输入企业信息，查看可能适用的政策</h2>
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
                placeholder="例如：上海，人工智能，50 人，有 6 项软著和 2 项发明专利——注册后按这些条件核对适用政策与申报要求。"
                value={searchInput}
                onChange={(e) => setSearchInput(e.target.value)}
              />
              <button type="submit" className="yc-search-submit">
                开始匹配
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
      <section className="section" id="report-preview">
        <div className="container">
          <div className="section-header">
            <span className="section-label">报告示例</span>
            <h2 className="section-title">一份初筛报告里有什么</h2>
            <p className="section-subtitle">
              每条推荐都对应到政策原文条款与企业事实；证据不足的项目会明确标出，而不是猜一个结论。
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

      {/* ===== REAL PRODUCT SCREENSHOTS ===== */}
      <section className="section section-alt" id="product">
        <div className="container">
          <div className="section-header">
            <span className="section-label">产品界面</span>
            <h2 className="section-title">登录后你看到的，就是这些</h2>
            <p className="section-subtitle">
              以下为示例工作区的真实界面截图（数据为测试数据），不是设计稿。
            </p>
          </div>
          <div className="yc-shots">
            <figure className="yc-shot">
              <img src="/product/command-center.webp" alt="指挥中心界面：资金管道、截止提醒与行动建议" width={1440} height={900} loading="lazy" />
              <figcaption>指挥中心 — 可申请资金、30 天截止、待补证据一屏可见</figcaption>
            </figure>
            <div className="yc-shot-row">
              <figure className="yc-shot">
                <img src="/product/discover.webp" alt="发现资金界面：政策目录与筛选" width={1440} height={900} loading="lazy" />
                <figcaption>发现资金 — 国家 / 市 / 区政策目录，可查原文</figcaption>
              </figure>
              <figure className="yc-shot">
                <img src="/product/opportunities.webp" alt="我的机会界面：匹配结果与资格状态" width={1440} height={900} loading="lazy" />
                <figcaption>我的机会 — 适配度评分与逐条资格状态</figcaption>
              </figure>
            </div>
          </div>
        </div>
      </section>

      {/* ===== WORKFLOW（用户实际工作流程，每步对应真实功能） ===== */}
      <section className="section">
        <div className="container">
          <div className="section-header">
            <span className="section-label">工作流程</span>
            <h2 className="section-title">从企业信息到初筛报告，五步完成</h2>
            <p className="section-subtitle">
              每一步都在产品里有对应页面，不是概念图。
            </p>
          </div>
          <div className="yc-workflow">
            {[
              { step: '01', title: '输入企业信息', desc: '名称、地区、行业、规模、知识产权与研发情况，10 分钟内可完成。' },
              { step: '02', title: '查找适用政策', desc: '按地区、行业与资质条件在政策库中检索，含国家、市、区三级。' },
              { step: '03', title: '核对申报条件', desc: '逐条硬性门槛判定：符合 / 不符合 / 证据不足，附政策原文条款。' },
              { step: '04', title: '整理材料清单', desc: '按政策要求生成待办材料与缺口，标注哪些已具备、哪些需补充。' },
              { step: '05', title: '生成初筛报告', desc: '汇总匹配结果与依据，导出 PDF，供内部决策或顾问复核。' },
            ].map((w) => (
              <div key={w.step} className="yc-workflow-step">
                <span className="yc-workflow-num">{w.step}</span>
                <div>
                  <h3>{w.title}</h3>
                  <p>{w.desc}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ===== CAPABILITIES BY USER TASK（按任务分组，区分已上线/开发中） ===== */}
      <section className="section section-alt">
        <div className="container">
          <div className="section-header">
            <span className="section-label">产品能力</span>
            <h2 className="section-title">按你要完成的事来组织</h2>
            <p className="section-subtitle">
              我们明确区分已上线与开发中的能力，未验证的功能不会出现在可点击入口里。
            </p>
          </div>
          <div className="yc-task-grid">
            {[
              {
                title: '发现政策机会',
                status: '已上线',
                href: '/discover',
                items: [
                  { name: '政策知识库检索', desc: '国家 / 市 / 区三级政策，含发布日期与有效期', live: true },
                  { name: '企业 × 政策匹配', desc: '按画像条件返回适配度与资格状态', live: true },
                  { name: '截止日提醒', desc: 'T-30 / 14 / 7 / 3 / 1 站内与邮件通知', live: true },
                ],
              },
              {
                title: '判断申报资格',
                status: '已上线',
                href: '/opportunities',
                items: [
                  { name: '硬性门槛核对', desc: '注册地、年限、营收、研发占比等逐条判定', live: true },
                  { name: '证据引用', desc: '每条结论可回溯到政策原文条款', live: true },
                  { name: '缺失信息清单', desc: '明确标出无法判定的条件与所需证明', live: true },
                ],
              },
              {
                title: '准备申报材料',
                status: '已上线',
                href: '/applications',
                items: [
                  { name: '材料清单与缺口', desc: '按政策要求生成待办与已具备项', live: true },
                  { name: '申报书草稿', desc: '结合企业事实生成初稿，人工复核后导出', live: true },
                  { name: '分章节智能改写', desc: '按评审意见逐节扩写、精简、补证据', live: false },
                ],
              },
              {
                title: '了解产业与园区资源',
                status: '部分上线',
                href: '/parks',
                items: [
                  { name: '园区政策资料', desc: '张江 / 临港 / 徐汇等重点载体公开政策整理', live: true },
                  { name: '产业研究报告', desc: '赛道格局与政策趋势分析（样例）', live: true },
                  { name: '园区知识库 Bot', desc: '面向园区运营方的问答部署', live: false },
                ],
              },
            ].map((group) => (
              <div key={group.title} className="yc-task-card">
                <div className="yc-task-head">
                  <h3>{group.title}</h3>
                  <span className={`yc-live-badge ${group.status === '已上线' ? 'on' : 'partial'}`}>{group.status}</span>
                </div>
                <ul className="yc-task-list">
                  {group.items.map((item) => (
                    <li key={item.name}>
                      <span className={item.live ? '' : 'yc-item-dev'}>
                        <strong>{item.name}</strong>
                        <small>{item.desc}</small>
                      </span>
                      {!item.live && <span className="yc-dev-tag">开发中</span>}
                    </li>
                  ))}
                </ul>
                <Link href={group.href} className="yc-task-link">进入使用 &rarr;</Link>
              </div>
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
              &mdash; 系统给出的每条结论都支持人工复核与修正；申报结果以主管部门审核为准，我们不承诺获批
            </span>
          </div>
        </div>
      </section>

      {/* ===== INDUSTRY SOLUTIONS ===== */}
      <section className="section section-alt">
        <div className="container">
          <div className="section-header">
            <span className="section-label">行业解决方案</span>
            <h2 className="section-title">我们重点服务的六个行业</h2>
            <p className="section-subtitle">
              不同行业的资助口径差异很大。我们按行业整理条件与材料要求，减少通用检索遗漏的专项政策。
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
            <a href="mailto:yanceai@163.com?subject=产品咨询" className="yc-btn-outline-white">
              联系我们
            </a>
          </div>
          <div className="yc-cta-info">
            <span>yanceai@163.com</span>
            <span className="yc-cta-sep">|</span>
            <span>衍策引擎AI</span>
          </div>
        </div>
      </section>
    </>
  );
}
