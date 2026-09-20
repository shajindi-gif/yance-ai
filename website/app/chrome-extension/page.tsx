'use client';

import { useState } from 'react';
import Link from 'next/link';

/* --- Extraction Fields --- */
const EXTRACTION_FIELDS = [
  { icon: '\u{1F4CB}', name: '政策名称', key: 'policy_name', desc: '自动识别政策文件标题和正式名称' },
  { icon: '\u{1F3DB}', name: '发文机关', key: 'issuing_authority', desc: '提取发布政策的政府部门或机构' },
  { icon: '\u{1F3ED}', name: '目标产业', key: 'target_industry', desc: '识别政策适用的行业和产业方向' },
  { icon: '\u{1F4B0}', name: '补贴金额', key: 'subsidy_amount', desc: '提取资金支持额度和比例信息' },
  { icon: '\u{1F4C5}', name: '申报截止', key: 'application_deadline', desc: '捕获申报时间节点和有效期' },
  { icon: '\u{1F4C4}', name: '材料要求', key: 'material_requirements', desc: '汇总申报所需材料清单' },
];

/* --- Workflow Steps --- */
const WORKFLOW = [
  { step: 1, title: '浏览政策页面', desc: '在任意政府网站或政策发布平台上浏览政策文件' },
  { step: 2, title: '智能识别采集', desc: '插件自动识别页面中的政策关键信息并高亮标注' },
  { step: 3, title: '一键保存到平台', desc: '确认采集结果，一键同步到 衍策引擎AI 企业账户' },
  { step: 4, title: '匹配与申报', desc: '在平台中自动匹配企业画像，生成申报建议' },
];

/* --- Tech Specs --- */
const TECH_SPECS = [
  { label: '产品状态', value: 'Concept Demo / 未发布' },
  { label: 'Manifest 目标', value: 'Manifest V3（待实现）' },
  { label: '权限范围', value: '发布前按最小权限重新评审' },
  { label: '数据处理', value: '发布前完成隐私与安全验收' },
  { label: '兼容性', value: '尚未建立真实兼容性测试矩阵' },
  { label: '安装包', value: 'No artifact available yet' },
];

/* --- Side Panel Mockup Component --- */
function SidePanelMockup() {
  return (
    <div className="yc-ext-mockup-browser">
      <div className="yc-ext-mockup-toolbar">
        <div className="yc-ext-mockup-dots">
          <span /><span /><span />
        </div>
        <div className="yc-ext-mockup-url">
          https://example.invalid/demo-policy
        </div>
      </div>
      <div className="yc-ext-mockup-body">
        {/* Main content area */}
        <div className="yc-ext-mockup-content">
          <div className="yc-ext-mockup-page-title">
            DEMO：人工智能专项资金项目申报通知（虚构示例）
          </div>
          <div className="yc-ext-mockup-page-text">
            <p>各有关单位：</p>
            <p>根据《上海市促进人工智能产业发展若干规定》，现启动 2026 年度人工智能专项资金项目申报工作。</p>
            <p className="yc-ext-highlighted">
              <span className="yc-ext-highlight-label">补贴金额</span>
              单个项目资助金额不超过 500 万元，资助比例不超过项目总投资的 30%。
            </p>
            <p className="yc-ext-highlighted">
              <span className="yc-ext-highlight-label">申报截止</span>
              项目申报截止日期为 2026 年 9 月 30 日。
            </p>
            <p>申报单位应为在本市注册的独立法人单位，具有良好信用记录...</p>
          </div>
        </div>
        {/* Side panel */}
        <div className="yc-ext-mockup-sidebar">
          <div className="yc-ext-sidebar-header">
            <img src="/logo.png" alt="" width={20} height={20} style={{ borderRadius: '4px', verticalAlign: 'middle', marginRight: '6px' }} />
            <span className="yc-ext-sidebar-logo">衍策引擎AI</span>
            <span className="yc-ext-sidebar-badge">6 项已识别</span>
          </div>
          <div className="yc-ext-sidebar-section">
            <div className="yc-ext-sidebar-label">提取结果</div>
            <div className="yc-ext-sidebar-field">
              <span className="yc-ext-field-key">政策名称</span>
              <span className="yc-ext-field-val">2026 年度人工智能专项资金项目申报</span>
            </div>
            <div className="yc-ext-sidebar-field">
              <span className="yc-ext-field-key">发文机关</span>
              <span className="yc-ext-field-val">上海市科学技术委员会</span>
            </div>
            <div className="yc-ext-sidebar-field">
              <span className="yc-ext-field-key">目标产业</span>
              <span className="yc-ext-field-val">人工智能</span>
            </div>
            <div className="yc-ext-sidebar-field">
              <span className="yc-ext-field-key">补贴金额</span>
              <span className="yc-ext-field-val yc-ext-val-highlight">≤ 500 万元 (30%)</span>
            </div>
            <div className="yc-ext-sidebar-field">
              <span className="yc-ext-field-key">申报截止</span>
              <span className="yc-ext-field-val yc-ext-val-warning">2026-09-30</span>
            </div>
            <div className="yc-ext-sidebar-field">
              <span className="yc-ext-field-key">材料要求</span>
              <span className="yc-ext-field-val">项目申报书、财务审计报告、知识产权证明...</span>
            </div>
          </div>
          <button className="yc-ext-sidebar-btn" disabled>DEMO：保存到工作区</button>
        </div>
      </div>
    </div>
  );
}

/* --- Page Component --- */
export default function ChromeExtensionPage() {
  const [activeTab, setActiveTab] = useState<'overview' | 'install'>('overview');

  return (
    <>
      {/* Hero */}
      <div className="yc-ext-hero">
        <div className="container">
          <span className="yc-ext-hero-badge">CONCEPT DEMO · 未发布</span>
          <h1 className="yc-ext-hero-title">衍策引擎AI 政策助手</h1>
          <p className="yc-ext-hero-subtitle">
            展示浏览器侧边栏采集与核对政策信息的产品设想；当前没有可下载扩展，也没有经验证的效率数据。
          </p>
          <div className="yc-ext-hero-ctas">
            <Link href="/login?register=1" className="yc-btn-primary">
              先用 Web 工作区
            </Link>
            <a href="#features" className="yc-btn-outline-white">
              了解功能
            </a>
          </div>
        </div>
      </div>

      {/* Feature Mockup */}
      <section className="section" id="features">
        <div className="container">
          <div className="section-header">
            <span className="section-label">核心功能</span>
            <h2 className="section-title">交互概念演示</h2>
            <p className="section-subtitle">
              下方界面和政策内容均为 DEMO，用于讨论未来采集、确认和保存流程，不代表已上线能力。
            </p>
          </div>
          <SidePanelMockup />
        </div>
      </section>

      {/* Extraction Fields */}
      <section className="section section-alt">
        <div className="container">
          <div className="section-header">
            <span className="section-label">智能提取</span>
            <h2 className="section-title">6 大结构化字段</h2>
            <p className="section-subtitle">
              基于中文语义理解引擎，从非结构化政策文本中精准提取关键信息
            </p>
          </div>
          <div className="yc-ext-fields-grid">
            {EXTRACTION_FIELDS.map((f, i) => (
              <div key={i} className="yc-ext-field-card">
                <div className="yc-ext-field-icon">{f.icon}</div>
                <h3 className="yc-ext-field-name">{f.name}</h3>
                <code className="yc-ext-field-key-code">{f.key}</code>
                <p className="yc-ext-field-desc">{f.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Sidebar Query Feature */}
      <section className="section">
        <div className="container">
          <div className="section-header">
            <span className="section-label">侧边栏查询</span>
            <h2 className="section-title">随时调起 AI 政策匹配</h2>
            <p className="section-subtitle">
              在任何网页上打开侧边栏，输入企业信息即可获取政策匹配建议、企业画像和申报方向。
            </p>
          </div>
          <div className="yc-ext-capabilities">
            <div className="yc-ext-cap-card">
              <div className="yc-ext-cap-icon">{'\u{1F50D}'}</div>
              <h3>政策查询</h3>
              <p>输入企业行业和地区，AI 从政策库中筛选最匹配的申报方向</p>
            </div>
            <div className="yc-ext-cap-card">
              <div className="yc-ext-cap-icon">{'\u{1F3E2}'}</div>
              <h3>企业画像</h3>
              <p>输入企业名称，自动生成技术能力、资质条件和发展阶段分析</p>
            </div>
            <div className="yc-ext-cap-card">
              <div className="yc-ext-cap-icon">{'\u{1F4E6}'}</div>
              <h3>采集管理</h3>
              <p>已采集的政策自动归类到企业账户，支持搜索、标注和导出</p>
            </div>
          </div>
        </div>
      </section>

      {/* Workflow */}
      <section className="section section-alt">
        <div className="container">
          <div className="section-header">
            <span className="section-label">使用流程</span>
            <h2 className="section-title">4 步完成政策采集</h2>
          </div>
          <div className="yc-ext-workflow">
            {WORKFLOW.map((w, i) => (
              <div key={i} className="yc-ext-workflow-step">
                <div className="yc-ext-workflow-num">{w.step}</div>
                <h3>{w.title}</h3>
                <p>{w.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Tabs: Overview / Install */}
      <section className="section">
        <div className="container container-narrow">
          <div className="yc-ext-tabs">
            <button
              className={`yc-ext-tab${activeTab === 'overview' ? ' yc-ext-tab-active' : ''}`}
              onClick={() => setActiveTab('overview')}
            >
              技术规格
            </button>
            <button
              className={`yc-ext-tab${activeTab === 'install' ? ' yc-ext-tab-active' : ''}`}
              onClick={() => setActiveTab('install')}
            >
              安装指南
            </button>
          </div>

          {activeTab === 'overview' && (
            <div className="yc-ext-tab-panel">
              <table className="yc-ext-specs-table">
                <tbody>
                  {TECH_SPECS.map((s, i) => (
                    <tr key={i}>
                      <td className="yc-ext-spec-label">{s.label}</td>
                      <td className="yc-ext-spec-value">{s.value}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
              <div className="yc-ext-security-note">
                <strong>设计目标：</strong>尽量本地处理并在上传前取得用户确认。具体权限、数据流与传输控制须在实现后通过安全评审，本页面不作既成能力承诺。
              </div>
            </div>
          )}

          {activeTab === 'install' && (
            <div className="yc-ext-tab-panel">
              <div className="yc-ext-install-steps">
                <div className="yc-ext-install-step">
                  <span className="yc-ext-install-num">1</span>
                  <div>
                    <h4>当前不可安装</h4>
                    <p>尚未生成或发布扩展安装包，请在 <Link href="/downloads">发布状态页</Link> 查看真实进度。</p>
                  </div>
                </div>
                <div className="yc-ext-install-step">
                  <span className="yc-ext-install-num">2</span>
                  <div>
                    <h4>完成实现</h4>
                    <p>实现最小权限、来源校验、租户认证和明确的数据上传确认。</p>
                  </div>
                </div>
                <div className="yc-ext-install-step">
                  <span className="yc-ext-install-num">3</span>
                  <div>
                    <h4>安全验收</h4>
                    <p>完成代码审查、权限审查、隐私披露和兼容性测试。</p>
                  </div>
                </div>
                <div className="yc-ext-install-step">
                  <span className="yc-ext-install-num">4</span>
                  <div>
                    <h4>签名发布</h4>
                    <p>仅在真实商店或签名构件可用后提供安装说明。</p>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      </section>

      {/* CTA */}
      <div className="yc-cta-section">
        <div className="container" style={{ textAlign: 'center' }}>
          <h2 className="yc-cta-title">先使用 Web 工作区</h2>
          <p style={{ color: 'var(--text-inverse-secondary)', marginBottom: 24, maxWidth: 520, marginLeft: 'auto', marginRight: 'auto' }}>
            浏览器扩展仍在路线图中；当前请使用已部署的 Web 功能。
          </p>
          <div className="yc-cta-actions" style={{ justifyContent: 'center' }}>
            <Link href="/downloads" className="yc-btn-primary">查看发布状态</Link>
            <Link href="/login?register=1" className="yc-btn-outline-white">打开 Web 工作区</Link>
          </div>
        </div>
      </div>
    </>
  );
}
